"""Workbook-backed controlled lists for Conventional production processes (Phase 9A).

Values are stable codes extracted from CBAM SEE Parameters_Constants / Translations
English column (C). Labels are English originals — not Carbonemit translations.
"""

from __future__ import annotations

from dataclasses import dataclass

from ecotrace.modules.cbam.application.production_process_constants import (
    DATA_QUALITY_JUSTIFICATION_LIST_CODE,
    DATA_QUALITY_LIST_CODE,
    DATA_VERIFICATION_LIST_CODE,
    ELEC_EF_SOURCE_LIST_CODE,
    MONITORING_APPROACH_LIST_CODE,
    WORKBOOK_FILENAME,
    WORKBOOK_PRIMARY_SHEET,
    WORKBOOK_SHA256,
)


@dataclass(frozen=True, slots=True)
class ControlledListItem:
    code: str
    label_en: str
    description_en: str | None
    sort_order: int
    workbook_ref: str


@dataclass(frozen=True, slots=True)
class ControlledList:
    list_code: str
    title_en: str
    workbook_named_range: str
    workbook_sheet: str
    help_en: str | None
    items: tuple[ControlledListItem, ...]


# CONST_DataQuality → Parameters_Constants!B42:F42 → Translations C1875:C1879
_DATA_QUALITY = ControlledList(
    list_code=DATA_QUALITY_LIST_CODE,
    title_en='Data quality',
    workbook_named_range='CONST_DataQuality',
    workbook_sheet='Parameters_Constants',
    help_en=(
        'Used on sheet C_Emissions&Energy (H40), not on D_Processes. '
        'Exposed for typed frontend dropdowns.'
    ),
    items=(
        ControlledListItem(
            code='MOSTLY_MEASUREMENTS_AND_ANALYSES',
            label_en='Mostly measurements & analyses',
            description_en=None,
            sort_order=1,
            workbook_ref='Translations!C1875 / Parameters_Constants!B42',
        ),
        ControlledListItem(
            code='MOSTLY_MEASUREMENTS_AND_NATIONAL_STANDARD_FACTORS',
            label_en=(
                'Mostly measurements & national standard factors for e.g. the emission factor'
            ),
            description_en=None,
            sort_order=2,
            workbook_ref='Translations!C1876 / Parameters_Constants!C42',
        ),
        ControlledListItem(
            code='MOSTLY_MEASUREMENTS_AND_SECTOR_STANDARD_FACTORS',
            label_en=(
                'Mostly measurements & sector-specific standard factors for e.g. '
                'the emission factor'
            ),
            description_en=None,
            sort_order=3,
            workbook_ref='Translations!C1877 / Parameters_Constants!D42',
        ),
        ControlledListItem(
            code='MOSTLY_MEASUREMENTS_AND_INTERNATIONAL_STANDARD_FACTORS',
            label_en=(
                'Mostly measurements & international standard factors for e.g. '
                'the emission factor'
            ),
            description_en=None,
            sort_order=4,
            workbook_ref='Translations!C1878 / Parameters_Constants!E42',
        ),
        ControlledListItem(
            code='MOSTLY_DEFAULT_VALUES_EC',
            label_en='Mostly default values provided by the European Commission',
            description_en=None,
            sort_order=5,
            workbook_ref='Translations!C1879 / Parameters_Constants!F42',
        ),
    ),
)

_DATA_VERIFICATION = ControlledList(
    list_code=DATA_VERIFICATION_LIST_CODE,
    title_en='Data verification',
    workbook_named_range='CONST_DataVerification',
    workbook_sheet='Parameters_Constants',
    help_en='Parameters_Constants!B43:E43 (Translations C1880–C1882 + C634 Other/NA path).',
    items=(
        ControlledListItem(
            code='THIRD_PARTY_VERIFICATION',
            label_en='Third-party verification',
            description_en=None,
            sort_order=1,
            workbook_ref='Translations!C1880 / Parameters_Constants!B43',
        ),
        ControlledListItem(
            code='INTERNAL_AUDITS',
            label_en='Internal audits',
            description_en=None,
            sort_order=2,
            workbook_ref='Translations!C1881 / Parameters_Constants!C43',
        ),
        ControlledListItem(
            code='FOUR_EYES_PRINCIPLE',
            label_en='Four eyes principle',
            description_en=None,
            sort_order=3,
            workbook_ref='Translations!C1882 / Parameters_Constants!D43',
        ),
    ),
)

_DATA_QUALITY_JUSTIFICATION = ControlledList(
    list_code=DATA_QUALITY_JUSTIFICATION_LIST_CODE,
    title_en='Data quality justification',
    workbook_named_range='CONST_DataQualityJustification',
    workbook_sheet='Parameters_Constants',
    help_en='Parameters_Constants!B44:D44.',
    items=(
        ControlledListItem(
            code='UNREASONABLE_COSTS',
            label_en='Unreasonable costs for more accurate monitoring',
            description_en=None,
            sort_order=1,
            workbook_ref='Translations!C1883 / Parameters_Constants!B44',
        ),
        ControlledListItem(
            code='DATA_GAPS',
            label_en='Data gaps',
            description_en=None,
            sort_order=2,
            workbook_ref='Translations!C1884 / Parameters_Constants!C44',
        ),
        ControlledListItem(
            code='OTHER',
            label_en='Other',
            description_en=None,
            sort_order=3,
            workbook_ref='Translations!C638 / Parameters_Constants!D44',
        ),
    ),
)

# CONST_ElecSource → Parameters_Constants!B15:G15 (codes are Annex III section refs)
_ELEC_SOURCE = ControlledList(
    list_code=ELEC_EF_SOURCE_LIST_CODE,
    title_en='Source of the emission factor of the electricity',
    workbook_named_range='CONST_ElecSource',
    workbook_sheet='Parameters_Constants',
    help_en=(
        'D_Processes L67 (and stride copies). Annex III section codes. '
        'Translations!C2075 documents the dropdown purpose.'
    ),
    items=(
        ControlledListItem(
            code='D.4(a)',
            label_en='D.4(a)',
            description_en='Annex III D.4(a)',
            sort_order=1,
            workbook_ref='Parameters_Constants!B15',
        ),
        ControlledListItem(
            code='D.4(b)',
            label_en='D.4(b)',
            description_en='Annex III D.4(b)',
            sort_order=2,
            workbook_ref='Parameters_Constants!C15',
        ),
        ControlledListItem(
            code='D.4.1',
            label_en='D.4.1',
            description_en='Annex III D.4.1',
            sort_order=3,
            workbook_ref='Parameters_Constants!D15',
        ),
        ControlledListItem(
            code='D.4.2',
            label_en='D.4.2',
            description_en='Annex III D.4.2',
            sort_order=4,
            workbook_ref='Parameters_Constants!E15',
        ),
        ControlledListItem(
            code='D.4.3.1',
            label_en='D.4.3.1',
            description_en='Annex III D.4.3.1',
            sort_order=5,
            workbook_ref='Parameters_Constants!F15',
        ),
        ControlledListItem(
            code='D.4.3.2',
            label_en='D.4.3.2',
            description_en='Annex III D.4.3.2',
            sort_order=6,
            workbook_ref='Parameters_Constants!G15',
        ),
        ControlledListItem(
            code='MIX',
            label_en='Mix',
            description_en='Translations!C460',
            sort_order=7,
            workbook_ref='Parameters_Constants!H15 → Translations!C460',
        ),
    ),
)

# Source-stream monitoring approach (C_Emissions) — NOT process calculation method.
# Kept here so FE does not confuse Combustion/Process emissions/Mass Balance with
# Conventional process method.
_MONITORING_APPROACH = ControlledList(
    list_code=MONITORING_APPROACH_LIST_CODE,
    title_en='Monitoring approach (source streams — not process method)',
    workbook_named_range='CONST_MonitoringApproach',
    workbook_sheet='Parameters_Constants',
    help_en=(
        'Applies to source-stream monitoring on C_Emissions&Energy. '
        'Distinct from EcoTrace process calculation_method CONVENTIONAL.'
    ),
    items=(
        ControlledListItem(
            code='COMBUSTION',
            label_en='Combustion',
            description_en=None,
            sort_order=1,
            workbook_ref='Translations!C181 / Parameters_Constants!B56',
        ),
        ControlledListItem(
            code='PROCESS_EMISSIONS',
            label_en='Process emissions',
            description_en=None,
            sort_order=2,
            workbook_ref='Translations!C646 / Parameters_Constants!C56',
        ),
        ControlledListItem(
            code='MASS_BALANCE',
            label_en='Mass Balance',
            description_en=None,
            sort_order=3,
            workbook_ref='Translations!C194 / Parameters_Constants!D56',
        ),
    ),
)

_ALL_LISTS: dict[str, ControlledList] = {
    lst.list_code: lst
    for lst in (
        _DATA_QUALITY,
        _DATA_VERIFICATION,
        _DATA_QUALITY_JUSTIFICATION,
        _ELEC_SOURCE,
        _MONITORING_APPROACH,
    )
}


def list_production_process_controlled_lists() -> list[ControlledList]:
    return list(_ALL_LISTS.values())


def get_production_process_controlled_list(list_code: str) -> ControlledList | None:
    return _ALL_LISTS.get(list_code)


def data_quality_codes() -> frozenset[str]:
    return frozenset(i.code for i in _DATA_QUALITY.items)


def data_verification_codes() -> frozenset[str]:
    return frozenset(i.code for i in _DATA_VERIFICATION.items)


def data_quality_justification_codes() -> frozenset[str]:
    return frozenset(i.code for i in _DATA_QUALITY_JUSTIFICATION.items)


def workbook_extraction_metadata() -> dict[str, str]:
    return {
        'workbookFilename': WORKBOOK_FILENAME,
        'workbookSha256': WORKBOOK_SHA256,
        'primarySheet': WORKBOOK_PRIMARY_SHEET,
        'englishLabelColumn': 'Translations!C',
        'note': (
            'Stable codes are EcoTrace identifiers mapped 1:1 to English workbook labels. '
            'Do not use translated UI labels as persistence keys.'
        ),
    }


# Process-1 field map (authoritative D_Processes cells)
PROCESS_FIELD_MAP: dict[str, dict[str, str]] = {
    'process_index': {'cell': 'C11', 'note': '1-based process slot index'},
    'process_name': {
        'cell': 'G11',
        'note': 'INDEX(CNTR_List_ExistProdProcNames) from A_InstData!T83:T92',
    },
    'product_good': {
        'cell': 'L11',
        'note': 'Aggregated goods category from CNTR_List_ExistProdProc (A_InstData!S83:S92)',
    },
    'production_route_amounts': {
        'cell': 'L16:L23',
        'note': 'Per-route produced amounts; unit from CONST_LIST_GoodsUnit via K16',
    },
    'produced_quantity_total': {
        'cell': 'L24',
        'formula': 'SUM(L16:L23)',
        'note': 'Denominator for SEE; process-specific (not EcoTrace production records)',
    },
    'marketed_quantity': {'cell': 'L27', 'note': 'Good to market / directly supplied'},
    'market_share': {'cell': 'L28', 'formula': 'L27/L24', 'note': 'Derived — do not persist as input'},
    'all_to_market': {
        'cell': 'L29',
        'formula': 'AND(L24>0,L24=L27)',
        'note': 'Derived boolean — do not ask user',
    },
    'use_in_other_cbam_processes': {
        'cell': 'E32:E40 / L32:L40',
        'note': 'Target process name from CNTR_List_ExistProdProcNames + quantity',
    },
    'non_cbam_quantity': {'cell': 'L41', 'note': 'Consumed for non-CBAM goods'},
    'distribution_control': {
        'cell': 'L42',
        'formula': 'L24-SUM(L27,L32:L41)',
        'note': 'Must equal 0 for consistency; exact compare',
    },
    'heat_applicability': {'cell': 'K50', 'note': 'True/False measurable heat'},
    'waste_gas_applicability': {'cell': 'L50', 'note': 'True/False waste gases'},
    'indirect_relevance': {
        'cell': 'M50',
        'formula': 'INDEX(CONST_LIST_GoodsIndRel,MATCH(L11,CONST_LIST_Goods,0))',
        'note': 'Goods-driven; not a user boolean',
    },
    'direct_emissions_dir_em': {
        'cell': 'L54',
        'note': (
            'Workbook user entry DirEm*. EcoTrace exposes current DEA product allocation '
            'read-only instead of re-entry.'
        ),
    },
    'heat_imported_amount': {'cell': 'L57', 'unit': 'TJ'},
    'heat_exported_amount': {'cell': 'M57', 'unit': 'TJ'},
    'heat_imported_ef': {'cell': 'L58', 'unit': 'tCO2/TJ'},
    'heat_exported_ef': {'cell': 'M58', 'unit': 'tCO2/TJ'},
    'heat_attributed_emissions': {
        'cell': 'T58',
        'formula': 'L57*L58-M57*M58',
    },
    'waste_gas_imported_amount': {'cell': 'L61', 'unit': 'TJ'},
    'waste_gas_exported_amount': {'cell': 'M61', 'unit': 'TJ'},
    'waste_gas_ef_ui': {
        'cell': 'L62:M62',
        'note': 'UI/validation decimal cells; T62 does NOT use them',
    },
    'waste_gas_attributed_emissions': {
        'cell': 'T62',
        'formula': 'L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667',
        'note': 'CONST_EFNatGas=56.1 tCO2/TJ (Parameters_Constants!B13)',
    },
    'electricity_consumption': {'cell': 'L65', 'unit': 'MWh'},
    'electricity_ef': {'cell': 'L66', 'unit': 'tCO2/MWh'},
    'electricity_ef_source': {'cell': 'L67', 'list': 'CONST_ElecSource'},
    'indirect_emissions': {
        'cell': 'T66',
        'formula': 'L65*L66',
        'note': 'EcoTrace exposes current IEA product allocation read-only',
    },
    'exported_electricity_amount': {
        'cell': 'L71',
        'unit': 'MWh',
        'note': 'Process-level entry (Phase 10D); independent of the facility PE export',
    },
    'exported_electricity_ef': {'cell': 'L72', 'unit': 'tCO2/MWh'},
    'exported_electricity_embed': {
        'cell': 'T72',
        'formula': '-L71*L72',
        'note': (
            'Not subtracted from T66 (indirect). Server-calculated from the process L71/L72 '
            'entry; the facility purchased-electricity export is only reconciled, never '
            'copied or divided across processes.'
        ),
    },
}
