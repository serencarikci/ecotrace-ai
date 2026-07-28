from __future__ import annotations
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import AuthorizationError, NotFoundError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import GeneratedReport, ScheduledReport
from ecotrace.modules.reporting.application import report_service as phase4_reports
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_manage, require_automation_read, require_automation_write

def list_scheduled(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(ScheduledReport).where(ScheduledReport.organization_id == organization_id)).scalars()
    return [_ser_sched(r) for r in rows]

def create_scheduled(db: Session, user: User, organization_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = ScheduledReport(organization_id=organization_id, code=str(payload['code']), name=str(payload['name']), report_type=str(payload.get('reportType') or 'executive_sustainability_summary'), schedule_expression=str(payload.get('scheduleExpression') or 'monthly'), timezone=str(payload.get('timezone') or 'UTC'), report_config_json=payload.get('reportConfig') or {}, output_format=str(payload.get('outputFormat') or 'json'), recipient_user_ids_json=payload.get('recipientUserIds') or [], approval_required=bool(payload.get('approvalRequired') or False), status='draft', created_by_user_id=user.id, next_generation_at=datetime.now(UTC))
    db.add(row)
    db.flush()
    write_audit_log(db, action='scheduled_report.created', actor_user_id=user.id, organization_id=organization_id, entity_type='scheduled_report', entity_id=str(row.id))
    return _ser_sched(row)

def get_scheduled(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser_sched(_get_sched(db, organization_id, report_id))

def update_scheduled(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_sched(db, organization_id, report_id)
    for key, attr in {'name': 'name', 'scheduleExpression': 'schedule_expression', 'outputFormat': 'output_format', 'reportConfig': 'report_config_json', 'recipientUserIds': 'recipient_user_ids_json', 'approvalRequired': 'approval_required'}.items():
        if key in payload:
            setattr(row, attr, payload[key])
    db.flush()
    return _ser_sched(row)

def activate_scheduled(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get_sched(db, organization_id, report_id)
    row.status = 'active'
    db.flush()
    return _ser_sched(row)

def pause_scheduled(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get_sched(db, organization_id, report_id)
    row.status = 'paused'
    db.flush()
    return _ser_sched(row)

def run_scheduled(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_sched(db, organization_id, report_id)
    return generate_now(db, user, organization_id, report_type=row.report_type, scheduled_report_id=row.id, output_format=row.output_format)

def generate_now(db: Session, user: User, organization_id: uuid.UUID, *, report_type: str, scheduled_report_id: uuid.UUID | None, output_format: str='json') -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    settings = get_settings()
    payload = _build_report_payload(db, user, organization_id, report_type)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')
    checksum = hashlib.sha256(raw).hexdigest()
    root = Path(settings.report_storage_path) / str(organization_id)
    root.mkdir(parents=True, exist_ok=True)
    file_name = f'{report_type}-{uuid.uuid4().hex}.{output_format}'
    path = root / file_name
    if output_format == 'csv':
        path.write_text(_to_csv(payload), encoding='utf-8')
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    elif output_format == 'pdf':
        path.write_bytes(b'%PDF-1.4\n% EcoTrace report artifact\n' + raw + b'\n%%EOF\n')
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        path.write_bytes(raw)
    status = 'pending_approval' if scheduled_report_id and _needs_approval(db, scheduled_report_id) else 'ready'
    row = GeneratedReport(organization_id=organization_id, scheduled_report_id=scheduled_report_id, report_type=report_type, title=f"{report_type.replace('_', ' ').title()} — {datetime.now(UTC).date()}", reporting_period_start=None, reporting_period_end=None, output_format=output_format, storage_path=str(path), checksum=checksum, status=status, generated_by_user_id=user.id, content_preview_json={'keys': list(payload.keys())[:20]})
    db.add(row)
    if scheduled_report_id:
        sched = _get_sched(db, organization_id, scheduled_report_id)
        sched.last_generated_at = datetime.now(UTC)
    write_audit_log(db, action='scheduled_report.generated', actor_user_id=user.id, organization_id=organization_id, entity_type='generated_report', entity_id=str(row.id), metadata={'checksum': checksum})
    db.flush()
    return _ser_gen(row)

def list_generated(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(GeneratedReport).where(GeneratedReport.organization_id == organization_id).order_by(GeneratedReport.created_at.desc())).scalars()
    return [_ser_gen(r) for r in rows]

def get_generated(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser_gen(_get_gen(db, organization_id, report_id))

def download(db: Session, user: User, organization_id: uuid.UUID, report_id: uuid.UUID) -> tuple[str, bytes, str]:
    require_automation_read(db, user, organization_id)
    row = _get_gen(db, organization_id, report_id)
    path = Path(row.storage_path)
    if not path.exists():
        raise NotFoundError('Report file missing.')
    settings = get_settings()
    root = Path(settings.report_storage_path).resolve()
    if root not in path.resolve().parents and path.resolve() != root:
        raise AuthorizationError('Invalid report path.')
    write_audit_log(db, action='generated_report.downloaded', actor_user_id=user.id, organization_id=organization_id, entity_type='generated_report', entity_id=str(row.id))
    media = {'json': 'application/json', 'csv': 'text/csv', 'pdf': 'application/pdf'}.get(row.output_format, 'application/octet-stream')
    return (path.name, path.read_bytes(), media)

def _needs_approval(db: Session, scheduled_report_id: uuid.UUID) -> bool:
    row = db.get(ScheduledReport, scheduled_report_id)
    return bool(row and row.approval_required)

def _build_report_payload(db: Session, user: User, organization_id: uuid.UUID, report_type: str) -> dict[str, Any]:
    try:
        if report_type in {'executive_sustainability_summary', 'executive'}:
            return phase4_reports.executive_report(db, user, organization_id)
        if report_type in {'carbon_inventory_summary', 'inventory_summary'}:
            return phase4_reports.inventory_summary_report(db, user, organization_id)
        if report_type == 'target_progress_report':
            return phase4_reports.target_progress_report(db, user, organization_id)
    except Exception as exc:
        return {'reportType': report_type, 'organizationId': str(organization_id), 'generatedAt': datetime.now(UTC).isoformat(), 'warning': f'Fallback payload due to: {exc}', 'summary': 'Report generated with limited data.'}
    return {'reportType': report_type, 'organizationId': str(organization_id), 'generatedAt': datetime.now(UTC).isoformat(), 'summary': f'EcoTrace {report_type} snapshot'}

def _to_csv(payload: dict[str, Any]) -> str:
    lines = ['key,value']
    for key, value in payload.items():
        raw = json.dumps(value, ensure_ascii=False).replace('"', "'")
        lines.append(f'"{key}","{raw}"')
    return '\n'.join(lines)

def _get_sched(db: Session, organization_id: uuid.UUID, report_id: uuid.UUID) -> ScheduledReport:
    row = db.execute(select(ScheduledReport).where(ScheduledReport.id == report_id, ScheduledReport.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Scheduled report not found.')
    return row

def _get_gen(db: Session, organization_id: uuid.UUID, report_id: uuid.UUID) -> GeneratedReport:
    row = db.execute(select(GeneratedReport).where(GeneratedReport.id == report_id, GeneratedReport.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Generated report not found.')
    return row

def _ser_sched(row: ScheduledReport) -> dict[str, Any]:
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'reportType': row.report_type, 'scheduleExpression': row.schedule_expression, 'timezone': row.timezone, 'outputFormat': row.output_format, 'approvalRequired': row.approval_required, 'status': row.status, 'lastGeneratedAt': row.last_generated_at.isoformat() if row.last_generated_at else None, 'nextGenerationAt': row.next_generation_at.isoformat() if row.next_generation_at else None}

def _ser_gen(row: GeneratedReport) -> dict[str, Any]:
    return {'id': str(row.id), 'scheduledReportId': str(row.scheduled_report_id) if row.scheduled_report_id else None, 'reportType': row.report_type, 'title': row.title, 'outputFormat': row.output_format, 'checksum': row.checksum, 'status': row.status, 'createdAt': row.created_at.isoformat() if row.created_at else None, 'preview': row.content_preview_json}
