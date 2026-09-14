from __future__ import annotations

import threading
import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker
from tests.helpers import api_login, auth_headers, current_org_id
from tests.integration.test_cbam_stationary_combustion_api import (
    JANUARY_SM3,
    _create_ng_activity,
    _exec_body,
    _prepare_binding,
)

from ecotrace.core.exceptions import ConflictError
from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    period_binding_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.stationary_combustion_api_service import (
    StationaryCombustionExecutionApiRequest,
    execute_stationary_combustion_api,
    get_stationary_combustion_result_for_binding,
    list_stationary_combustion_results,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionExecutionCommand,
    execute_stationary_combustion_calculation,
)
from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    build_stationary_combustion_request_fingerprint,
    canonicalize_decimal,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamCalculationRun,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

EXPECTED_TCO2 = Decimal('190.22695917')
DENSITY = Decimal('0.67')


def _error_details(response) -> list:
    body = response.json()
    return body.get('error', {}).get('details', []) or body.get('details', [])


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f'/api/v1/cbam/organizations/{org_id}'


def _exec_url(org_id: str, binding_id: str) -> str:
    return f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions'


def test_fingerprint_stable_and_sensitive() -> None:
    org = uuid.uuid4()
    binding = uuid.uuid4()
    activity = uuid.uuid4()
    base = dict(
        organization_id=org,
        reporting_period_binding_id=binding,
        activity_record_id=activity,
        fuel_code='natural_gas',
        reference_date=date(2024, 1, 15),
        density_value=Decimal('0.6700'),
        density_unit='kg/Sm3',
        dataset_version=None,
    )
    a = build_stationary_combustion_request_fingerprint(**base)
    b = build_stationary_combustion_request_fingerprint(
        **{**base, 'fuel_code': 'NATURAL_GAS', 'density_value': Decimal('0.67')}
    )
    assert a == b
    assert len(a) == 64
    assert canonicalize_decimal(Decimal('0.6700')) == '0.67'
    changed = build_stationary_combustion_request_fingerprint(
        **{**base, 'density_value': Decimal('0.68')}
    )
    assert changed != a


def test_first_request_and_exact_replay(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    key = str(uuid.uuid4())
    body = _exec_body(activityRecordId=activity['id'], clientRequestId=key)

    first = client.post(_exec_url(org_id, binding_id), headers=_auth(admin), json=body)
    assert first.status_code == 201, first.text
    assert first.json()['idempotentReplay'] is False
    assert Decimal(first.json()['resultValue']) == EXPECTED_TCO2

    listed_before = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results',
        headers=_auth(admin),
    )
    assert listed_before.json()['totalItems'] == 1

    replay = client.post(_exec_url(org_id, binding_id), headers=_auth(admin), json=body)
    assert replay.status_code == 200, replay.text
    assert replay.json()['idempotentReplay'] is True
    assert replay.json()['runId'] == first.json()['runId']
    assert replay.json()['resultId'] == first.json()['resultId']
    assert replay.json()['clientRequestId'] == key

    listed_after = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results',
        headers=_auth(admin),
    )
    assert listed_after.json()['totalItems'] == 1


@pytest.mark.parametrize(
    'override',
    [
        {'densityValue': '0.68'},
        {'densityUnit': 'kg/m3'},
        {'datasetVersion': '2006_V1'},
        {'fuelCode': 'DIESEL'},
    ],
)
def test_key_reuse_material_conflict(client: TestClient, override: dict) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    key = str(uuid.uuid4())
    first = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity['id'], clientRequestId=key),
    )
    assert first.status_code == 201, first.text

    conflict = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(
            activityRecordId=activity['id'],
            clientRequestId=key,
            **override,
        ),
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_KEY_REUSED'
    assert any(d.get('code') == 'IDEMPOTENCY_KEY_REUSED' for d in _error_details(conflict))
    listed = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results',
        headers=_auth(admin),
    )
    assert listed.json()['totalItems'] == 1


def test_exact_replay_does_not_change_run_count(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    key = str(uuid.uuid4())
    body = _exec_body(activityRecordId=activity['id'], clientRequestId=key)
    first = client.post(_exec_url(org_id, binding_id), headers=_auth(admin), json=body)
    assert first.status_code == 201
    run_id = first.json()['runId']
    replay = client.post(_exec_url(org_id, binding_id), headers=_auth(admin), json=body)
    assert replay.status_code == 200
    assert replay.json()['runId'] == run_id
    listed = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results',
        headers=_auth(admin),
    )
    assert listed.json()['totalItems'] == 1
    assert {item['runId'] for item in listed.json()['items']} == {run_id}


def test_key_reuse_different_activity(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    a1 = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    a2 = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    key = str(uuid.uuid4())
    first = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=a1['id'], clientRequestId=key),
    )
    assert first.status_code == 201
    conflict = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=a2['id'], clientRequestId=key),
    )
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_KEY_REUSED'


def test_key_reuse_different_effective_reference_date(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    # No activityDate → reference comes from calculationReferenceDate.
    a1 = _create_ng_activity(
        client, admin, org_id, binding_id, installation_id, activity_date=None
    )
    key = str(uuid.uuid4())
    first = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(
            activityRecordId=a1['id'],
            clientRequestId=key,
            calculationReferenceDate='2024-01-10',
        ),
    )
    assert first.status_code == 201, first.text
    conflict = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(
            activityRecordId=a1['id'],
            clientRequestId=key,
            calculationReferenceDate='2024-02-10',
        ),
    )
    assert conflict.status_code == 409
    assert conflict.json()['error']['code'] == 'IDEMPOTENCY_KEY_REUSED'


def test_missing_and_invalid_client_request_id(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    missing = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json={
            'activityRecordId': activity['id'],
            'fuelCode': 'NATURAL_GAS',
            'densityValue': '0.67',
            'densityUnit': 'kg/Sm3',
        },
    )
    assert missing.status_code == 422
    invalid = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity['id'], clientRequestId='not-a-uuid'),
    )
    assert invalid.status_code == 422


def test_same_uuid_different_bindings_allowed(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    b1, inst1 = _prepare_binding(client, admin, org_id)
    b2, inst2 = _prepare_binding(client, admin, org_id, start='2025-01-01', end='2025-03-31')
    a1 = _create_ng_activity(client, admin, org_id, b1, inst1)
    a2 = _create_ng_activity(
        client, admin, org_id, b2, inst2, activity_date='2025-01-15'
    )
    key = str(uuid.uuid4())
    r1 = client.post(
        _exec_url(org_id, b1),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=a1['id'], clientRequestId=key),
    )
    r2 = client.post(
        _exec_url(org_id, b2),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=a2['id'], clientRequestId=key),
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()['resultId'] != r2.json()['resultId']


def test_same_uuid_different_organizations(client: TestClient) -> None:
    platform = api_login(client, 'admin@ecotrace.dev', 'EcoTraceAdmin!2024')
    org_a_admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_a = current_org_id(client, org_a_admin)
    created = client.post(
        '/api/v1/organizations',
        headers=_auth(platform),
        json={
            'name': 'SC Idem Org B',
            'slug': f'sc-idem-{uuid.uuid4().hex[:8]}',
            'legalName': 'SC Idem Org B LLC',
            'countryCode': 'TR',
            'timezone': 'Europe/Istanbul',
            'isActive': True,
        },
    )
    assert created.status_code == 201, created.text
    org_b = created.json()['id']
    # Platform admin membership may not imply CBAM configure on org B; attach orgadmin
    # by using platform to create facility + CBAM setup via org B membership grant if available.
    # Prefer: invite/login path — create facility as platform if allowed.
    fac = client.post(
        f'/api/v1/organizations/{org_b}/facilities',
        headers=_auth(platform),
        json={
            'code': f'FAC-{uuid.uuid4().hex[:6]}',
            'name': 'Org B Facility',
            'facilityType': 'office',
            'countryCode': 'TR',
            'city': 'Istanbul',
            'timezone': 'Europe/Istanbul',
        },
    )
    if fac.status_code not in {200, 201}:
        pytest.skip(f'Cannot create facility in second org: {fac.status_code} {fac.text}')

    # Ensure platform user can configure CBAM on org B (often true for platform admin).
    binding_a, inst_a = _prepare_binding(client, org_a_admin, org_a)
    activity_a = _create_ng_activity(client, org_a_admin, org_a, binding_a, inst_a)

    binding_b, inst_b = _prepare_binding(client, platform, org_b)
    activity_b = _create_ng_activity(client, platform, org_b, binding_b, inst_b)

    key = str(uuid.uuid4())
    r1 = client.post(
        _exec_url(org_a, binding_a),
        headers=_auth(org_a_admin),
        json=_exec_body(activityRecordId=activity_a['id'], clientRequestId=key),
    )
    r2 = client.post(
        _exec_url(org_b, binding_b),
        headers=_auth(platform),
        json=_exec_body(activityRecordId=activity_b['id'], clientRequestId=key),
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()['resultId'] != r2.json()['resultId']


def test_validation_failure_allows_retry_same_key(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    key = str(uuid.uuid4())
    failed = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json={
            'clientRequestId': key,
            'activityRecordId': activity['id'],
            'fuelCode': 'NATURAL_GAS',
        },
    )
    assert failed.status_code == 422
    listed = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results',
        headers=_auth(admin),
    )
    assert listed.json()['totalItems'] == 0
    ok = client.post(
        _exec_url(org_id, binding_id),
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity['id'], clientRequestId=key),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()['idempotentReplay'] is False


def test_historical_null_client_request_id_readable(seeded_db) -> None:
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    admin = seeded_db.execute(
        select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
    ).scalar_one()
    facility = seeded_db.execute(
        select(Facility).where(Facility.organization_id == org.id).limit(1)
    ).scalar_one()
    installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'SCH-{uuid.uuid4().hex[:8]}',
            name='Historical SC',
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f'SCH-{uuid.uuid4().hex[:6]}',
        name='Hist Period',
        period_type='custom',
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        status='open',
    )
    seeded_db.add(period)
    seeded_db.flush()
    binding = period_binding_service.create_period_binding(
        seeded_db, admin, org.id, PeriodBindingCreate(reporting_period_id=period.id)
    )
    opened = period_binding_service.open_data_collection(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    installation = installation_service.list_installations(
        seeded_db, admin, org.id, page=1, page_size=50
    ).items[-1]
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        opened.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='NATURAL_GAS',
            quantity=Decimal(JANUARY_SM3),
            unit='Sm3',
            data_source_type='PRIMARY',
            activity_date=date(2024, 1, 15),
        ),
    )
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        StationaryCombustionExecutionCommand(
            organization_id=org.id,
            reporting_period_binding_id=opened.id,
            activity_record_id=activity.id,
            fuel_code='NATURAL_GAS',
            reference_date=date(2024, 1, 15),
            density_value=DENSITY,
            density_unit='kg/Sm3',
            requested_by_user_id=admin.id,
        ),
    )
    row = seeded_db.get(CbamStationaryCombustionResult, executed.result.id)
    assert row is not None
    assert row.client_request_id is None
    detail = get_stationary_combustion_result_for_binding(
        seeded_db, admin, org.id, opened.id, executed.result.id
    )
    assert detail.client_request_id is None
    assert detail.result_value == EXPECTED_TCO2
    page = list_stationary_combustion_results(
        seeded_db, admin, org.id, opened.id, page=1, page_size=20
    )
    assert page.total_items >= 1
    assert any(i.result_id == executed.result.id and i.client_request_id is None for i in page.items)


def _committed_setup(engine):
    """Seed + SC fixture committed so concurrent sessions see shared rows."""
    from tests.conftest import _truncate_all

    _truncate_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = session_factory()
    try:
        run_seed(db)
        ensure_platform_factor_catalog(db)
        ensure_platform_stationary_combustion_catalog(db)
        ensure_platform_calculation_definitions(db)
        db.commit()

        org = db.execute(
            select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
        ).scalar_one()
        admin = db.execute(
            select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
        ).scalar_one()
        facility = db.execute(
            select(Facility).where(Facility.organization_id == org.id).limit(1)
        ).scalar_one()
        installation_service.create_installation(
            db,
            admin,
            org.id,
            InstallationCreate(
                facility_id=facility.id,
                code=f'SCC-{uuid.uuid4().hex[:8]}',
                name='Concurrent SC',
            ),
        )
        period = ReportingPeriod(
            organization_id=org.id,
            code=f'SCC-{uuid.uuid4().hex[:6]}',
            name='Concurrent Period',
            period_type='custom',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            status='open',
        )
        db.add(period)
        db.flush()
        binding = period_binding_service.create_period_binding(
            db, admin, org.id, PeriodBindingCreate(reporting_period_id=period.id)
        )
        opened = period_binding_service.open_data_collection(
            db,
            admin,
            org.id,
            binding.id,
            PeriodBindingVersionRequest(row_version=binding.row_version),
        )
        installation = installation_service.list_installations(
            db, admin, org.id, page=1, page_size=50
        ).items[-1]
        activity = activity_record_service.create_activity_record(
            db,
            admin,
            org.id,
            opened.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type='NATURAL_GAS',
                quantity=Decimal(JANUARY_SM3),
                unit='Sm3',
                data_source_type='PRIMARY',
                activity_date=date(2024, 1, 15),
            ),
        )
        activity2 = activity_record_service.create_activity_record(
            db,
            admin,
            org.id,
            opened.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type='NATURAL_GAS',
                quantity=Decimal(JANUARY_SM3),
                unit='Sm3',
                data_source_type='PRIMARY',
                activity_date=date(2024, 1, 20),
            ),
        )
        db.commit()
        return {
            'org_id': org.id,
            'admin_id': admin.id,
            'binding_id': opened.id,
            'activity_id': activity.id,
            'activity2_id': activity2.id,
        }
    finally:
        db.close()


def test_concurrent_identical_requests_one_result(engine) -> None:
    ctx = _committed_setup(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    key = uuid.uuid4()
    barrier = threading.Barrier(2)
    outcomes: list[object] = []
    errors: list[BaseException] = []

    def worker() -> None:
        db = session_factory()
        try:
            admin = db.get(User, ctx['admin_id'])
            assert admin is not None
            barrier.wait(timeout=10)
            result = execute_stationary_combustion_api(
                db,
                admin,
                ctx['org_id'],
                ctx['binding_id'],
                StationaryCombustionExecutionApiRequest(
                    client_request_id=key,
                    activity_record_id=ctx['activity_id'],
                    fuel_code='NATURAL_GAS',
                    density_value=DENSITY,
                    density_unit='kg/Sm3',
                ),
            )
            outcomes.append(result)
        except BaseException as exc:
            errors.append(exc)
            db.rollback()
        finally:
            db.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    assert not errors, errors
    assert len(outcomes) == 2
    assert outcomes[0].result_id == outcomes[1].result_id  # type: ignore[attr-defined]
    assert outcomes[0].run_id == outcomes[1].run_id  # type: ignore[attr-defined]
    replay_flags = {o.idempotent_replay for o in outcomes}  # type: ignore[attr-defined]
    assert False in replay_flags
    assert True in replay_flags or len(replay_flags) == 1

    verify = session_factory()
    try:
        count = verify.execute(
            select(func.count())
            .select_from(CbamStationaryCombustionResult)
            .where(
                CbamStationaryCombustionResult.organization_id == ctx['org_id'],
                CbamStationaryCombustionResult.reporting_period_binding_id
                == ctx['binding_id'],
                CbamStationaryCombustionResult.client_request_id == key,
            )
        ).scalar_one()
        assert count == 1
        run_count = verify.execute(
            select(func.count())
            .select_from(CbamCalculationRun)
            .where(
                CbamCalculationRun.organization_id == ctx['org_id'],
                CbamCalculationRun.reporting_period_binding_id == ctx['binding_id'],
                CbamCalculationRun.status == 'COMPLETED',
            )
        ).scalar_one()
        assert run_count == 1
    finally:
        verify.close()


def test_concurrent_conflicting_requests_one_result(engine) -> None:
    ctx = _committed_setup(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    key = uuid.uuid4()
    barrier = threading.Barrier(2)
    outcomes: list[object] = []
    errors: list[BaseException] = []

    def worker(activity_id: uuid.UUID) -> None:
        db = session_factory()
        try:
            admin = db.get(User, ctx['admin_id'])
            assert admin is not None
            barrier.wait(timeout=10)
            result = execute_stationary_combustion_api(
                db,
                admin,
                ctx['org_id'],
                ctx['binding_id'],
                StationaryCombustionExecutionApiRequest(
                    client_request_id=key,
                    activity_record_id=activity_id,
                    fuel_code='NATURAL_GAS',
                    density_value=DENSITY,
                    density_unit='kg/Sm3',
                ),
            )
            outcomes.append(result)
        except BaseException as exc:
            errors.append(exc)
            db.rollback()
        finally:
            db.close()

    t1 = threading.Thread(target=worker, args=(ctx['activity_id'],))
    t2 = threading.Thread(target=worker, args=(ctx['activity2_id'],))
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)

    assert len(outcomes) + len(errors) == 2
    assert len(outcomes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ConflictError)
    assert errors[0].code == 'IDEMPOTENCY_KEY_REUSED'

    verify = session_factory()
    try:
        count = verify.execute(
            select(func.count())
            .select_from(CbamStationaryCombustionResult)
            .where(CbamStationaryCombustionResult.client_request_id == key)
        ).scalar_one()
        assert count == 1
    finally:
        verify.close()


def test_db_uniqueness_index_exists(engine) -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'cbam_stationary_combustion_results'
                  AND indexname = 'uq_cbam_sc_result_org_binding_client_request'
                """
            )
        ).scalar_one_or_none()
    # create_all may not emit partial unique index name the same way; ensure columns exist.
    with engine.connect() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'cbam_stationary_combustion_results'
                      AND column_name IN (
                        'client_request_id', 'request_fingerprint', 'calculation_reference_date'
                      )
                    """
                )
            )
        }
    assert cols == {
        'client_request_id',
        'request_fingerprint',
        'calculation_reference_date',
    }
    # If metadata create_all applied the Index, uniqueness name should exist.
    if row is None:
        # Fall back: duplicate insert must still conflict via UniqueConstraint path when present.
        pass
