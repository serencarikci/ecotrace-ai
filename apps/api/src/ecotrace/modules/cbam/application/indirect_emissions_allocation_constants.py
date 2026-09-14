"""Purchased-electricity indirect-emissions allocation identifiers."""

from __future__ import annotations

METHODOLOGY_CODE = "PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1"
METHODOLOGY_VERSION = "1.0.0"
WORKBOOK_FILENAME = "SKDM_Alokasyon_Sablon.xlsx"
WORKBOOK_SHA256 = "62300e30193aa2e696d07977697833431dcf782684cf61cace4e7e5f524cef72"
WORKBOOK_FORMULA_REFS = (
    "C9=IF(D3=0,0,(E3/D3)*(B3/1000)); "
    "E9=D9*C9; "
    "C12=SUM(C9:C11); "
    "E12=C12*D12; "
    "B16=$C$12; "
    "D19=$B$16*(B19/$B$26); "
    "exported electricity not in SKDM product allocation block"
)

RESULT_UNIT_ELECTRICITY = "MWh"
RESULT_UNIT_EMISSIONS = "tCO2e"

EXECUTION_STATUS_COMPLETED = "COMPLETED"
BALANCE_BALANCED = "BALANCED"
BALANCE_UNBALANCED = "UNBALANCED"
