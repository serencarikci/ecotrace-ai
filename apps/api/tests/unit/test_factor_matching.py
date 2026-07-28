from datetime import date
from types import SimpleNamespace
from ecotrace.core.carbon_constants import MATCH_PRIORITY_ACTIVITY_COUNTRY, MATCH_PRIORITY_ACTIVITY_GEO_TECH, MATCH_PRIORITY_ACTIVITY_GLOBAL
from ecotrace.modules.carbon_accounting.application.matching_service import _score_factor

def _factor(**kwargs):
    defaults = {'geography_code': 'GLOBAL', 'technology_code': None, 'fuel_type': None, 'transportation_mode': None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)

def test_matching_precedence_country_over_global() -> None:
    country = _score_factor(_factor(geography_code='TR'), country_code='TR', region_code=None, technology_code=None, fuel_type=None, transportation_mode=None)
    global_f = _score_factor(_factor(geography_code='GLOBAL'), country_code='TR', region_code=None, technology_code=None, fuel_type=None, transportation_mode=None)
    assert country is not None and global_f is not None
    assert country.priority == MATCH_PRIORITY_ACTIVITY_COUNTRY
    assert global_f.priority == MATCH_PRIORITY_ACTIVITY_GLOBAL
    assert country.priority < global_f.priority

def test_matching_geo_tech_beats_country() -> None:
    scored = _score_factor(_factor(geography_code='TR', fuel_type='diesel'), country_code='TR', region_code=None, technology_code=None, fuel_type='diesel', transportation_mode=None)
    assert scored is not None
    assert scored.priority == MATCH_PRIORITY_ACTIVITY_GEO_TECH

def test_non_matching_geography_excluded() -> None:
    scored = _score_factor(_factor(geography_code='DE'), country_code='TR', region_code=None, technology_code=None, fuel_type=None, transportation_mode=None)
    assert scored is None

def test_factor_valid_on_helper() -> None:
    from ecotrace.modules.carbon_accounting.application.matching_service import _factor_valid_on
    factor = SimpleNamespace(valid_from=date(2024, 1, 1), valid_to=date(2024, 12, 31))
    assert _factor_valid_on(factor, date(2024, 6, 1)) is True
    assert _factor_valid_on(factor, date(2023, 12, 31)) is False
    assert _factor_valid_on(factor, date(2025, 1, 1)) is False
