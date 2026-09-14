"""Purchased-electricity indirect emissions constants."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

METHODOLOGY_CODE = 'PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1'
METHODOLOGY_VERSION = '1'
FORMULA_VERSION = 'purchased-electricity-indirect-v1'
RESULT_UNIT = 'tCO2e'
FACTOR_DEFINITION_CODE = 'ELECTRICITY_GRID_EMISSION_FACTOR'

FACTOR_SOURCE_PLATFORM_DEFAULT = 'PLATFORM_DEFAULT'
FACTOR_SOURCE_MANUAL = 'MANUAL'

EXECUTION_STATUS_COMPLETED = 'COMPLETED'

ELECTRICITY_ACTIVITY_TYPE = 'ELECTRICITY'
ELECTRICITY_QUANTITY_UNITS = frozenset({'kWh', 'MWh'})
# Intensity units accepted for electricity (workbook uses tCO2/MWh; result stored as tCO2e).
ELECTRICITY_FACTOR_UNITS = frozenset(
    {
        'tCO2e/MWh',
        'kgCO2e/kWh',
        'kgCO2e/MWh',
        'tCO2e/kWh',
        'tCO2/MWh',
        'kgCO2/kWh',
        'kgCO2/MWh',
        'tCO2/kWh',
    }
)

CANONICAL_FACTOR_UNIT = 'tCO2e/MWh'

WORKBOOK_ALLOCATION_FILENAME = 'SKDM_Alokasyon_Sablon.xlsx'
WORKBOOK_SEE_FILENAME = (
    'CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx'
)
WORKBOOK_ALLOCATION_SHA256 = (
    '62300e30193aa2e696d07977697833431dcf782684cf61cace4e7e5f524cef72'
)
WORKBOOK_SEE_SHA256 = (
    '83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64'
)

# SKDM allocation template — facility electricity path (before product allocation).
WORKBOOK_FORMULA_REFS = (
    'SKDM!B2 Elektrik(KWh); SKDM!H4 Elektrik EF(tCO2/MWh)=0.439 (no provenance); '
    'SKDM!C9=(E3/D3)*(B3/1000) attributed MWh; SKDM!E9=D9*C9; SKDM!E12=C12*D12; '
    'SEE!D_Processes!T66=SUM(L65)*SUM(L66) consumption×EF; '
    'SEE!D_Processes!T72=-SUM(L71)*SUM(L72) exported×EF as separate negative direct path'
)

# Non-blocking seed-data blocker: workbooks show 0.439 without authoritative provenance.
TURKEY_DEFAULT_FACTOR_SEED_BLOCKER = (
    'TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING'
)

ZERO = Decimal('0')


def local_reference_path(filename: str) -> Path:
    # .../application → repo root is parents[7]
    # application, cbam, modules, ecotrace, src, api, apps, <repo>
    root = Path(__file__).resolve().parents[7]
    return root / 'local-reference' / filename
