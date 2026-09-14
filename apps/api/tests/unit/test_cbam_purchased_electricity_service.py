"""Phase 8A purchased-electricity service / API behavior tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.helpers import api_login, auth_headers, current_org_id

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, ValidationAppError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    factor_catalog_service,
    installation_service,
    period_binding_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_electricity_constants import (
    FACTOR_DEFINITION_CODE,
    TURKEY_DEFAULT_FACTOR_SEED_BLOCKER,
)
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    PurchasedElectricityExecuteRequest,
    PurchasedElectricityManualFactor,
    execute_purchased_electricity,
    get_purchased_electricity_result,
    get_purchased_electricity_summary,
    resolve_platform_default_factor,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamFactorDefinition,
    CbamFactorValue,
    CbamPurchasedElectricityCurrentResult,
    CbamPurchasedElectricityResult,
    CbamReferenceSource,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _org(db: Session) -> Organization:
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db: Session) -> User:
    return db.execute(
        select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
    ).scalar_one()


def _setup(db: Session, *, qty: Decimal = Decimal('100'), unit: str = 'MWh'):
    user = _admin(db)
    organization = _org(db)
    facility = db.execute(
        select(Facility).where(Facility.organization_id == organization.id).limit(1)
    ).scalar_one()
    inst = installation_service.create_installation(
        db,
        user,
        organization.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'PE-{uuid.uuid4().hex[:8]}',
            name='PE Install',
        ),
    )
    period = ReportingPeriod(
        organization_id=organization.id,
        code=f'PEP-{uuid.uuid4().hex[:6]}',
        name='PE Period',
        period_type='custom',
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        status='open',
    )
    db.add(period)
    db.flush()
    binding = period_binding_service.create_period_binding(
        db,
        user,
        organization.id,
        PeriodBindingCreate(reporting_period_id=period.id),
    )
    opened = period_binding_service.open_data_collection(
        db,
        user,
        organization.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    activity = activity_record_service.create_activity_record(
        db,
        user,
        organization.id,
        opened.id,
        ActivityRecordCreate(
            installation_profile_id=inst.id,
            activity_type='ELECTRICITY',
            activity_date=date(2024, 6, 15),
            quantity=qty,
            unit=unit,
            data_source_type='PRIMARY',
        ),
    )
    db.commit()
    return user, organization, opened, activity


def _manual_factor(**overrides) -> PurchasedElectricityManualFactor:
    data = {
        'value': Decimal('0.439'),
        'unit': 'tCO2e/MWh',
        'source_name': 'Org verified grid factor',
        'source_document': 'Supplier declaration 2024',
        'dataset_version': 'ORG-2024-01',
        'reference_description': 'Manual org factor with provenance',
        'effective_date': date(2024, 1, 1),
    }
    data.update(overrides)
    return PurchasedElectricityManualFactor(**data)


def _platform_default_source(db: Session) -> CbamReferenceSource:
    return db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == 'MANUAL_APPROVED_REFERENCE',
        )
    ).scalar_one()


def _electricity_definition(db: Session) -> CbamFactorDefinition:
    factor_catalog_service.ensure_platform_factor_catalog(db)
    return db.execute(
        select(CbamFactorDefinition).where(CbamFactorDefinition.code == FACTOR_DEFINITION_CODE)
    ).scalar_one()


def _activate_platform_electricity_factor(
    db: Session,
    user: User,
    org_id: uuid.UUID,
    *,
    value: Decimal,
    valid_from: date | None,
    valid_until: date | None,
    source_reference: str,
) -> None:
    """Insert ACTIVE platform-scoped DEFAULT_REFERENCE (API cannot activate platform rows)."""
    del org_id  # unused; platform rows are org-null
    definition = _electricity_definition(db)
    row = CbamFactorValue(
        organization_id=None,
        factor_definition_id=definition.id,
        reference_source_id=_platform_default_source(db).id,
        activity_type='ELECTRICITY',
        numeric_value=value,
        unit='tCO2e/MWh',
        valid_from=valid_from,
        valid_until=valid_until,
        data_source_type='DEFAULT_REFERENCE',
        source_reference=source_reference,
        notes='Temporary test platform electricity factor',
        supplier_name='TEST_PLATFORM_DEFAULT',
        facility_specific=False,
        status='ACTIVE',
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.commit()


def test_factor_effective_date_resolution(seeded_db: Session) -> None:
    user, org, _binding, _activity = _setup(seeded_db)
    _activate_platform_electricity_factor(
        seeded_db,
        user,
        org.id,
        value=Decimal('0.41'),
        valid_from=date(2024, 1, 1),
        valid_until=date(2024, 12, 31),
        source_reference='TEST-EF-2024',
    )
    inside = resolve_platform_default_factor(seeded_db, reference_date=date(2024, 6, 15))
    assert inside.resolved is True
    assert inside.factor_value == Decimal('0.41')
    outside = resolve_platform_default_factor(seeded_db, reference_date=date(2025, 1, 1))
    assert outside.resolved is False
    assert 'UNRESOLVED_PLATFORM_DEFAULT' in outside.blocking_issue_codes


def test_factor_ambiguity_fails_closed(seeded_db: Session) -> None:
    user, org, _binding, _activity = _setup(seeded_db)
    _activate_platform_electricity_factor(
        seeded_db,
        user,
        org.id,
        value=Decimal('0.41'),
        valid_from=date(2024, 1, 1),
        valid_until=date(2024, 12, 31),
        source_reference='TEST-EF-A',
    )
    _activate_platform_electricity_factor(
        seeded_db,
        user,
        org.id,
        value=Decimal('0.42'),
        valid_from=date(2024, 1, 1),
        valid_until=date(2024, 12, 31),
        source_reference='TEST-EF-B',
    )
    resolved = resolve_platform_default_factor(seeded_db, reference_date=date(2024, 6, 15))
    assert resolved.resolved is False
    assert 'AMBIGUOUS_PLATFORM_DEFAULT' in resolved.blocking_issue_codes


def test_exported_electricity_separate_not_subtracted(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db, qty=Decimal('100'))
    result = execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(),
            exported_electricity_quantity=Decimal('10'),
            exported_electricity_unit='MWh',
        ),
    )
    assert result.indirect_emissions_tco2e == Decimal('43.90000000')
    assert result.exported_electricity_mwh == Decimal('10')
    detail = get_purchased_electricity_result(
        seeded_db, user, org.id, binding.id, result.result_id
    )
    assert detail.exported_electricity_mwh == Decimal('10')
    assert detail.indirect_emissions_tco2e == Decimal('43.90000000')


def test_unresolved_platform_default_fails_closed(seeded_db: Session) -> None:
    resolved = resolve_platform_default_factor(seeded_db, reference_date=date(2024, 6, 1))
    assert resolved.resolved is False
    assert 'UNRESOLVED_PLATFORM_DEFAULT' in resolved.blocking_issue_codes
    assert TURKEY_DEFAULT_FACTOR_SEED_BLOCKER in resolved.informational_issue_codes


def test_manual_factor_with_provenance_works(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    resp = execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(),
            exported_electricity_quantity=Decimal('5'),
            exported_electricity_unit='MWh',
        ),
    )
    assert resp.indirect_emissions_tco2e == Decimal('43.90000000')
    assert resp.result_unit == 'tCO2e'
    assert resp.exported_electricity_mwh == Decimal('5')
    assert resp.electricity_mwh == Decimal('100')
    # Exported not subtracted from purchased
    assert resp.electricity_mwh == Decimal('100')


def test_manual_factor_without_provenance_fails(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    with pytest.raises(ValidationAppError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=activity.id,
                factor_source_mode='MANUAL',
                manual_factor=_manual_factor(source_document=''),
            ),
        )
    assert any(
        d.get('code') == 'MANUAL_FACTOR_DOCUMENT_REQUIRED' for d in (exc.value.details or [])
    )


def test_missing_manual_factor_rejected(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    with pytest.raises(ValidationAppError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=activity.id,
                factor_source_mode='MANUAL',
                manual_factor=None,
            ),
        )
    assert any(d.get('code') == 'MANUAL_FACTOR_REQUIRED' for d in (exc.value.details or []))


def test_platform_default_execution_fails_closed(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    with pytest.raises(BusinessRuleError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=activity.id,
                factor_source_mode='PLATFORM_DEFAULT',
            ),
        )
    assert any(
        d.get('code') == 'UNRESOLVED_PLATFORM_DEFAULT' for d in (exc.value.details or [])
    )


def test_negative_electricity_rejected_on_activity(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    row = seeded_db.get(CbamActivityRecord, activity.id)
    assert row is not None
    # Keep change in the identity map only (DB check forbids flushing negatives).
    row.quantity = Decimal('-1')
    with pytest.raises(ValidationAppError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=activity.id,
                factor_source_mode='MANUAL',
                manual_factor=_manual_factor(),
            ),
        )
    assert any(
        d.get('code') == 'NEGATIVE_ELECTRICITY_QUANTITY' for d in (exc.value.details or [])
    )


def test_incompatible_activity_unit_rejected(seeded_db: Session) -> None:
    user, org, binding, _ = _setup(seeded_db)
    facility = seeded_db.execute(
        select(Facility).where(Facility.organization_id == org.id).limit(1)
    ).scalar_one()
    inst = installation_service.create_installation(
        seeded_db,
        user,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'PE2-{uuid.uuid4().hex[:8]}',
            name='PE2',
        ),
    )
    gas = activity_record_service.create_activity_record(
        seeded_db,
        user,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=inst.id,
            activity_type='NATURAL_GAS',
            activity_date=date(2024, 6, 15),
            quantity=Decimal('10'),
            unit='Sm3',
            data_source_type='PRIMARY',
        ),
    )
    seeded_db.commit()
    with pytest.raises(ValidationAppError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=gas.id,
                factor_source_mode='MANUAL',
                manual_factor=_manual_factor(),
            ),
        )
    assert any(
        d.get('code') == 'INCOMPATIBLE_ACTIVITY_TYPE' for d in (exc.value.details or [])
    )


def test_immutable_snapshot_and_current_history(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    first_id = uuid.uuid4()
    r1 = execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=first_id,
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(),
        ),
    )
    r2 = execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(value=Decimal('0.5')),
        ),
    )
    detail1 = get_purchased_electricity_result(
        seeded_db, user, org.id, binding.id, r1.result_id
    )
    detail2 = get_purchased_electricity_result(
        seeded_db, user, org.id, binding.id, r2.result_id
    )
    assert detail1.factor_value == Decimal('0.439')
    assert detail2.factor_value == Decimal('0.5')
    assert detail1.is_current is False
    assert detail2.is_current is True
    count = seeded_db.execute(
        select(CbamPurchasedElectricityResult).where(
            CbamPurchasedElectricityResult.reporting_period_binding_id == binding.id
        )
    ).scalars().all()
    assert len(count) == 2


def test_input_change_makes_result_stale(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(),
        ),
    )
    activity_record_service.update_activity_record(
        seeded_db,
        user,
        org.id,
        activity.id,
        activity_record_service.ActivityRecordUpdate(
            row_version=activity.row_version,
            quantity=Decimal('200'),
        ),
    )
    seeded_db.commit()
    summary = get_purchased_electricity_summary(seeded_db, user, org.id, binding.id)
    assert summary.stale_result_count == 1
    assert 'ELECTRICITY_RESULTS_STALE' in summary.blocking_issue_codes


def test_idempotent_replay_and_conflict(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    key = uuid.uuid4()
    body = PurchasedElectricityExecuteRequest(
        client_request_id=key,
        activity_record_id=activity.id,
        factor_source_mode='MANUAL',
        manual_factor=_manual_factor(),
    )
    first = execute_purchased_electricity(seeded_db, user, org.id, binding.id, body)
    replay = execute_purchased_electricity(seeded_db, user, org.id, binding.id, body)
    assert replay.idempotent_replay is True
    assert replay.result_id == first.result_id
    with pytest.raises(ConflictError) as exc:
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=key,
                activity_record_id=activity.id,
                factor_source_mode='MANUAL',
                manual_factor=_manual_factor(value=Decimal('0.5')),
            ),
        )
    assert exc.value.code == 'IDEMPOTENCY_KEY_REUSED'


def test_failed_recalculation_preserves_current(seeded_db: Session) -> None:
    user, org, binding, activity = _setup(seeded_db)
    ok = execute_purchased_electricity(
        seeded_db,
        user,
        org.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode='MANUAL',
            manual_factor=_manual_factor(),
        ),
    )
    pointer_before = seeded_db.execute(
        select(CbamPurchasedElectricityCurrentResult).where(
            CbamPurchasedElectricityCurrentResult.activity_record_id == activity.id
        )
    ).scalar_one()
    assert pointer_before.current_result_id == ok.result_id
    with pytest.raises(BusinessRuleError):
        execute_purchased_electricity(
            seeded_db,
            user,
            org.id,
            binding.id,
            PurchasedElectricityExecuteRequest(
                client_request_id=uuid.uuid4(),
                activity_record_id=activity.id,
                factor_source_mode='PLATFORM_DEFAULT',
            ),
        )
    pointer_after = seeded_db.execute(
        select(CbamPurchasedElectricityCurrentResult).where(
            CbamPurchasedElectricityCurrentResult.activity_record_id == activity.id
        )
    ).scalar_one()
    assert pointer_after.current_result_id == ok.result_id


def test_api_routes_and_tenant_isolation(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    facilities = client.get(
        f'/api/v1/organizations/{org_id}/facilities', headers=headers
    ).json()['items']
    inst = client.post(
        f'/api/v1/cbam/organizations/{org_id}/installations',
        headers=headers,
        json={
            'facilityId': facilities[0]['id'],
            'code': f'PEAPI-{uuid.uuid4().hex[:8]}',
            'name': 'PE API',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f'/api/v1/organizations/{org_id}/reporting-periods',
        headers=headers,
        json={
            'code': f'PEAP-{uuid.uuid4().hex[:6]}',
            'name': 'PE API Period',
            'periodType': 'custom',
            'startDate': '2024-01-01',
            'endDate': '2024-12-31',
        },
    )
    assert period.status_code == 201, period.text
    binding = client.post(
        f'/api/v1/cbam/organizations/{org_id}/reporting-period-bindings',
        headers=headers,
        json={'reportingPeriodId': period.json()['id']},
    )
    assert binding.status_code == 201, binding.text
    opened = client.post(
        f"/api/v1/cbam/organizations/{org_id}/reporting-period-bindings/"
        f"{binding.json()['id']}/open-data-collection",
        headers=headers,
        json={'rowVersion': binding.json()['rowVersion']},
    )
    assert opened.status_code == 200, opened.text
    binding_id = binding.json()['id']
    base = f'/api/v1/cbam/organizations/{org_id}/reporting-period-bindings/{binding_id}'

    factors = client.get(f'{base}/purchased-electricity/factors/default', headers=headers)
    assert factors.status_code == 200, factors.text
    assert factors.json()['resolved'] is False

    activity = client.post(
        f'{base}/activity-records',
        headers=headers,
        json={
            'installationProfileId': inst.json()['id'],
            'activityType': 'ELECTRICITY',
            'activityDate': '2024-06-15',
            'quantity': '100',
            'unit': 'MWh',
            'dataSourceType': 'PRIMARY',
        },
    )
    assert activity.status_code == 201, activity.text

    exec_resp = client.post(
        f'{base}/purchased-electricity/executions',
        headers=headers,
        json={
            'clientRequestId': str(uuid.uuid4()),
            'activityRecordId': activity.json()['id'],
            'factorSourceMode': 'MANUAL',
            'manualFactor': {
                'value': '0.439',
                'unit': 'tCO2e/MWh',
                'sourceName': 'Org factor',
                'sourceDocument': 'Doc',
                'datasetVersion': 'v1',
                'referenceDescription': 'Provenance',
            },
            'exportedElectricityQuantity': '2',
            'exportedElectricityUnit': 'MWh',
        },
    )
    assert exec_resp.status_code == 201, exec_resp.text
    body = exec_resp.json()
    assert body['indirectEmissionsTco2e'] == '43.90000000'
    assert body['exportedElectricityMwh'] == '2.000000000000000000'
    assert body['resultUnit'] == 'tCO2e'
    # Client must not submit calculated emissions — none in request; server computed.

    summary = client.get(f'{base}/purchased-electricity/summary', headers=headers)
    assert summary.status_code == 200
    assert summary.json()['totalElectricityMwh'] == '100.000000000000000000'
    assert summary.json()['totalExportedElectricityMwh'] == '2.000000000000000000'

    # Tenant isolation: other org UUID should 404/403
    other = client.get(
        f'/api/v1/cbam/organizations/{uuid.uuid4()}/reporting-period-bindings/'
        f'{binding_id}/purchased-electricity/summary',
        headers=headers,
    )
    assert other.status_code in {403, 404}
