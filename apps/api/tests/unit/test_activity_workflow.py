from __future__ import annotations
import pytest
from sqlalchemy import select
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, ValidationAppError
from ecotrace.core.security import normalize_email
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.activity_data.application.activity_service import ActivityUpdate, ReasonRequest, approve_record, reject_record, submit_record, update_record
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.application.period_service import assert_period_writable, lock_period
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

@pytest.fixture
def seeded(seeded_db):
    org = seeded_db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()
    analyst = seeded_db.execute(select(User).where(User.normalized_email == normalize_email('analyst@ecotrace.dev'))).scalar_one()
    org_admin = seeded_db.execute(select(User).where(User.normalized_email == normalize_email('orgadmin@ecotrace.dev'))).scalar_one()
    return (seeded_db, org, analyst, org_admin)

def test_submit_approve_workflow(seeded) -> None:
    db_session, org, analyst, org_admin = seeded
    draft = db_session.execute(select(ActivityRecord).where(ActivityRecord.organization_id == org.id, ActivityRecord.status == 'draft')).scalar_one()
    submitted = submit_record(db_session, analyst, org.id, draft.id, ReasonRequest(row_version=draft.row_version))
    assert submitted.status == 'submitted'
    approved = approve_record(db_session, org_admin, org.id, draft.id, ReasonRequest(row_version=submitted.row_version))
    assert approved.status == 'approved'

def test_optimistic_concurrency(seeded) -> None:
    db_session, org, analyst, _ = seeded
    draft = db_session.execute(select(ActivityRecord).where(ActivityRecord.organization_id == org.id, ActivityRecord.status == 'draft')).scalar_one()
    with pytest.raises(ConflictError):
        update_record(db_session, analyst, org.id, draft.id, ActivityUpdate(row_version=draft.row_version + 5, notes='stale'))

def test_locked_period_blocks_mutations(seeded) -> None:
    db_session, org, analyst, org_admin = seeded
    period = db_session.execute(select(ReportingPeriod).where(ReportingPeriod.organization_id == org.id, ReportingPeriod.code == '2024-01')).scalar_one()
    lock_period(db_session, org_admin, org.id, period.id)
    db_session.refresh(period)
    with pytest.raises(BusinessRuleError):
        assert_period_writable(period)
    draft = db_session.execute(select(ActivityRecord).where(ActivityRecord.organization_id == org.id, ActivityRecord.status == 'draft')).scalar_one()
    with pytest.raises(BusinessRuleError):
        submit_record(db_session, analyst, org.id, draft.id, ReasonRequest(row_version=draft.row_version))

def test_reject_requires_reason(seeded) -> None:
    db_session, org, _, org_admin = seeded
    submitted = db_session.execute(select(ActivityRecord).where(ActivityRecord.organization_id == org.id, ActivityRecord.status == 'submitted')).scalar_one()
    with pytest.raises(ValidationAppError):
        reject_record(db_session, org_admin, org.id, submitted.id, ReasonRequest(reason='   ', row_version=submitted.row_version))
