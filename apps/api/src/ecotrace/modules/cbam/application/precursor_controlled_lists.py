"""Workbook-backed controlled lists for purchased precursors (Phase 10A).

Codes are stable EcoTrace identifiers mapped 1:1 to the English labels of the
CBAM SEE Parameters_Constants named ranges used by E_PurchPrec. Labels are the
English workbook originals, not UI translations.
"""

from __future__ import annotations

from ecotrace.modules.cbam.application.precursor_constants import (
    DEFAULT_JUSTIFICATION_LIST_CODE,
    ELEC_SOURCE_LIST_CODE,
    MEAS_DEFAULT_UNKNOWN_LIST_CODE,
    PARAMETER_SOURCE_DEFAULT,
    PARAMETER_SOURCE_MEASURED,
    PARAMETER_SOURCE_UNKNOWN,
    WORKBOOK_FILENAME,
    WORKBOOK_PRIMARY_SHEET,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.production_process_controlled_lists import (
    ControlledList,
    ControlledListItem,
)

# CONST_MeasDefaultUnknown — per-parameter data-source switch on E_PurchPrec.
_MEAS_DEFAULT_UNKNOWN = ControlledList(
    list_code=MEAS_DEFAULT_UNKNOWN_LIST_CODE,
    title_en="Determination of the parameter",
    workbook_named_range="CONST_MeasDefaultUnknown",
    workbook_sheet="Parameters_Constants",
    help_en=(
        "Per-parameter switch in the workbook. Phase 10A activates whole-record modes "
        "SUPPLIER_DATA and EU_DEFAULT only and rejects mixing them on one precursor."
    ),
    items=(
        ControlledListItem(
            code=PARAMETER_SOURCE_MEASURED,
            label_en="Measured",
            description_en="Value determined by the precursor supplier (actual data).",
            sort_order=1,
            workbook_ref="Parameters_Constants!CONST_MeasDefaultUnknown",
        ),
        ControlledListItem(
            code=PARAMETER_SOURCE_DEFAULT,
            label_en="Default",
            description_en="Value taken from the Commission default values.",
            sort_order=2,
            workbook_ref="Parameters_Constants!CONST_MeasDefaultUnknown",
        ),
        ControlledListItem(
            code=PARAMETER_SOURCE_UNKNOWN,
            label_en="Unknown",
            description_en="Determination method not known. Not accepted in Phase 10A V1.",
            sort_order=3,
            workbook_ref="Parameters_Constants!CONST_MeasDefaultUnknown",
        ),
    ),
)

# CONST_ElecSource — Annex III section codes for the electricity emission factor.
_ELEC_SOURCE = ControlledList(
    list_code=ELEC_SOURCE_LIST_CODE,
    title_en="Source of the emission factor of the electricity",
    workbook_named_range="CONST_ElecSource",
    workbook_sheet="Parameters_Constants",
    help_en="E_PurchPrec electricity emission-factor source. Annex III section codes.",
    items=(
        ControlledListItem(
            code="D.4(a)",
            label_en="D.4(a)",
            description_en="Annex III D.4(a)",
            sort_order=1,
            workbook_ref="Parameters_Constants!B15",
        ),
        ControlledListItem(
            code="D.4(b)",
            label_en="D.4(b)",
            description_en="Annex III D.4(b)",
            sort_order=2,
            workbook_ref="Parameters_Constants!C15",
        ),
        ControlledListItem(
            code="D.4.1",
            label_en="D.4.1",
            description_en="Annex III D.4.1",
            sort_order=3,
            workbook_ref="Parameters_Constants!D15",
        ),
        ControlledListItem(
            code="D.4.2",
            label_en="D.4.2",
            description_en="Annex III D.4.2",
            sort_order=4,
            workbook_ref="Parameters_Constants!E15",
        ),
        ControlledListItem(
            code="D.4.3.1",
            label_en="D.4.3.1",
            description_en="Annex III D.4.3.1",
            sort_order=5,
            workbook_ref="Parameters_Constants!F15",
        ),
        ControlledListItem(
            code="D.4.3.2",
            label_en="D.4.3.2",
            description_en="Annex III D.4.3.2",
            sort_order=6,
            workbook_ref="Parameters_Constants!G15",
        ),
        ControlledListItem(
            code="MIX",
            label_en="Mix",
            description_en="Translations!C460",
            sort_order=7,
            workbook_ref="Parameters_Constants!H15 → Translations!C460",
        ),
    ),
)

# Why a Commission default value is used instead of supplier data.
_DEFAULT_JUSTIFICATION = ControlledList(
    list_code=DEFAULT_JUSTIFICATION_LIST_CODE,
    title_en="Justification for using default values",
    workbook_named_range="CONST_DataQualityJustification",
    workbook_sheet="Parameters_Constants",
    help_en="Reused from Parameters_Constants!B44:D44 for the EU_DEFAULT precursor mode.",
    items=(
        ControlledListItem(
            code="SUPPLIER_DATA_UNAVAILABLE",
            label_en="Data gaps",
            description_en="Supplier could not provide actual embedded-emission data.",
            sort_order=1,
            workbook_ref="Translations!C1884 / Parameters_Constants!C44",
        ),
        ControlledListItem(
            code="UNREASONABLE_COSTS",
            label_en="Unreasonable costs for more accurate monitoring",
            description_en=None,
            sort_order=2,
            workbook_ref="Translations!C1883 / Parameters_Constants!B44",
        ),
        ControlledListItem(
            code="OTHER",
            label_en="Other",
            description_en=None,
            sort_order=3,
            workbook_ref="Translations!C638 / Parameters_Constants!D44",
        ),
    ),
)

_ALL_LISTS: dict[str, ControlledList] = {
    lst.list_code: lst for lst in (_MEAS_DEFAULT_UNKNOWN, _ELEC_SOURCE, _DEFAULT_JUSTIFICATION)
}


def list_precursor_controlled_lists() -> list[ControlledList]:
    return list(_ALL_LISTS.values())


def get_precursor_controlled_list(list_code: str) -> ControlledList | None:
    return _ALL_LISTS.get(list_code)


def parameter_source_codes() -> frozenset[str]:
    return frozenset(item.code for item in _MEAS_DEFAULT_UNKNOWN.items)


def electricity_source_codes() -> frozenset[str]:
    return frozenset(item.code for item in _ELEC_SOURCE.items)


def default_justification_codes() -> frozenset[str]:
    return frozenset(item.code for item in _DEFAULT_JUSTIFICATION.items)


def workbook_extraction_metadata() -> dict[str, str]:
    return {
        "workbookFilename": WORKBOOK_FILENAME,
        "workbookSha256": WORKBOOK_SHA256,
        "primarySheet": WORKBOOK_PRIMARY_SHEET,
        "englishLabelColumn": "Translations!C",
        "note": (
            "E_PurchPrec has no precursor CN-code or supplier cells. EcoTrace adds CN code "
            "and country of origin because the EU default-value lookup requires them."
        ),
    }


PRECURSOR_FIELD_MAP: dict[str, dict[str, str]] = {
    "purchased_quantity_total": {
        "cell": "L25",
        "formula": "SUM(production-route amounts)",
        "note": "Total purchased precursor amount; SEE distribution numerator",
    },
    "use_in_cbam_processes": {
        "cell": "L28:L37",
        "note": "Amount of the precursor consumed per CBAM production process/product",
    },
    "non_cbam_quantity": {"cell": "L38", "note": "Consumed for non-CBAM goods"},
    "distribution_control": {
        "cell": "L39",
        "formula": "L25-SUM(L28:L38)",
        "note": "Must equal 0 for consistency; exact compare (no tolerance)",
    },
    "specific_direct_embedded_emissions": {
        "cell": "L49",
        "unit": "tCO2e/t",
        "note": "Specific direct embedded emissions of the purchased precursor",
    },
    "total_direct_embedded_emissions": {
        "cell": "T49",
        "formula": "L25*L49",
        "unit": "tCO2e",
    },
    "electricity_consumption_intensity": {
        "cell": "L50",
        "unit": "MWh/t",
        "note": "Electricity consumed per tonne of purchased precursor",
    },
    "electricity_emission_factor": {
        "cell": "L51",
        "unit": "tCO2e/MWh",
        "note": "Emission factor of that electricity; source list CONST_ElecSource",
    },
    "specific_indirect_embedded_emissions": {
        "cell": "L52",
        "formula": "L50*L51",
        "unit": "tCO2e/t",
    },
    "total_indirect_embedded_emissions": {
        "cell": "T52",
        "formula": "L25*L52",
        "unit": "tCO2e",
    },
    "cn_code": {
        "cell": "n/a",
        "note": "EcoTrace-only. Required to resolve an EU default value.",
    },
    "country_of_origin": {
        "cell": "n/a",
        "note": "EcoTrace-only. Required to resolve an EU default value.",
    },
    "supplier": {
        "cell": "n/a",
        "note": "EcoTrace-only optional identity link to the suppliers module.",
    },
}
