from __future__ import annotations
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import JobExecution
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_manage, require_automation_read

def list_jobs(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(JobExecution).where(JobExecution.organization_id == organization_id).order_by(JobExecution.created_at.desc()).limit(200)).scalars()
    return [_ser(r) for r in rows]

def get_job(db: Session, user: User, organization_id: uuid.UUID, execution_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser(_get(db, organization_id, execution_id))

def retry_job(db: Session, user: User, organization_id: uuid.UUID, execution_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get(db, organization_id, execution_id)
    if row.status not in {'failed', 'timed_out'}:
        raise ValidationAppError('Only failed/timed_out jobs can be retried.')
    if row.attempt_number >= row.max_attempts:
        raise ValidationAppError('Maximum retry attempts exceeded.')
    settings = get_settings()
    backoff = min(300, 2 ** row.attempt_number)
    row.attempt_number += 1
    row.status = 'retrying'
    row.scheduled_for = datetime.now(UTC) + timedelta(seconds=backoff)
    row.error_details_json = {**(row.error_details_json or {}), 'retryScheduledInSeconds': backoff, 'maxAttempts': settings.job_max_attempts}
    write_audit_log(db, action='job.retried', actor_user_id=user.id, organization_id=organization_id, entity_type='job_execution', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def cancel_job(db: Session, user: User, organization_id: uuid.UUID, execution_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get(db, organization_id, execution_id)
    if row.status in {'completed', 'cancelled'}:
        raise ValidationAppError('Job cannot be cancelled.')
    row.status = 'cancelled'
    row.completed_at = datetime.now(UTC)
    write_audit_log(db, action='job.cancelled', actor_user_id=user.id, organization_id=organization_id, entity_type='job_execution', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def try_acquire_lock(db: Session, job: JobExecution, worker_id: str) -> bool:
    if job.locked_at and job.locked_at > datetime.now(UTC) - timedelta(minutes=10) and job.worker_id and (job.worker_id != worker_id) and (job.status == 'running'):
        return False
    job.locked_at = datetime.now(UTC)
    job.worker_id = worker_id
    job.status = 'running'
    job.started_at = datetime.now(UTC)
    db.flush()
    return True

def recent_failures(db: Session, user: User, *, limit: int=20) -> list[dict[str, Any]]:
    from ecotrace.shared.application.org_access import require_system_admin
    require_system_admin(user)
    rows = db.execute(select(JobExecution).where(JobExecution.status.in_(['failed', 'timed_out'])).order_by(JobExecution.created_at.desc()).limit(limit)).scalars()
    return [_ser(r) for r in rows]

def _get(db: Session, organization_id: uuid.UUID, execution_id: uuid.UUID) -> JobExecution:
    row = db.execute(select(JobExecution).where(JobExecution.id == execution_id, JobExecution.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Job execution not found.')
    return row

def _ser(row: JobExecution) -> dict[str, Any]:
    return {'id': str(row.id), 'jobType': row.job_type, 'jobReferenceId': str(row.job_reference_id) if row.job_reference_id else None, 'executionKey': row.execution_key, 'status': row.status, 'scheduledFor': row.scheduled_for.isoformat() if row.scheduled_for else None, 'startedAt': row.started_at.isoformat() if row.started_at else None, 'completedAt': row.completed_at.isoformat() if row.completed_at else None, 'attemptNumber': row.attempt_number, 'maxAttempts': row.max_attempts, 'workerId': row.worker_id, 'resultSummary': row.result_summary_json, 'errorDetails': row.error_details_json, 'traceId': row.trace_id}
