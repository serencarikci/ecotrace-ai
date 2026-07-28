from decimal import Decimal
from typing import Final
ENGINE_VERSION: Final[str] = '3.0.0'
GWP_DATASET_AR5_DEMO: Final[str] = 'AR5-demo'
METHODOLOGY_VERSION: Final[str] = 'ecotrace-v1'
KG_CO2E_QUANTUM: Final[Decimal] = Decimal('0.00000001')
T_CO2E_QUANTUM: Final[Decimal] = Decimal('0.000001')
KG_PER_TONNE: Final[Decimal] = Decimal('1000')
SCOPES: Final[frozenset[str]] = frozenset({'scope_1', 'scope_2', 'scope_3'})
SCOPE_1_CATEGORIES: Final[frozenset[str]] = frozenset({'stationary_combustion', 'mobile_combustion', 'fugitive_emissions', 'process_emissions'})
SCOPE_2_CATEGORIES: Final[frozenset[str]] = frozenset({'purchased_electricity', 'purchased_steam', 'purchased_heat', 'purchased_cooling'})
SCOPE_3_CATEGORIES: Final[frozenset[str]] = frozenset({'purchased_goods_and_services', 'capital_goods', 'fuel_and_energy_related', 'upstream_transportation', 'waste_generated_in_operations', 'business_travel', 'employee_commuting', 'downstream_transportation'})
GHG_GAS_CODES: Final[frozenset[str]] = frozenset({'CO2', 'CH4', 'N2O', 'HFCs', 'PFCs', 'SF6', 'NF3', 'CO2e'})
FACTOR_STATUSES: Final[frozenset[str]] = frozenset({'draft', 'active', 'superseded', 'archived'})
INVENTORY_STATUSES: Final[frozenset[str]] = frozenset({'draft', 'calculating', 'calculated', 'under_review', 'approved', 'failed', 'superseded'})
RUN_STATUSES: Final[frozenset[str]] = frozenset({'queued', 'running', 'completed', 'completed_with_errors', 'failed', 'cancelled'})
ITEM_STATUSES: Final[frozenset[str]] = frozenset({'calculated', 'skipped', 'failed'})
MATCH_PRIORITY_ORG_PREFERENCE: Final[int] = 1
MATCH_PRIORITY_ACTIVITY_GEO_TECH: Final[int] = 2
MATCH_PRIORITY_ACTIVITY_GEO: Final[int] = 3
MATCH_PRIORITY_ACTIVITY_COUNTRY: Final[int] = 4
MATCH_PRIORITY_ACTIVITY_GLOBAL: Final[int] = 5
ACTIVITY_TYPE_DEFAULT_SCOPE: Final[dict[str, tuple[str, str]]] = {'purchased_electricity': ('scope_2', 'purchased_electricity'), 'generated_electricity': ('scope_1', 'stationary_combustion'), 'natural_gas_consumption': ('scope_1', 'stationary_combustion'), 'diesel_consumption': ('scope_1', 'stationary_combustion'), 'gasoline_consumption': ('scope_1', 'mobile_combustion'), 'lpg_consumption': ('scope_1', 'stationary_combustion'), 'hazardous_waste': ('scope_3', 'waste_generated_in_operations'), 'non_hazardous_waste': ('scope_3', 'waste_generated_in_operations'), 'recycled_waste': ('scope_3', 'waste_generated_in_operations'), 'road_freight': ('scope_3', 'upstream_transportation'), 'air_travel': ('scope_3', 'business_travel'), 'employee_commuting': ('scope_3', 'employee_commuting'), 'refrigerant_refill': ('scope_1', 'fugitive_emissions')}
