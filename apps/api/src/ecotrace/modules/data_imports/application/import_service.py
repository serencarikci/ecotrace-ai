from __future__ import annotations
import csv
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.data_imports.infrastructure.models import ImportJob, ImportJobRow
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.operational_assets.infrastructure.models import DataSource, Equipment, ProductionLine
from ecotrace.modules.reference_data.application.unit_conversion import normalize_quantity
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit
from ecotrace.modules.reporting_periods.application.period_service import assert_period_writable
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_write_operational
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate
REQUIRED_HEADERS = ('facilityCode', 'activityTypeCode', 'activityDate', 'quantity', 'unitCode')
OPTIONAL_HEADERS = ('productionLineCode', 'equipmentCode', 'dataSourceCode', 'reportingPeriodCode', 'periodStart', 'periodEnd', 'sourceReference', 'description', 'notes')
TEMPLATE_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS
CSV_TEMPLATE = ','.join(TEMPLATE_HEADERS) + '\n' + 'IZM-PROD,purchased_electricity,2024-01-15,1250.5,kWh,,,,,2024-01,,INV-001,Demo electricity,Demo notes\n'

class ImportJobResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    file_name: str
    stored_file_name: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    imported_rows: int
    duplicate_rows: int
    started_at: datetime | None
    completed_at: datetime | None
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

class ImportJobRowResponse(CamelModel):
    id: uuid.UUID
    import_job_id: uuid.UUID
    row_number: int
    raw_data_json: dict[str, Any]
    normalized_data_json: dict[str, Any] | None
    validation_status: str
    validation_errors_json: list[Any] | None
    activity_record_id: uuid.UUID | None
    created_at: datetime

def get_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if job is None or job.organization_id != organization_id:
        raise NotFoundError('Import job not found.')
    return job

def list_jobs(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None) -> Page[ImportJobResponse]:
    from sqlalchemy import func
    ensure_org_access(db, user, organization_id)
    stmt = select(ImportJob).where(ImportJob.organization_id == organization_id)
    if status:
        stmt = stmt.where(ImportJob.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ImportJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([ImportJobResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def list_rows(db: Session, user: User, organization_id: uuid.UUID, job_id: uuid.UUID, *, page: int, page_size: int, validation_status: str | None=None) -> Page[ImportJobRowResponse]:
    ensure_org_access(db, user, organization_id)
    get_job(db, organization_id, job_id)
    stmt = select(ImportJobRow).where(ImportJobRow.import_job_id == job_id)
    if validation_status:
        stmt = stmt.where(ImportJobRow.validation_status == validation_status)
    from sqlalchemy import func
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ImportJobRow.row_number).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([ImportJobRowResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def _import_storage_dir(organization_id: uuid.UUID) -> Path:
    settings = get_settings()
    root = Path(settings.attachment_storage_path).resolve() / 'imports' / str(organization_id)
    root.mkdir(parents=True, exist_ok=True)
    return root

def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None

def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationAppError(f"Invalid date for {field}: '{value}'") from exc

def _duplicate_key(*, facility_id: uuid.UUID, activity_type_id: uuid.UUID, activity_date: date | None, period_start: date | None, period_end: date | None, source_reference: str | None, quantity: Decimal, unit_code: str) -> str:
    return '|'.join([str(facility_id), str(activity_type_id), activity_date.isoformat() if activity_date else '', period_start.isoformat() if period_start else '', period_end.isoformat() if period_end else '', source_reference or '', format(quantity, 'f'), unit_code])

def upload_csv(db: Session, user: User, organization_id: uuid.UUID, *, file_name: str, data: bytes, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ImportJobResponse:
    require_write_operational(db, user, organization_id)
    settings = get_settings()
    if not file_name.lower().endswith('.csv'):
        raise ValidationAppError('Only CSV files are accepted.')
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValidationAppError('CSV must be UTF-8 encoded.') from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValidationAppError('CSV header row is missing.')
    headers = [h.strip() for h in reader.fieldnames if h]
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise ValidationAppError('CSV headers are invalid.', details=[{'field': 'headers', 'message': f"Missing: {', '.join(missing)}"}])
    rows = list(reader)
    if len(rows) > settings.max_csv_import_rows:
        raise ValidationAppError(f'CSV exceeds maximum of {settings.max_csv_import_rows} rows.')
    stored_name = f'{uuid.uuid4().hex}.csv'
    path = _import_storage_dir(organization_id) / stored_name
    path.write_bytes(data)
    job = ImportJob(organization_id=organization_id, file_name=Path(file_name).name, stored_file_name=stored_name, status='uploaded', total_rows=len(rows), created_by_user_id=user.id)
    db.add(job)
    db.flush()
    for index, raw in enumerate(rows, start=2):
        cleaned = {k: _norm(v) if isinstance(v, str) else v for k, v in raw.items() if k}
        db.add(ImportJobRow(import_job_id=job.id, row_number=index, raw_data_json=cleaned, validation_status='pending'))
    write_audit_log(db, action='import.uploaded', actor_user_id=user.id, organization_id=organization_id, entity_type='import_job', entity_id=str(job.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fileName': job.file_name, 'totalRows': job.total_rows})
    db.commit()
    db.refresh(job)
    return ImportJobResponse.model_validate(job)

def _lookup_facility(db: Session, organization_id: uuid.UUID, code: str) -> Facility | None:
    return db.execute(select(Facility).where(Facility.organization_id == organization_id, Facility.code == code, Facility.is_active.is_(True))).scalar_one_or_none()

def _lookup_activity_type(db: Session, code: str) -> ActivityType | None:
    return db.execute(select(ActivityType).where(ActivityType.code == code, ActivityType.is_active.is_(True))).scalar_one_or_none()

def _lookup_period(db: Session, organization_id: uuid.UUID, code: str | None, activity_date: date | None) -> ReportingPeriod | None:
    if code:
        return db.execute(select(ReportingPeriod).where(ReportingPeriod.organization_id == organization_id, ReportingPeriod.code == code, ReportingPeriod.status != 'archived')).scalar_one_or_none()
    if activity_date is None:
        return None
    return db.execute(select(ReportingPeriod).where(ReportingPeriod.organization_id == organization_id, ReportingPeriod.status.in_(('open', 'under_review')), ReportingPeriod.start_date <= activity_date, ReportingPeriod.end_date >= activity_date).order_by(ReportingPeriod.start_date.desc()).limit(1)).scalar_one_or_none()

def validate_job(db: Session, user: User, organization_id: uuid.UUID, job_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ImportJobResponse:
    require_write_operational(db, user, organization_id)
    job = get_job(db, organization_id, job_id)
    if job.status in {'importing', 'completed', 'completed_with_errors'}:
        raise BusinessRuleError('Import job can no longer be validated.')
    if job.executed_at is not None:
        raise BusinessRuleError('Import job has already been executed.')
    job.status = 'validating'
    job.started_at = datetime.now(UTC)
    db.flush()
    rows = list(db.execute(select(ImportJobRow).where(ImportJobRow.import_job_id == job.id).order_by(ImportJobRow.row_number)).scalars().all())
    seen_keys: set[str] = set()
    valid = 0
    invalid = 0
    duplicates = 0
    for row in rows:
        errors: list[dict[str, str]] = []
        raw = row.raw_data_json or {}
        facility_code = _norm(raw.get('facilityCode'))
        activity_type_code = _norm(raw.get('activityTypeCode'))
        activity_date_raw = _norm(raw.get('activityDate'))
        quantity_raw = _norm(raw.get('quantity'))
        unit_code = _norm(raw.get('unitCode'))
        period_start_raw = _norm(raw.get('periodStart'))
        period_end_raw = _norm(raw.get('periodEnd'))
        source_reference = _norm(raw.get('sourceReference'))
        production_line_code = _norm(raw.get('productionLineCode'))
        equipment_code = _norm(raw.get('equipmentCode'))
        data_source_code = _norm(raw.get('dataSourceCode'))
        reporting_period_code = _norm(raw.get('reportingPeriodCode'))
        description = _norm(raw.get('description'))
        notes = _norm(raw.get('notes'))
        facility = None
        activity_type = None
        period = None
        quantity: Decimal | None = None
        activity_date: date | None = None
        period_start: date | None = None
        period_end: date | None = None
        production_line_id = None
        equipment_id = None
        data_source_id = None
        normalized_quantity = None
        normalized_unit_code = None
        if not facility_code:
            errors.append({'field': 'facilityCode', 'message': 'Required.'})
        else:
            facility = _lookup_facility(db, organization_id, facility_code)
            if facility is None:
                errors.append({'field': 'facilityCode', 'message': 'Unknown facility code.'})
        if not activity_type_code:
            errors.append({'field': 'activityTypeCode', 'message': 'Required.'})
        else:
            activity_type = _lookup_activity_type(db, activity_type_code)
            if activity_type is None:
                errors.append({'field': 'activityTypeCode', 'message': 'Unknown activity type.'})
        if not unit_code:
            errors.append({'field': 'unitCode', 'message': 'Required.'})
        else:
            unit = db.execute(select(Unit).where(Unit.code == unit_code, Unit.is_active.is_(True))).scalar_one_or_none()
            if unit is None:
                errors.append({'field': 'unitCode', 'message': 'Unknown unit.'})
        if not quantity_raw:
            errors.append({'field': 'quantity', 'message': 'Required.'})
        else:
            try:
                quantity = Decimal(quantity_raw)
                if quantity < 0:
                    errors.append({'field': 'quantity', 'message': 'Must be >= 0.'})
            except InvalidOperation:
                errors.append({'field': 'quantity', 'message': 'Invalid decimal.'})
        try:
            activity_date = _parse_date(activity_date_raw, 'activityDate')
        except ValidationAppError as exc:
            errors.append({'field': 'activityDate', 'message': str(exc.message)})
        if activity_date is None and (not period_start_raw):
            errors.append({'field': 'activityDate', 'message': 'Required when periodStart is empty.'})
        try:
            period_start = _parse_date(period_start_raw, 'periodStart')
            period_end = _parse_date(period_end_raw, 'periodEnd')
        except ValidationAppError as exc:
            errors.append({'field': 'period', 'message': str(exc.message)})
        period = _lookup_period(db, organization_id, reporting_period_code, activity_date or period_start)
        if period is None:
            errors.append({'field': 'reportingPeriodCode', 'message': 'No matching open period.'})
        else:
            try:
                assert_period_writable(period)
            except Exception as exc:
                errors.append({'field': 'reportingPeriodCode', 'message': str(getattr(exc, 'message', exc))})
        if facility and production_line_code:
            line = db.execute(select(ProductionLine).where(ProductionLine.organization_id == organization_id, ProductionLine.facility_id == facility.id, ProductionLine.code == production_line_code, ProductionLine.is_active.is_(True))).scalar_one_or_none()
            if line is None:
                errors.append({'field': 'productionLineCode', 'message': 'Unknown production line.'})
            else:
                production_line_id = line.id
        if facility and equipment_code:
            eq = db.execute(select(Equipment).where(Equipment.organization_id == organization_id, Equipment.facility_id == facility.id, Equipment.code == equipment_code, Equipment.is_active.is_(True))).scalar_one_or_none()
            if eq is None:
                errors.append({'field': 'equipmentCode', 'message': 'Unknown equipment.'})
            else:
                equipment_id = eq.id
        if data_source_code:
            ds = db.execute(select(DataSource).where(DataSource.organization_id == organization_id, DataSource.code == data_source_code, DataSource.is_active.is_(True))).scalar_one_or_none()
            if ds is None:
                errors.append({'field': 'dataSourceCode', 'message': 'Unknown data source.'})
            else:
                data_source_id = ds.id
        if activity_type and quantity is not None and unit_code and (not errors):
            try:
                normalized_quantity, normalized_unit_code = normalize_quantity(db, quantity=quantity, unit_code=unit_code, activity_type=activity_type)
            except Exception as exc:
                errors.append({'field': 'unitCode', 'message': str(getattr(exc, 'message', exc))})
        is_duplicate = False
        if facility and activity_type and (quantity is not None) and unit_code and (not errors):
            key = _duplicate_key(facility_id=facility.id, activity_type_id=activity_type.id, activity_date=activity_date, period_start=period_start, period_end=period_end, source_reference=source_reference, quantity=quantity, unit_code=unit_code)
            if key in seen_keys:
                is_duplicate = True
            else:
                seen_keys.add(key)
                existing = db.execute(select(ActivityRecord.id).where(ActivityRecord.organization_id == organization_id, ActivityRecord.facility_id == facility.id, ActivityRecord.activity_type_id == activity_type.id, ActivityRecord.activity_date == activity_date, ActivityRecord.period_start == period_start, ActivityRecord.period_end == period_end, ActivityRecord.source_reference == source_reference, ActivityRecord.quantity == quantity, ActivityRecord.unit_code == unit_code, ActivityRecord.is_archived.is_(False))).scalar_one_or_none()
                if existing is not None:
                    is_duplicate = True
            if is_duplicate:
                errors.append({'field': 'duplicate', 'message': 'Duplicate activity row detected.'})
                duplicates += 1
        if errors:
            row.validation_status = 'invalid'
            row.validation_errors_json = errors
            row.normalized_data_json = None
            invalid += 1
        else:
            assert facility and activity_type and period and (quantity is not None)
            row.validation_status = 'valid'
            row.validation_errors_json = None
            row.normalized_data_json = {'facilityId': str(facility.id), 'activityTypeId': str(activity_type.id), 'reportingPeriodId': str(period.id), 'productionLineId': str(production_line_id) if production_line_id else None, 'equipmentId': str(equipment_id) if equipment_id else None, 'dataSourceId': str(data_source_id) if data_source_id else None, 'activityDate': activity_date.isoformat() if activity_date else None, 'periodStart': period_start.isoformat() if period_start else None, 'periodEnd': period_end.isoformat() if period_end else None, 'quantity': format(quantity, 'f'), 'unitCode': unit_code, 'normalizedQuantity': format(normalized_quantity, 'f') if normalized_quantity is not None else None, 'normalizedUnitCode': normalized_unit_code, 'sourceReference': source_reference, 'description': description, 'notes': notes}
            valid += 1
    job.valid_rows = valid
    job.invalid_rows = invalid
    job.duplicate_rows = duplicates
    job.status = 'ready' if valid > 0 else 'validation_failed'
    job.completed_at = datetime.now(UTC)
    write_audit_log(db, action='import.validated', actor_user_id=user.id, organization_id=organization_id, entity_type='import_job', entity_id=str(job.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'validRows': valid, 'invalidRows': invalid, 'duplicateRows': duplicates, 'status': job.status})
    db.commit()
    db.refresh(job)
    return ImportJobResponse.model_validate(job)

def execute_job(db: Session, user: User, organization_id: uuid.UUID, job_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ImportJobResponse:
    require_write_operational(db, user, organization_id)
    job = get_job(db, organization_id, job_id)
    if job.executed_at is not None:
        raise ConflictError('Import job has already been executed.')
    if job.status not in {'ready', 'completed_with_errors'}:
        raise BusinessRuleError('Import job must be validated and ready before execution.')
    if job.valid_rows <= 0:
        raise BusinessRuleError('No valid rows to import.')
    job.status = 'importing'
    db.flush()
    imported = 0
    failed = 0
    rows = list(db.execute(select(ImportJobRow).where(ImportJobRow.import_job_id == job.id, ImportJobRow.validation_status == 'valid', ImportJobRow.activity_record_id.is_(None))).scalars().all())
    try:
        for row in rows:
            data = row.normalized_data_json or {}
            record = ActivityRecord(organization_id=organization_id, facility_id=uuid.UUID(data['facilityId']), production_line_id=uuid.UUID(data['productionLineId']) if data.get('productionLineId') else None, equipment_id=uuid.UUID(data['equipmentId']) if data.get('equipmentId') else None, data_source_id=uuid.UUID(data['dataSourceId']) if data.get('dataSourceId') else None, activity_type_id=uuid.UUID(data['activityTypeId']), reporting_period_id=uuid.UUID(data['reportingPeriodId']), activity_date=date.fromisoformat(data['activityDate']) if data.get('activityDate') else None, period_start=date.fromisoformat(data['periodStart']) if data.get('periodStart') else None, period_end=date.fromisoformat(data['periodEnd']) if data.get('periodEnd') else None, quantity=Decimal(data['quantity']), unit_code=data['unitCode'], normalized_quantity=Decimal(data['normalizedQuantity']), normalized_unit_code=data['normalizedUnitCode'], status='draft', source_reference=data.get('sourceReference'), description=data.get('description'), notes=data.get('notes'), metadata_json={'importJobId': str(job.id), 'importRowNumber': row.row_number}, created_by_user_id=user.id, updated_by_user_id=user.id, row_version=1, is_archived=False)
            db.add(record)
            db.flush()
            row.activity_record_id = record.id
            imported += 1
        job.imported_rows = imported
        job.executed_at = datetime.now(UTC)
        job.completed_at = datetime.now(UTC)
        job.status = 'completed' if failed == 0 and job.invalid_rows == 0 else 'completed_with_errors'
        write_audit_log(db, action='import.executed', actor_user_id=user.id, organization_id=organization_id, entity_type='import_job', entity_id=str(job.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'importedRows': imported})
        db.commit()
    except Exception:
        db.rollback()
        job = get_job(db, organization_id, job_id)
        job.status = 'failed'
        write_audit_log(db, action='import.failed', actor_user_id=user.id, organization_id=organization_id, entity_type='import_job', entity_id=str(job.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={})
        db.commit()
        raise
    db.refresh(job)
    return ImportJobResponse.model_validate(job)
