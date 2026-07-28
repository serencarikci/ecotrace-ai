from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.constants import DEFAULT_ROLES, ROLE_ANALYST, ROLE_ORGANIZATION_ADMIN, ROLE_SYSTEM_ADMIN, ROLE_VIEWER
from ecotrace.core.database import get_session_factory, init_db
from ecotrace.core.logging import configure_logging, get_logger
from ecotrace.core.security import hash_password, normalize_email
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import Role, User, UserRole
from ecotrace.modules.operational_assets.infrastructure.models import DataSource, Equipment, ProductionLine
from ecotrace.modules.organizations.infrastructure.models import Organization, OrganizationMembership
from ecotrace.modules.reference_data.application.unit_conversion import normalize_quantity
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
logger = get_logger(__name__)
DEMO_ORG_NAME = 'EcoTrace Demo Industries'
DEMO_ORG_SLUG = 'ecotrace-demo-industries'
SEED_UNITS: list[dict[str, object]] = [{'code': 'kWh', 'name': 'Kilowatt hour', 'symbol': 'kWh', 'dimension': 'energy', 'factor': '1', 'base': 'kWh', 'precision': 4}, {'code': 'MWh', 'name': 'Megawatt hour', 'symbol': 'MWh', 'dimension': 'energy', 'factor': '1000', 'base': 'kWh', 'precision': 6}, {'code': 'GJ', 'name': 'Gigajoule', 'symbol': 'GJ', 'dimension': 'energy', 'factor': '277.777777778', 'base': 'kWh', 'precision': 6}, {'code': 'MJ', 'name': 'Megajoule', 'symbol': 'MJ', 'dimension': 'energy', 'factor': '0.277777778', 'base': 'kWh', 'precision': 6}, {'code': 'L', 'name': 'Litre', 'symbol': 'L', 'dimension': 'volume', 'factor': '0.001', 'base': 'm3', 'precision': 4}, {'code': 'm3', 'name': 'Cubic metre', 'symbol': 'm³', 'dimension': 'volume', 'factor': '1', 'base': 'm3', 'precision': 4}, {'code': 'g', 'name': 'Gram', 'symbol': 'g', 'dimension': 'mass', 'factor': '0.001', 'base': 'kg', 'precision': 4}, {'code': 'kg', 'name': 'Kilogram', 'symbol': 'kg', 'dimension': 'mass', 'factor': '1', 'base': 'kg', 'precision': 4}, {'code': 't', 'name': 'Tonne', 'symbol': 't', 'dimension': 'mass', 'factor': '1000', 'base': 'kg', 'precision': 6}, {'code': 'km', 'name': 'Kilometre', 'symbol': 'km', 'dimension': 'distance', 'factor': '1', 'base': 'km', 'precision': 4}, {'code': 'tonne_km', 'name': 'Tonne kilometre', 'symbol': 't·km', 'dimension': 'transport_work', 'factor': '1', 'base': 'tonne_km', 'precision': 4}, {'code': 'unit', 'name': 'Unit count', 'symbol': 'u', 'dimension': 'count', 'factor': '1', 'base': 'unit', 'precision': 0}, {'code': 'hour', 'name': 'Hour', 'symbol': 'h', 'dimension': 'time', 'factor': '1', 'base': 'hour', 'precision': 4}, {'code': 'day', 'name': 'Day', 'symbol': 'd', 'dimension': 'time', 'factor': '24', 'base': 'hour', 'precision': 4}, {'code': 'percent', 'name': 'Percent', 'symbol': '%', 'dimension': 'percentage', 'factor': '1', 'base': 'percent', 'precision': 2}]
SEED_ACTIVITY_TYPES: list[dict[str, object]] = [{'code': 'purchased_electricity', 'name': 'Purchased electricity', 'category': 'electricity', 'unit': 'kWh', 'dimension': 'energy'}, {'code': 'generated_electricity', 'name': 'Generated electricity', 'category': 'electricity', 'unit': 'kWh', 'dimension': 'energy'}, {'code': 'natural_gas_consumption', 'name': 'Natural gas consumption', 'category': 'natural_gas', 'unit': 'm3', 'dimension': 'volume'}, {'code': 'diesel_consumption', 'name': 'Diesel consumption', 'category': 'stationary_fuel', 'unit': 'L', 'dimension': 'volume'}, {'code': 'gasoline_consumption', 'name': 'Gasoline consumption', 'category': 'mobile_fuel', 'unit': 'L', 'dimension': 'volume'}, {'code': 'lpg_consumption', 'name': 'LPG consumption', 'category': 'stationary_fuel', 'unit': 'kg', 'dimension': 'mass'}, {'code': 'water_consumption', 'name': 'Water consumption', 'category': 'water', 'unit': 'm3', 'dimension': 'volume'}, {'code': 'wastewater_volume', 'name': 'Wastewater volume', 'category': 'water', 'unit': 'm3', 'dimension': 'volume'}, {'code': 'hazardous_waste', 'name': 'Hazardous waste', 'category': 'waste', 'unit': 'kg', 'dimension': 'mass'}, {'code': 'non_hazardous_waste', 'name': 'Non-hazardous waste', 'category': 'waste', 'unit': 'kg', 'dimension': 'mass'}, {'code': 'recycled_waste', 'name': 'Recycled waste', 'category': 'waste', 'unit': 'kg', 'dimension': 'mass'}, {'code': 'road_freight', 'name': 'Road freight', 'category': 'transport', 'unit': 'tonne_km', 'dimension': 'transport_work'}, {'code': 'air_travel', 'name': 'Air travel', 'category': 'transport', 'unit': 'km', 'dimension': 'distance'}, {'code': 'employee_commuting', 'name': 'Employee commuting', 'category': 'transport', 'unit': 'km', 'dimension': 'distance'}, {'code': 'production_output', 'name': 'Production output', 'category': 'production_output', 'unit': 'unit', 'dimension': 'count'}, {'code': 'refrigerant_refill', 'name': 'Refrigerant refill', 'category': 'refrigerant', 'unit': 'kg', 'dimension': 'mass'}]

def seed_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for code, name, description in DEFAULT_ROLES:
        existing = db.execute(select(Role).where(Role.code == code)).scalar_one_or_none()
        if existing is None:
            existing = Role(id=uuid.uuid4(), code=code, name=name, description=description)
            db.add(existing)
            db.flush()
            logger.info('seed.role_created', code=code)
        else:
            existing.name = name
            existing.description = description
        roles[code] = existing
    return roles

def upsert_user(db: Session, *, email: str, full_name: str, password: str, role: Role, is_verified: bool=True) -> User:
    normalized = normalize_email(email)
    user = db.execute(select(User).where(User.normalized_email == normalized)).scalar_one_or_none()
    if user is None:
        user = User(id=uuid.uuid4(), email=email.strip(), normalized_email=normalized, full_name=full_name, hashed_password=hash_password(password), is_active=True, is_verified=is_verified)
        db.add(user)
        db.flush()
        logger.info('seed.user_created', email=normalized)
    else:
        user.email = email.strip()
        user.full_name = full_name
        user.is_active = True
        user.is_verified = is_verified
    has_role = db.execute(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)).scalar_one_or_none()
    if has_role is None:
        db.add(UserRole(id=uuid.uuid4(), user_id=user.id, role_id=role.id))
        db.flush()
    return user

def seed_demo_organization(db: Session) -> Organization:
    org = db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one_or_none()
    if org is None:
        org = Organization(id=uuid.uuid4(), name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG, legal_name='EcoTrace Demo Industries Ltd.', country_code='DE', timezone='Europe/Berlin', is_active=True)
        db.add(org)
        db.flush()
        logger.info('seed.organization_created', slug=DEMO_ORG_SLUG)
    else:
        org.name = DEMO_ORG_NAME
        org.legal_name = 'EcoTrace Demo Industries Ltd.'
        org.is_active = True
    return org

def ensure_membership(db: Session, *, organization: Organization, user: User, role: Role) -> None:
    existing = db.execute(select(OrganizationMembership).where(OrganizationMembership.organization_id == organization.id, OrganizationMembership.user_id == user.id)).scalar_one_or_none()
    if existing is None:
        db.add(OrganizationMembership(id=uuid.uuid4(), organization_id=organization.id, user_id=user.id, role_id=role.id, is_active=True))
        db.flush()
        logger.info('seed.membership_created', user=user.normalized_email, role=role.code)
    else:
        existing.role_id = role.id
        existing.is_active = True

def seed_units(db: Session) -> dict[str, Unit]:
    units: dict[str, Unit] = {}
    for item in SEED_UNITS:
        code = str(item['code'])
        existing = db.execute(select(Unit).where(Unit.code == code)).scalar_one_or_none()
        if existing is None:
            existing = Unit(code=code, name=str(item['name']), symbol=str(item['symbol']), dimension=str(item['dimension']), conversion_factor_to_base=Decimal(str(item['factor'])), base_unit_code=str(item['base']), decimal_precision=int(str(item['precision'])), is_active=True)
            db.add(existing)
            db.flush()
            logger.info('seed.unit_created', code=code)
        else:
            existing.name = str(item['name'])
            existing.symbol = str(item['symbol'])
            existing.is_active = True
        units[code] = existing
    return units

def seed_activity_types(db: Session) -> dict[str, ActivityType]:
    types: dict[str, ActivityType] = {}
    for item in SEED_ACTIVITY_TYPES:
        code = str(item['code'])
        existing = db.execute(select(ActivityType).where(ActivityType.code == code)).scalar_one_or_none()
        if existing is None:
            existing = ActivityType(code=code, name=str(item['name']), description=None, category=str(item['category']), default_unit_code=str(item['unit']), allowed_unit_dimension=str(item['dimension']), expected_value_type='decimal', data_frequency='monthly', requires_facility=True, requires_equipment=False, is_active=True)
            db.add(existing)
            db.flush()
            logger.info('seed.activity_type_created', code=code)
        else:
            existing.name = str(item['name'])
            existing.is_active = True
        types[code] = existing
    return types

def _upsert_facility(db: Session, org: Organization, *, code: str, name: str, city: str, facility_type: str='manufacturing') -> Facility:
    existing = db.execute(select(Facility).where(Facility.organization_id == org.id, Facility.code == code)).scalar_one_or_none()
    if existing is None:
        existing = Facility(organization_id=org.id, code=code, name=name, description=f'Demo facility in {city}', facility_type=facility_type, country_code='TR', city=city, timezone='Europe/Istanbul', is_active=True)
        db.add(existing)
        db.flush()
        logger.info('seed.facility_created', code=code)
    else:
        existing.name = name
        existing.city = city
        existing.is_active = True
    return existing

def _upsert_line(db: Session, org: Organization, facility: Facility, *, code: str, name: str) -> ProductionLine:
    existing = db.execute(select(ProductionLine).where(ProductionLine.facility_id == facility.id, ProductionLine.code == code)).scalar_one_or_none()
    if existing is None:
        existing = ProductionLine(organization_id=org.id, facility_id=facility.id, code=code, name=name, production_category='general', capacity_value=Decimal('1000'), capacity_unit_code='unit', is_active=True)
        db.add(existing)
        db.flush()
    else:
        existing.name = name
        existing.is_active = True
    return existing

def _upsert_equipment(db: Session, org: Organization, facility: Facility, line: ProductionLine | None, *, code: str, name: str, equipment_type: str) -> Equipment:
    existing = db.execute(select(Equipment).where(Equipment.facility_id == facility.id, Equipment.code == code)).scalar_one_or_none()
    if existing is None:
        existing = Equipment(organization_id=org.id, facility_id=facility.id, production_line_id=line.id if line else None, code=code, name=name, equipment_type=equipment_type, is_active=True)
        db.add(existing)
        db.flush()
    else:
        existing.name = name
        existing.is_active = True
    return existing

def _upsert_data_source(db: Session, org: Organization, facility: Facility, equipment: Equipment | None, *, code: str, name: str, source_type: str) -> DataSource:
    existing = db.execute(select(DataSource).where(DataSource.organization_id == org.id, DataSource.code == code)).scalar_one_or_none()
    if existing is None:
        existing = DataSource(organization_id=org.id, facility_id=facility.id, equipment_id=equipment.id if equipment else None, code=code, name=name, source_type=source_type, is_active=True)
        db.add(existing)
        db.flush()
    else:
        existing.name = name
        existing.is_active = True
    return existing

def _upsert_period(db: Session, org: Organization, *, code: str, name: str, period_type: str, start: date, end: date, status: str='open') -> ReportingPeriod:
    existing = db.execute(select(ReportingPeriod).where(ReportingPeriod.organization_id == org.id, ReportingPeriod.code == code)).scalar_one_or_none()
    if existing is None:
        existing = ReportingPeriod(organization_id=org.id, code=code, name=name, period_type=period_type, start_date=start, end_date=end, status=status)
        db.add(existing)
        db.flush()
        logger.info('seed.period_created', code=code)
    else:
        existing.name = name
        if existing.status != 'locked':
            existing.status = status
    return existing

def seed_ops(db: Session, org: Organization, analyst: User) -> None:
    seed_units(db)
    activity_types = seed_activity_types(db)
    izmir = _upsert_facility(db, org, code='IZM-PROD', name='İzmir Production Plant', city='İzmir')
    manisa = _upsert_facility(db, org, code='MAN-WH', name='Manisa Logistics Warehouse', city='Manisa', facility_type='warehouse')
    line_a = _upsert_line(db, org, izmir, code='FERM-01', name='Fermentation Line')
    line_b = _upsert_line(db, org, izmir, code='PACK-01', name='Packaging Line')
    _upsert_line(db, org, manisa, code='DOCK-1', name='Loading Dock 1')
    meter = _upsert_equipment(db, org, izmir, line_a, code='EM-01', name='Main Electricity Meter', equipment_type='electricity_meter')
    boiler = _upsert_equipment(db, org, izmir, line_b, code='BL-01', name='Process Boiler', equipment_type='boiler')
    _upsert_equipment(db, org, manisa, None, code='VH-01', name='Warehouse Forklift', equipment_type='vehicle')
    manual_src = _upsert_data_source(db, org, izmir, meter, code='SRC-MANUAL', name='Manual meter reading', source_type='manual_entry')
    csv_src = _upsert_data_source(db, org, izmir, boiler, code='SRC-CSV', name='CSV utility import', source_type='csv_import')
    _upsert_data_source(db, org, manisa, None, code='SRC-INVOICE', name='Utility invoice', source_type='utility_invoice')
    period_jan = _upsert_period(db, org, code='2024-01', name='January 2024', period_type='monthly', start=date(2024, 1, 1), end=date(2024, 1, 31), status='open')
    _upsert_period(db, org, code='2024-02', name='February 2024', period_type='monthly', start=date(2024, 2, 1), end=date(2024, 2, 29), status='open')
    _upsert_period(db, org, code='2024-03', name='March 2024', period_type='monthly', start=date(2024, 3, 1), end=date(2024, 3, 31), status='open')
    period_q1 = _upsert_period(db, org, code='2024-Q1', name='Q1 2024', period_type='quarterly', start=date(2024, 1, 1), end=date(2024, 3, 31), status='open')
    _upsert_period(db, org, code='2023', name='Annual 2023', period_type='annual', start=date(2023, 1, 1), end=date(2023, 12, 31), status='locked')
    samples = [('draft', Decimal('1250.50'), 'kWh', 'purchased_electricity', period_jan, date(2024, 1, 15)), ('submitted', Decimal('320.00'), 'm3', 'natural_gas_consumption', period_jan, date(2024, 1, 20)), ('approved', Decimal('45.00'), 'L', 'diesel_consumption', period_q1, date(2024, 2, 5)), ('rejected', Decimal('12.5'), 'kg', 'hazardous_waste', period_jan, date(2024, 1, 28))]
    for status, quantity, unit_code, type_code, period, activity_date in samples:
        marker = f'seed:{type_code}:{status}'
        existing = db.execute(select(ActivityRecord).where(ActivityRecord.organization_id == org.id, ActivityRecord.source_reference == marker)).scalar_one_or_none()
        activity_type = activity_types[type_code]
        if existing is None:
            normalized, normalized_unit = normalize_quantity(db, quantity=quantity, unit_code=unit_code, activity_type=activity_type)
            existing = ActivityRecord(organization_id=org.id, facility_id=izmir.id, production_line_id=line_a.id, equipment_id=meter.id, data_source_id=manual_src.id if status != 'approved' else csv_src.id, activity_type_id=activity_type.id, reporting_period_id=period.id, activity_date=activity_date, quantity=quantity, unit_code=unit_code, normalized_quantity=normalized, normalized_unit_code=normalized_unit, status=status, source_reference=marker, description=f'Seed {status} sample', rejection_reason='Incomplete meter photo' if status == 'rejected' else None, created_by_user_id=analyst.id, updated_by_user_id=analyst.id, row_version=1, is_archived=False)
            db.add(existing)
            db.flush()
            logger.info('seed.activity_record_created', status=status, type=type_code)
        else:
            existing.status = status
            existing.is_archived = False

def run_seed(db: Session | None=None) -> None:
    settings = get_settings()
    own_session = db is None
    if db is None:
        init_db(settings)
        session: Session = get_session_factory()()
    else:
        session = db
    try:
        roles = seed_roles(session)
        org = seed_demo_organization(session)
        admin = upsert_user(session, email=settings.initial_admin_email, full_name=settings.initial_admin_full_name, password=settings.initial_admin_password, role=roles[ROLE_SYSTEM_ADMIN])
        org_admin = upsert_user(session, email=settings.demo_org_admin_email, full_name='Demo Organization Admin', password=settings.demo_org_admin_password, role=roles[ROLE_ORGANIZATION_ADMIN])
        analyst = upsert_user(session, email=settings.demo_analyst_email, full_name='Demo Analyst', password=settings.demo_analyst_password, role=roles[ROLE_ANALYST])
        viewer = upsert_user(session, email=settings.demo_viewer_email, full_name='Demo Viewer', password=settings.demo_viewer_password, role=roles[ROLE_VIEWER])
        ensure_membership(session, organization=org, user=admin, role=roles[ROLE_SYSTEM_ADMIN])
        ensure_membership(session, organization=org, user=org_admin, role=roles[ROLE_ORGANIZATION_ADMIN])
        ensure_membership(session, organization=org, user=analyst, role=roles[ROLE_ANALYST])
        ensure_membership(session, organization=org, user=viewer, role=roles[ROLE_VIEWER])
        seed_ops(session, org, analyst)
        from ecotrace.db.seed_carbon import seed_carbon
        seed_carbon(session, org, org_admin)
        from ecotrace.db.seed_analytics import seed_analytics
        seed_analytics(session, org, org_admin)
        from ecotrace.db.seed_lca import seed_lca
        seed_lca(session, org, org_admin)
        from ecotrace.db.seed_ai import seed_ai
        seed_ai(session, org, org_admin)
        from ecotrace.db.seed_phase7 import seed_phase7
        seed_phase7(session, org, org_admin)
        session.commit()
        logger.info('seed.completed')
    except Exception:
        session.rollback()
        raise
    finally:
        if own_session:
            session.close()

def main() -> None:
    configure_logging()
    run_seed()
if __name__ == '__main__':
    main()
