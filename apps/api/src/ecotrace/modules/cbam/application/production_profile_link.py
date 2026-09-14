"""Authoritative production ↔ product-profile link rules (Phase 6C)."""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.collection_guards import get_product_profile_for_org
from ecotrace.modules.cbam.infrastructure.models import (
    CbamProductionRecord,
    CbamProductProfileVersion,
)

ProfileLinkStatus = Literal['MISSING', 'READY', 'OUTDATED', 'INVALID']


def require_linkable_product_profile(
    db: Session,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
) -> CbamProductProfileVersion:
    """Profiles that may be newly linked to a production record (active + ready)."""
    profile = get_product_profile_for_org(db, organization_id, profile_id)
    if profile.status == 'archived':
        raise BusinessRuleError(
            'Archived product profiles cannot be linked to production records.',
            details=[{'code': 'PRODUCT_PROFILE_ARCHIVED'}],
        )
    if profile.status == 'draft':
        raise BusinessRuleError(
            'Draft product profiles cannot be linked to production records. Publish the profile first.',
            details=[{'code': 'PRODUCT_PROFILE_NOT_ACTIVE'}],
        )
    if profile.status == 'superseded':
        raise BusinessRuleError(
            'Superseded product profiles cannot be linked to new production records. '
            'Choose the active published version.',
            details=[{'code': 'PRODUCT_PROFILE_NOT_ACTIVE'}],
        )
    if profile.status != 'active':
        raise BusinessRuleError(
            'Only an active published product profile can be linked to a production record.',
            details=[{'code': 'PRODUCT_PROFILE_NOT_ACTIVE'}],
        )
    if not profile.classification_ready:
        raise BusinessRuleError(
            'This product profile is not classification-ready yet.',
            details=[{'code': 'PRODUCT_PROFILE_NOT_READY'}],
        )
    return profile


def require_production_profile_id(profile_id: uuid.UUID | None) -> uuid.UUID:
    if profile_id is None:
        raise BusinessRuleError(
            'Select a published product profile before saving production data.',
            details=[{'code': 'PRODUCT_PROFILE_REQUIRED'}],
        )
    return profile_id


def compute_profile_link_state(
    db: Session,
    row: CbamProductionRecord,
) -> tuple[ProfileLinkStatus, list[str], CbamProductProfileVersion | None]:
    """Server-owned link status for reads (does not rewrite historical references)."""
    if row.product_profile_version_id is None:
        return 'MISSING', ['PRODUCT_PROFILE_REQUIRED'], None

    profile = db.get(CbamProductProfileVersion, row.product_profile_version_id)
    if profile is None:
        return 'INVALID', ['PRODUCT_PROFILE_REQUIRED'], None
    if profile.organization_id != row.organization_id:
        return 'INVALID', ['PRODUCT_PROFILE_ORGANIZATION_MISMATCH'], profile
    if not profile.classification_ready:
        return 'INVALID', ['PRODUCT_PROFILE_NOT_READY'], profile
    if profile.status == 'active':
        return 'READY', [], profile
    if profile.status in ('superseded', 'archived'):
        # Historical immutable reference remains readable for allocation eligibility.
        return 'OUTDATED', [], profile
    if profile.status == 'draft':
        return 'INVALID', ['PRODUCT_PROFILE_NOT_ACTIVE'], profile
    return 'INVALID', ['PRODUCT_PROFILE_NOT_ACTIVE'], profile


def is_allocation_eligible_link(status: ProfileLinkStatus) -> bool:
    return status in ('READY', 'OUTDATED')
