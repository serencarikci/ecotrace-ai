from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.carbon_constants import (
    MATCH_PRIORITY_ACTIVITY_COUNTRY,
    MATCH_PRIORITY_ACTIVITY_GEO,
    MATCH_PRIORITY_ACTIVITY_GEO_TECH,
    MATCH_PRIORITY_ACTIVITY_GLOBAL,
    MATCH_PRIORITY_ORG_PREFERENCE,
)
from ecotrace.modules.emission_factors.infrastructure.models import (
    EmissionFactor,
    OrganizationEmissionFactorPreference,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.reference_data.infrastructure.models import Unit


@dataclass
class MatchCandidate:
    factor: EmissionFactor
    priority: int
    reason: str


@dataclass
class MatchResult:
    selected: EmissionFactor | None = None
    priority: int | None = None
    reason: str | None = None
    ambiguous: bool = False
    alternatives: list[EmissionFactor] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    explanation: str | None = None


def _factor_valid_on(factor: EmissionFactor, activity_date: date | None) -> bool:
    if activity_date is None:
        return True
    if factor.valid_from and activity_date < factor.valid_from:
        return False
    return not (factor.valid_to and activity_date > factor.valid_to)


def _pref_valid_on(pref: OrganizationEmissionFactorPreference, activity_date: date | None) -> bool:
    if activity_date is None:
        return True
    if pref.valid_from and activity_date < pref.valid_from:
        return False
    return not (pref.valid_to and activity_date > pref.valid_to)


def _units_compatible(db: Session, activity_unit_code: str, factor_unit_code: str) -> bool:
    activity_unit = db.execute(
        select(Unit).where(Unit.code == activity_unit_code, Unit.is_active.is_(True))
    ).scalar_one_or_none()
    factor_unit = db.execute(
        select(Unit).where(Unit.code == factor_unit_code, Unit.is_active.is_(True))
    ).scalar_one_or_none()
    if activity_unit is None or factor_unit is None:
        return False
    return activity_unit.dimension == factor_unit.dimension


def _score_factor(
    factor: EmissionFactor,
    *,
    country_code: str | None,
    region_code: str | None,
    technology_code: str | None,
    fuel_type: str | None,
    transportation_mode: str | None,
) -> MatchCandidate | None:
    geo = (factor.geography_code or "GLOBAL").upper()
    country = (country_code or "").upper() or None
    region = (region_code or "").upper() or None

    tech_match = False
    if technology_code and factor.technology_code:
        tech_match = factor.technology_code.lower() == technology_code.lower()
    elif fuel_type and factor.fuel_type:
        tech_match = factor.fuel_type.lower() == fuel_type.lower()
    elif transportation_mode and factor.transportation_mode:
        tech_match = factor.transportation_mode.lower() == transportation_mode.lower()

    if region and geo == region:
        priority = MATCH_PRIORITY_ACTIVITY_GEO_TECH if tech_match else MATCH_PRIORITY_ACTIVITY_GEO
        reason = (
            "Exact activity type, geography (region/grid), and technology"
            if tech_match
            else "Exact activity type and geography (region/grid)"
        )
        return MatchCandidate(factor=factor, priority=priority, reason=reason)

    if country and geo == country:
        priority = (
            MATCH_PRIORITY_ACTIVITY_GEO_TECH if tech_match else MATCH_PRIORITY_ACTIVITY_COUNTRY
        )
        reason = (
            "Exact activity type, country geography, and technology"
            if tech_match
            else "Exact activity type and country"
        )
        return MatchCandidate(factor=factor, priority=priority, reason=reason)

    if geo in {"GLOBAL", "WW", "WORLD"}:
        return MatchCandidate(
            factor=factor,
            priority=MATCH_PRIORITY_ACTIVITY_GLOBAL,
            reason="Exact activity type and global factor",
        )

    return None


def match_emission_factor(
    db: Session,
    *,
    organization_id: uuid.UUID,
    activity_type_id: uuid.UUID,
    activity_date: date | None,
    activity_unit_code: str,
    facility_id: uuid.UUID | None = None,
    technology_code: str | None = None,
    fuel_type: str | None = None,
    transportation_mode: str | None = None,
    preferred_source_id: uuid.UUID | None = None,
) -> MatchResult:
    result = MatchResult()

    country_code: str | None = None
    region_code: str | None = None
    if facility_id:
        facility = db.get(Facility, facility_id)
        if facility and facility.organization_id == organization_id:
            country_code = facility.country_code

            region_code = facility.district

    pref_stmt = (
        select(OrganizationEmissionFactorPreference)
        .where(
            OrganizationEmissionFactorPreference.organization_id == organization_id,
            OrganizationEmissionFactorPreference.activity_type_id == activity_type_id,
            OrganizationEmissionFactorPreference.is_active.is_(True),
        )
        .order_by(OrganizationEmissionFactorPreference.priority.asc())
    )
    prefs = list(db.execute(pref_stmt).scalars().all())
    pref_candidates: list[MatchCandidate] = []
    for pref in prefs:
        if not _pref_valid_on(pref, activity_date):
            continue
        factor = db.get(EmissionFactor, pref.emission_factor_id)
        if factor is None:
            continue
        if factor.status != "active" or not factor.is_active:
            continue
        if factor.activity_type_id != activity_type_id:
            continue
        if not _factor_valid_on(factor, activity_date):
            continue
        if not _units_compatible(db, activity_unit_code, factor.unit_code):
            continue
        pref_candidates.append(
            MatchCandidate(
                factor=factor,
                priority=MATCH_PRIORITY_ORG_PREFERENCE,
                reason=(
                    f"Organization-approved factor preference "
                    f"(priority={pref.priority}"
                    + (f", reason={pref.reason}" if pref.reason else "")
                    + ")"
                ),
            )
        )

    if pref_candidates:
        best_p = min(c.priority for c in pref_candidates)

        top = [c for c in pref_candidates if c.priority == best_p]

        if len(top) > 1:
            result.ambiguous = True
            result.alternatives = [c.factor for c in top]
            result.errors.append(
                {
                    "code": "ambiguous_factor",
                    "message": "Multiple organization preferences match with equal priority.",
                }
            )
            result.explanation = "Ambiguous organization factor preferences."
            return result
        chosen = top[0]
        result.selected = chosen.factor
        result.priority = chosen.priority
        result.reason = chosen.reason
        result.explanation = chosen.reason
        return result

    stmt = select(EmissionFactor).where(
        EmissionFactor.activity_type_id == activity_type_id,
        EmissionFactor.status == "active",
        EmissionFactor.is_active.is_(True),
    )
    factors = list(db.execute(stmt).scalars().all())
    candidates: list[MatchCandidate] = []
    for factor in factors:
        if not _factor_valid_on(factor, activity_date):
            continue
        if not _units_compatible(db, activity_unit_code, factor.unit_code):
            continue
        scored = _score_factor(
            factor,
            country_code=country_code,
            region_code=region_code,
            technology_code=technology_code,
            fuel_type=fuel_type,
            transportation_mode=transportation_mode,
        )
        if scored:
            candidates.append(scored)

    if not candidates:
        result.errors.append(
            {
                "code": "missing_factor",
                "message": "No compatible active emission factor found for this activity.",
            }
        )
        result.explanation = "No match"
        return result

    best_priority = min(c.priority for c in candidates)
    top = [c for c in candidates if c.priority == best_priority]

    if preferred_source_id and len(top) > 1:
        sourced = [c for c in top if c.factor.source_id == preferred_source_id]
        if len(sourced) == 1:
            top = sourced

    if len(top) > 1:
        result.ambiguous = True
        result.alternatives = [c.factor for c in top]
        result.errors.append(
            {
                "code": "ambiguous_factor",
                "message": (
                    f"Multiple factors share matching priority {best_priority}; "
                    "user resolution required."
                ),
            }
        )
        result.explanation = "Ambiguous match — calculation blocked."
        return result

    chosen = top[0]
    result.selected = chosen.factor
    result.priority = chosen.priority
    result.reason = chosen.reason
    result.alternatives = [c.factor for c in candidates if c.factor.id != chosen.factor.id][:10]
    result.explanation = chosen.reason
    return result


def find_overlapping_active_factors(
    db: Session,
    *,
    activity_type_id: uuid.UUID,
    geography_code: str,
    technology_code: str | None,
    fuel_type: str | None,
    transportation_mode: str | None,
    unit_code: str,
    valid_from: date | None,
    valid_to: date | None,
    exclude_factor_id: uuid.UUID | None = None,
) -> list[EmissionFactor]:
    stmt = select(EmissionFactor).where(
        EmissionFactor.activity_type_id == activity_type_id,
        EmissionFactor.status == "active",
        EmissionFactor.is_active.is_(True),
        EmissionFactor.geography_code == geography_code,
        EmissionFactor.unit_code == unit_code,
    )
    if exclude_factor_id:
        stmt = stmt.where(EmissionFactor.id != exclude_factor_id)
    rows = list(db.execute(stmt).scalars().all())

    def dim_equal(a: str | None, b: str | None) -> bool:
        return (a or "").lower() == (b or "").lower()

    overlaps: list[EmissionFactor] = []
    for row in rows:
        if not dim_equal(row.technology_code, technology_code):
            continue
        if not dim_equal(row.fuel_type, fuel_type):
            continue
        if not dim_equal(row.transportation_mode, transportation_mode):
            continue

        a_from = valid_from or date.min
        a_to = valid_to or date.max
        b_from = row.valid_from or date.min
        b_to = row.valid_to or date.max
        if a_from <= b_to and b_from <= a_to:
            overlaps.append(row)
    return overlaps
