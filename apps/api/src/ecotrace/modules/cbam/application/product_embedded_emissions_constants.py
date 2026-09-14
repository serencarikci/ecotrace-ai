"""Product embedded-emissions roll-up constants (CBAM SEE D_Processes/Summary)."""

from __future__ import annotations

from typing import Final

METHODOLOGY_CODE = 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1'
METHODOLOGY_VERSION = '1.0.0'

# Phase 10D — full SEE roll-up fidelity: internal Leontief propagation plus the
# process-level T72 exported-electricity term. V1 and V2 keep separate current pointers,
# so promoting V2 never rewrites or invalidates a historical V1 result.
METHODOLOGY_CODE_V2 = 'CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2'
METHODOLOGY_VERSION_V2 = '2.0.0'
DEFAULT_METHODOLOGY_CODE = METHODOLOGY_CODE_V2
SUPPORTED_METHODOLOGY_CODES: Final[tuple[str, ...]] = (
    METHODOLOGY_CODE,
    METHODOLOGY_CODE_V2,
)
METHODOLOGY_VERSION_BY_CODE: Final[dict[str, str]] = {
    METHODOLOGY_CODE: METHODOLOGY_VERSION,
    METHODOLOGY_CODE_V2: METHODOLOGY_VERSION_V2,
}
CODE_METHODOLOGY_UNSUPPORTED = 'PRODUCT_EMBEDDED_EMISSIONS_METHODOLOGY_UNSUPPORTED'

WORKBOOK_FILENAME = (
    'CBAM SEE V2.1_Example Steel 3 Screws and nuts_final '
    'Dosyasının Kopyası- (1) (1).xlsx'
)
WORKBOOK_SHA256 = '83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64'
WORKBOOK_PRIMARY_SHEET = 'D_Processes'
WORKBOOK_SUMMARY_SHEET = 'Summary_Products'

# Process 1 attributed-emission block (stride 65) plus the product summary consumers.
WORKBOOK_FORMULA_REFS = (
    'D_Processes!L24=SUM(L16:L23); '
    'D_Processes!T54=DirEm_ (allocated direct emissions of the process); '
    'D_Processes!T58=L57*L58-M57*M58; '
    'D_Processes!T62=L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667; '
    'D_Processes!T66=L65*L66; '
    'D_Processes!T72=-L71*L72; '
    'D_Processes!S72=EmbedEmDir_; '
    'Summary_Products!I=direct specific; '
    'Summary_Products!J=indirect specific; '
    'Summary_Products!K=total specific'
)

# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
RESULT_UNIT_TCO2E = 'tCO2e'
SPECIFIC_UNIT_TCO2E_PER_T = 'tCO2e/t'
CANONICAL_MASS_UNIT = 't'
ELECTRICITY_UNIT_MWH = 'MWh'

# The direct-emissions allocation engine persists fossil CO2 in tCO2. The roll-up
# combines it with tCO2e quantities using numeric equivalence at GWP = 1 (CO2).
# Historical DEA field names are intentionally NOT renamed.
DEA_SOURCE_UNIT_TCO2 = 'tCO2'
WORKBOOK_GAS = 'CO2'
WORKBOOK_GWP = '1'
WORKBOOK_GWP_FACTOR = '1'
GWP_EQUIVALENCE_NOTE = (
    'Direct-emissions allocation product rows are stored in tCO2 (fossil CO2 only). '
    'The product roll-up reports tCO2e using numeric equivalence at GWP = 1 for CO2. '
    'No conversion factor is applied and no DEA field is renamed.'
)

# ---------------------------------------------------------------------------
# V1 scope limitations
# ---------------------------------------------------------------------------
EXPORTED_ELECTRICITY_NOTE_CODE = 'PROCESS_LEVEL_EXPORTED_ELECTRICITY_INPUTS_NOT_MODELED'
EXPORTED_ELECTRICITY_NOTE = (
    'Workbook D_Processes!T72 = -L71*L72 requires process-level exported electricity '
    'quantity and emission factor. EcoTrace does not model L71/L72 on the process, and '
    'facility-level purchased-electricity export must not be attributed to a single '
    'product. V1 snapshots exportedElectricityDirectTco2e = 0 and never invents an '
    'allocation. Indirect emissions are unaffected (workbook S72=EmbedEmDir_).'
)

INTERNAL_PRECURSOR_NOTE_CODE = 'INTERNAL_PROCESS_PRECURSOR_LEONTIEF_NOT_MODELED'
INTERNAL_PRECURSOR_NOTE = (
    'V1 covers purchased precursors only. EcoTrace has no process-as-precursor '
    'relation, so the workbook process-process block is zero and the Leontief system '
    'reduces to a direct sum of purchased-precursor contributions.'
)

DENOMINATOR_NOTE = (
    'The specific-emission denominator is the process produced quantity '
    '(D_Processes!L24 → TotProd_) converted to tonnes. Marketed quantity and the '
    'production-record sum are never used as the denominator; production records are '
    'reconciled only.'
)

# ---------------------------------------------------------------------------
# Statuses
# ---------------------------------------------------------------------------
EXECUTION_STATUS_COMPLETED = 'COMPLETED'
READINESS_READY = 'READY'
READINESS_NOT_READY = 'NOT_READY'

# ---------------------------------------------------------------------------
# Blocking issue codes (server-authoritative)
# ---------------------------------------------------------------------------
CODE_NO_ELIGIBLE_PRODUCTS = 'PRODUCT_EMBEDDED_EMISSIONS_NO_ELIGIBLE_PRODUCTS'
CODE_DEA_NOT_READY = 'DIRECT_EMISSIONS_ALLOCATION_NOT_READY'
CODE_DEA_STALE = 'DIRECT_EMISSIONS_ALLOCATION_STALE'
CODE_DEA_PRODUCT_ROW_MISSING = 'DEA_PRODUCT_ROW_MISSING'
CODE_IEA_NOT_READY = 'INDIRECT_EMISSIONS_ALLOCATION_NOT_READY'
CODE_IEA_STALE = 'INDIRECT_EMISSIONS_ALLOCATION_STALE'
CODE_IEA_PRODUCT_ROW_MISSING = 'IEA_PRODUCT_ROW_MISSING'
CODE_PROCESS_MISSING_FOR_PRODUCT = 'PROCESS_MISSING_FOR_PRODUCT'
CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT = 'PROCESS_AMBIGUOUS_FOR_PRODUCT'
CODE_PROCESS_NOT_READY = 'PROCESS_NOT_READY'
CODE_PROCESS_METHOD_UNSUPPORTED = 'PROCESS_METHOD_UNSUPPORTED'
CODE_PRECURSOR_NOT_READY = 'PRECURSOR_NOT_READY'
CODE_PRECURSOR_SPECIFIC_VALUES_MISSING = 'PRECURSOR_SPECIFIC_VALUES_MISSING'
CODE_PRECURSOR_USE_UNIT_INVALID = 'PRECURSOR_USE_UNIT_INVALID'
CODE_PRODUCT_DENOMINATOR_ZERO = 'PRODUCT_DENOMINATOR_ZERO'
CODE_PRODUCT_DENOMINATOR_MISSING = 'PRODUCT_DENOMINATOR_MISSING'
CODE_PRODUCT_DENOMINATOR_MISMATCH = 'PRODUCT_DENOMINATOR_MISMATCH'
CODE_PRODUCT_PROFILE_NOT_LINKABLE = 'PRODUCT_PROFILE_NOT_LINKABLE'

BLOCKING_ISSUE_CODES: Final[tuple[str, ...]] = (
    CODE_NO_ELIGIBLE_PRODUCTS,
    CODE_DEA_NOT_READY,
    CODE_DEA_STALE,
    CODE_DEA_PRODUCT_ROW_MISSING,
    CODE_IEA_NOT_READY,
    CODE_IEA_STALE,
    CODE_IEA_PRODUCT_ROW_MISSING,
    CODE_PROCESS_MISSING_FOR_PRODUCT,
    CODE_PROCESS_AMBIGUOUS_FOR_PRODUCT,
    CODE_PROCESS_NOT_READY,
    CODE_PROCESS_METHOD_UNSUPPORTED,
    CODE_PRECURSOR_NOT_READY,
    CODE_PRECURSOR_SPECIFIC_VALUES_MISSING,
    CODE_PRECURSOR_USE_UNIT_INVALID,
    CODE_PRODUCT_DENOMINATOR_ZERO,
    CODE_PRODUCT_DENOMINATOR_MISSING,
    CODE_PRODUCT_DENOMINATOR_MISMATCH,
    CODE_PRODUCT_PROFILE_NOT_LINKABLE,
)

# ---------------------------------------------------------------------------
# Stale reason codes
# ---------------------------------------------------------------------------
STALE_METHODOLOGY_OR_WORKBOOK_CHANGED = 'METHODOLOGY_OR_WORKBOOK_CHANGED'
STALE_DEA_CURRENT_RESULT_CHANGED = 'DEA_CURRENT_RESULT_CHANGED'
STALE_DEA_STALE = 'DIRECT_EMISSIONS_ALLOCATION_STALE'
STALE_DEA_PRODUCT_VALUE_CHANGED = 'DEA_PRODUCT_VALUE_CHANGED'
STALE_IEA_CURRENT_RESULT_CHANGED = 'IEA_CURRENT_RESULT_CHANGED'
STALE_IEA_STALE = 'INDIRECT_EMISSIONS_ALLOCATION_STALE'
STALE_IEA_PRODUCT_VALUE_CHANGED = 'IEA_PRODUCT_VALUE_CHANGED'
STALE_PRODUCT_SET_CHANGED = 'PRODUCT_SET_CHANGED'
STALE_PROCESS_CHANGED = 'PROCESS_CHANGED'
STALE_PROCESS_PRODUCED_QUANTITY_CHANGED = 'PROCESS_PRODUCED_QUANTITY_CHANGED'
STALE_PROCESS_HEAT_OR_WASTE_GAS_CHANGED = 'PROCESS_HEAT_OR_WASTE_GAS_CHANGED'
STALE_PRECURSOR_SET_CHANGED = 'PRECURSOR_SET_CHANGED'
STALE_PRECURSOR_CHANGED = 'PRECURSOR_CHANGED'
STALE_PRECURSOR_PRODUCT_USE_CHANGED = 'PRECURSOR_PRODUCT_USE_CHANGED'
STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED = 'PRECURSOR_SPECIFIC_VALUES_CHANGED'
STALE_PRECURSOR_DEFAULT_SNAPSHOT_CHANGED = 'PRECURSOR_DEFAULT_SNAPSHOT_CHANGED'
STALE_PRODUCTION_RECORDS_CHANGED = 'PRODUCTION_RECORDS_CHANGED'
STALE_PRODUCT_DENOMINATOR_CHANGED = 'PRODUCT_DENOMINATOR_CHANGED'
STALE_NOT_READY = 'PRODUCT_EMBEDDED_EMISSIONS_NOT_READY'

STALE_REASON_CODES: Final[tuple[str, ...]] = (
    STALE_METHODOLOGY_OR_WORKBOOK_CHANGED,
    STALE_DEA_CURRENT_RESULT_CHANGED,
    STALE_DEA_STALE,
    STALE_DEA_PRODUCT_VALUE_CHANGED,
    STALE_IEA_CURRENT_RESULT_CHANGED,
    STALE_IEA_STALE,
    STALE_IEA_PRODUCT_VALUE_CHANGED,
    STALE_PRODUCT_SET_CHANGED,
    STALE_PROCESS_CHANGED,
    STALE_PROCESS_PRODUCED_QUANTITY_CHANGED,
    STALE_PROCESS_HEAT_OR_WASTE_GAS_CHANGED,
    STALE_PRECURSOR_SET_CHANGED,
    STALE_PRECURSOR_CHANGED,
    STALE_PRECURSOR_PRODUCT_USE_CHANGED,
    STALE_PRECURSOR_SPECIFIC_VALUES_CHANGED,
    STALE_PRECURSOR_DEFAULT_SNAPSHOT_CHANGED,
    STALE_PRODUCTION_RECORDS_CHANGED,
    STALE_PRODUCT_DENOMINATOR_CHANGED,
    STALE_NOT_READY,
)

# Display-only fields that must never trigger a stale evaluation.
NON_MATERIAL_FIELDS: Final[tuple[str, ...]] = (
    'name',
    'identifier',
    'notes',
    'productName',
    'cnDisplayCode',
)

VALUE_SOURCE_SUPPLIER_DATA = 'SUPPLIER_DATA'
VALUE_SOURCE_EU_DEFAULT_SNAPSHOT = 'EU_DEFAULT_SNAPSHOT'

# ---------------------------------------------------------------------------
# Phase 10D (V2) — internal product flows and the T72 exported-electricity term
# ---------------------------------------------------------------------------
WORKBOOK_FORMULA_REFS_V2 = (
    'D_Processes!L24=SUM(L16:L23); '
    'D_Processes!L32:L40=internal use of other CBAM process outputs; '
    'D_Processes!T54=DirEm_ (allocated direct emissions of the process); '
    'D_Processes!T58=L57*L58-M57*M58; '
    'D_Processes!T62=L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667; '
    'D_Processes!T66=L65*L66; '
    'D_Processes!T72=-L71*L72; '
    'D_Processes!S72=EmbedEmDir_; '
    'SEE=(I-A)^-1·base with A[consumer][supplier]=qty/TotProd(consumer); '
    'Summary_Products!I=direct specific; '
    'Summary_Products!J=indirect specific; '
    'Summary_Products!K=total specific'
)

EXPORTED_ELECTRICITY_NOTE_CODE_V2 = 'PROCESS_LEVEL_EXPORTED_ELECTRICITY_MODELED'
EXPORTED_ELECTRICITY_NOTE_V2 = (
    'Workbook D_Processes!T72 = -L71*L72 is calculated from the process-level exported '
    'electricity quantity and emission factor entered on the production process. It '
    'reduces attributed direct emissions only; indirect emissions are unaffected '
    '(workbook S72=EmbedEmDir_). Facility purchased-electricity export is reconciled '
    'against the process entries and is never copied into or divided across processes.'
)

INTERNAL_PRECURSOR_NOTE_CODE_V2 = 'INTERNAL_PROCESS_PRECURSOR_LEONTIEF_MODELED'
INTERNAL_PRECURSOR_NOTE_V2 = (
    'Internal CBAM product flows between production processes form the workbook '
    'process-to-process matrix A[consumer][supplier] = consumed quantity / consumer '
    'produced quantity. Specific embedded emissions solve (I - A) · SEE = base with exact '
    'Decimal arithmetic. Marketed (L27) and non-CBAM (L41) quantities never enter A and '
    'purchased precursors stay outside the internal matrix.'
)

CODE_INTERNAL_PRODUCT_FLOW_SINGULAR = 'INTERNAL_PRODUCT_FLOW_SINGULAR'
CODE_INTERNAL_PRODUCT_FLOW_INVALID = 'INTERNAL_PRODUCT_FLOW_INVALID'
CODE_INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO = 'INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO'
CODE_INTERNAL_PRODUCT_FLOW_PROFILE_MISSING = 'INTERNAL_PRODUCT_FLOW_PROFILE_MISSING'
CODE_INTERNAL_PRODUCT_FLOW_UNBALANCED = 'INTERNAL_PRODUCT_FLOW_UNBALANCED'
CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE = 'INTERNAL_PRODUCT_FLOW_SELF_REFERENCE'
CODE_PROCESS_EXPORTED_ELECTRICITY_NOT_READY = 'PROCESS_EXPORTED_ELECTRICITY_NOT_READY'

INTERNAL_PRODUCT_FLOW_BLOCKING_CODES: Final[tuple[str, ...]] = (
    CODE_INTERNAL_PRODUCT_FLOW_SINGULAR,
    CODE_INTERNAL_PRODUCT_FLOW_INVALID,
    CODE_INTERNAL_PRODUCT_FLOW_DENOMINATOR_ZERO,
    CODE_INTERNAL_PRODUCT_FLOW_PROFILE_MISSING,
    CODE_INTERNAL_PRODUCT_FLOW_UNBALANCED,
    CODE_INTERNAL_PRODUCT_FLOW_SELF_REFERENCE,
    CODE_PROCESS_EXPORTED_ELECTRICITY_NOT_READY,
)

STALE_INTERNAL_PRODUCT_FLOW_SET_CHANGED = 'INTERNAL_PRODUCT_FLOW_SET_CHANGED'
STALE_INTERNAL_PRODUCT_FLOW_CHANGED = 'INTERNAL_PRODUCT_FLOW_CHANGED'
STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED = 'PROCESS_EXPORTED_ELECTRICITY_CHANGED'
STALE_EXPORTED_ELECTRICITY_RECONCILIATION_CHANGED = (
    'EXPORTED_ELECTRICITY_RECONCILIATION_CHANGED'
)

STALE_REASON_CODES_V2: Final[tuple[str, ...]] = (
    *STALE_REASON_CODES,
    STALE_INTERNAL_PRODUCT_FLOW_SET_CHANGED,
    STALE_INTERNAL_PRODUCT_FLOW_CHANGED,
    STALE_PROCESS_EXPORTED_ELECTRICITY_CHANGED,
    STALE_EXPORTED_ELECTRICITY_RECONCILIATION_CHANGED,
)


def workbook_formula_refs_for(methodology_code: str) -> str:
    return (
        WORKBOOK_FORMULA_REFS_V2
        if methodology_code == METHODOLOGY_CODE_V2
        else WORKBOOK_FORMULA_REFS
    )


def exported_electricity_note_for(methodology_code: str) -> tuple[str, str]:
    if methodology_code == METHODOLOGY_CODE_V2:
        return EXPORTED_ELECTRICITY_NOTE_CODE_V2, EXPORTED_ELECTRICITY_NOTE_V2
    return EXPORTED_ELECTRICITY_NOTE_CODE, EXPORTED_ELECTRICITY_NOTE


def internal_precursor_note_for(methodology_code: str) -> tuple[str, str]:
    if methodology_code == METHODOLOGY_CODE_V2:
        return INTERNAL_PRECURSOR_NOTE_CODE_V2, INTERNAL_PRECURSOR_NOTE_V2
    return INTERNAL_PRECURSOR_NOTE_CODE, INTERNAL_PRECURSOR_NOTE
