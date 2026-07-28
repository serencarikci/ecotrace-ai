from __future__ import annotations
import csv
import io
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ValidationAppError
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactor, EmissionFactorImportJob, EmissionFactorSource
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_system_admin
from ecotrace.shared.domain.schemas import CamelModel
REQUIRED_COLUMNS = ['sourceCode', 'factorCode', 'factorName', 'activityTypeCode', 'scope', 'category', 'unitCode', 'factorValue', 'geographyCode', 'validFrom', 'validTo', 'version']
TEMPLATE_CSV = 'sourceCode,factorCode,factorName,activityTypeCode,scope,category,unitCode,factorValue,geographyCode,validFrom,validTo,version,subcategory,co2Factor,ch4Factor,n2oFactor,uncertaintyPercentage,methodology,metadata\nDEMO_GRID,EF-ELEC-TR-DEMO,Demo TR Electricity,purchased_electricity,scope_2,purchased_electricity,kWh,0.442,TR,2024-01-01,2024-12-31,1,,,,,\n'

class FactorImportResult(CamelModel):
    id: uuid.UUID
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    created_count: int
    error_summary_json: list[Any] | dict[str, Any] | None

def get_template() -> str:
    return TEMPLATE_CSV

def _parse_date(value: str | None) -> date | None:
    if value is None or value.strip() == '':
        return None
    return date.fromisoformat(value.strip())

def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None or value.strip() == '':
        return None
    return Decimal(value.strip())

def validate_and_import(db: Session, user: User, *, filename: str, content: bytes, execute: bool=False, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorImportResult:
    require_system_admin(user, message='Only system administrators may import emission factors.')
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValidationAppError('CSV must be UTF-8 encoded.') from exc
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValidationAppError('CSV has no header row.')
    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise ValidationAppError('CSV is missing required columns.', details=[{'field': c, 'message': 'Required'} for c in missing])
    sources = {s.code: s for s in db.execute(select(EmissionFactorSource)).scalars().all()}
    activity_types = {a.code: a for a in db.execute(select(ActivityType)).scalars().all()}
    units = {u.code: u for u in db.execute(select(Unit).where(Unit.is_active.is_(True))).scalars().all()}
    errors: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for idx, row in enumerate(reader, start=2):
        row_errors: list[str] = []
        source_code = (row.get('sourceCode') or '').strip()
        factor_code = (row.get('factorCode') or '').strip()
        try:
            version = int((row.get('version') or '').strip())
        except ValueError:
            version = -1
            row_errors.append('version must be an integer')
        if source_code not in sources:
            row_errors.append(f"Unknown sourceCode '{source_code}'")
        activity_code = (row.get('activityTypeCode') or '').strip()
        if activity_code not in activity_types:
            row_errors.append(f"Unknown activityTypeCode '{activity_code}'")
        unit_code = (row.get('unitCode') or '').strip()
        if unit_code not in units:
            row_errors.append(f"Unknown unitCode '{unit_code}'")
        elif activity_code in activity_types and units[unit_code].dimension != activity_types[activity_code].allowed_unit_dimension:
            row_errors.append('unitCode dimension incompatible with activity type')
        try:
            factor_value = _parse_decimal(row.get('factorValue'))
            co2 = _parse_decimal(row.get('co2Factor'))
            ch4 = _parse_decimal(row.get('ch4Factor'))
            n2o = _parse_decimal(row.get('n2oFactor'))
            unc = _parse_decimal(row.get('uncertaintyPercentage'))
        except (InvalidOperation, ValueError):
            factor_value = co2 = ch4 = n2o = unc = None
            row_errors.append('Invalid numeric factor value')
        try:
            valid_from = _parse_date(row.get('validFrom'))
            valid_to = _parse_date(row.get('validTo'))
        except ValueError:
            valid_from = valid_to = None
            row_errors.append('Invalid date format (YYYY-MM-DD)')
        if valid_from and valid_to and (valid_to < valid_from):
            row_errors.append('validTo earlier than validFrom')
        if factor_value is None and co2 is None and (ch4 is None) and (n2o is None):
            row_errors.append('factorValue or gas factors required')
        if any((v is not None and v < 0 for v in (factor_value, co2, ch4, n2o))):
            row_errors.append('Factor values must be non-negative')
        key = (factor_code, version)
        if key in seen_keys:
            row_errors.append('Duplicate code+version in file')
        seen_keys.add(key)
        existing = db.execute(select(EmissionFactor).where(EmissionFactor.code == factor_code, EmissionFactor.version == version)).scalar_one_or_none()
        if existing:
            row_errors.append('Factor code+version already exists')
        if row_errors:
            errors.append({'row': idx, 'errors': row_errors})
            continue
        valid_rows.append({'source_id': sources[source_code].id, 'code': factor_code, 'name': (row.get('factorName') or '').strip(), 'activity_type_id': activity_types[activity_code].id, 'scope': (row.get('scope') or '').strip(), 'category': (row.get('category') or '').strip(), 'subcategory': (row.get('subcategory') or '').strip() or None, 'unit_code': unit_code, 'factor_value': factor_value, 'co2_factor': co2, 'ch4_factor': ch4, 'n2o_factor': n2o, 'uncertainty_percentage': unc, 'geography_code': (row.get('geographyCode') or 'GLOBAL').strip().upper(), 'valid_from': valid_from, 'valid_to': valid_to, 'version': version, 'metadata_json': {'imported': True, 'methodology': (row.get('methodology') or '').strip() or None, 'disclaimer': 'Demo/reference data — not for regulatory reporting.', 'rawMetadata': (row.get('metadata') or '').strip() or None}})
    job = EmissionFactorImportJob(uploaded_by_user_id=user.id, original_filename=filename, status='validated' if not errors else 'validation_failed', total_rows=len(valid_rows) + len(errors), valid_rows=len(valid_rows), invalid_rows=len(errors), created_count=0, error_summary_json=errors)
    db.add(job)
    db.flush()
    created = 0
    if execute:
        if errors:
            raise BusinessRuleError('Cannot execute import while row-level errors exist.')
        for payload in valid_rows:
            db.add(EmissionFactor(**payload, status='draft', is_active=False, is_demo=True, description='Imported draft factor (demo).'))
            created += 1
        job.status = 'executed'
        job.created_count = created
        job.executed_at = datetime.now(UTC)
        write_audit_log(db, action='factor.import_executed', actor_user_id=user.id, entity_type='emission_factor_import_job', entity_id=str(job.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'created': created, 'filename': filename})
    db.commit()
    db.refresh(job)
    return FactorImportResult(id=job.id, status=job.status, total_rows=job.total_rows, valid_rows=job.valid_rows, invalid_rows=job.invalid_rows, created_count=job.created_count, error_summary_json=job.error_summary_json)
