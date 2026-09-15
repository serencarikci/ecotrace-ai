# Purchased precursors (Phase 10A backend + Phase 10B Angular)

**Status:** `PHASE_10A_BACKEND` + `PHASE_10B_ANGULAR`  
**Date:** 2026-08-30  
**Frontend:** Angular **Purchased precursors** section on the Purchased Inputs tab — no client math, no HYBRID, no product roll-up  
**Excel export:** out of scope  
**Tax / final product roll-up:** out of scope

## Authoritative workbooks

### CBAM SEE V2.1

- File: `CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx`
- SHA-256: `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64`
- Primary sheet: `E_PurchPrec` (Precursor 1 block; stride 44 across 20 slots)
- Master identity (country / name / routes / goods): `A_InstData` (not on `E_PurchPrec` itself)
- English labels: `Translations`

### EU default values (DV)

- File: `DVs_as_adopted_v20260204.xlsx` (local-reference only; **not** committed)
- SHA-256: `865372ed23649b7b02c9124f207fc0b0875fd244c45c19e9fb8cdb1e503a5003`
- Seed JSON: `apps/api/src/ecotrace/modules/cbam/data/cbam_precursor_defaults_v20260204.json`
- Dataset code/version: `CBAM_EU_DEFAULT_VALUES` / `IR_2025_2621_v20260204`
- Content checksum: `7543752e2ba7ccb314e6037355dfa2e11c65a0f129f6d27a0c5ffdd167c645c4`
- Value count: **12532**
- Regulation reference: Implementing Regulation (EU) 2025/2621

## SEE precursor field map (Precursor 1)

| Concept | Cell(s) | Notes |
|---------|---------|-------|
| Precursor name / goods | via `A_InstData` + `E_PurchPrec` header | SEE has **no** dedicated precursor CN cell on `E_PurchPrec` |
| Supplier identity | — | **Not** a workbook input cell; guidance only in Translations. EcoTrace optional `supplierId` |
| Country of origin | master / declarant entry | Required for `EU_DEFAULT` |
| Production route amounts | `L17:L24` | Summed into total |
| Total precursor quantity | `L25` | `=IF(G14="","",SUM(L17:L24))` |
| Quantity unit | adjacent unit cells | Mass units → EcoTrace canonical `t` |
| Product distribution (process uses) | `L28:L37` | Workbook targets process names; EcoTrace uses **typed product-profile versions** |
| Non-CBAM use | `L38` | Included in balance |
| Balance / control | `L39` | `=IF(OR(G14="",L25=""),"",SUM(L25)-SUM(L28:L38))` must be **0** |
| Specific direct embedded emissions | `L49` | tCO2e/t (SEE application unit) |
| Direct source Measured/Default/Unknown | adjacent source | Per-parameter in SEE |
| Electricity consumption intensity | `L50` | MWh/t |
| Electricity emission factor | `L51` | tCO2e/MWh — manually editable (meeting-confirmed) |
| Electricity EF source | `CONST_ElecSource` | D.4(a)…MIX |
| Specific indirect | `L52` | `=IF(COUNT(L50:L51)=0,"",L50*L51)` |
| Total direct embedded | `T49` | `=IF(OR(L25="",L49=""),"",L25*L49)` |
| Total indirect embedded | `T52` | `=IF(OR(L25="",L52=""),"",L25*L52)` |
| Default-value lookup | — | **No** automatic DV VLOOKUP on SEE; Default is a source flag; values still entered / resolved by EcoTrace |

### Summary / Communication consumers

SEE Summary/Communication sheets consume purchased-precursor totals through the SEE template graph. Phase 10A **does not** roll precursor embedded emissions into EcoTrace product totals or allocation engines.

## Quantity distribution / balance

```text
total (L25)
  = Σ CBAM product uses (L28:L37)
  + non-CBAM (L38)
remaining (L39) = total − distributed
```

- Exact Decimal after mass-unit conversion to tonnes
- **No** business tolerance
- Draft save allowed while incomplete/unbalanced
- Readiness requires remaining == 0 at canonical precision
- Typed rows: precursor → `targetProductProfileVersionId` + quantity + unit (not free-text process names)

## Data-source modes (V1)

| Mode | Meaning |
|------|---------|
| `SUPPLIER_DATA` | Supplier-specific L49/L50/L51 (+ provenance) |
| `EU_DEFAULT` | Resolved DV catalog row snapshotted onto the record |

- One authoritative primary mode per precursor version
- Mixing supplier emission fields with default-resolution fields → `MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED`
- **No HYBRID** mode invented; model retains extension point for future field-level provenance
- Workbook per-parameter Measured/Default/Unknown remains a controlled list for documentation only

### SUPPLIER_DATA

- Require specific direct + complete electricity pair for READY
- Provenance (`provenanceNotes` and/or `evidenceReference`) required when numeric emission values present
- Blank ≠ zero
- Incompatible units → `INCOMPATIBLE_PRECURSOR_UNIT`

### EU_DEFAULT

- Resolver key: **country + CN (+ production route when present) (+ goods description when needed to disambiguate)**
- Statuses: `RESOLVED` | `UNRESOLVED` | `AMBIGUOUS`
- Never pick arbitrary first/newest row
- Never invent country → “Other Countries and Territories” fallback (explicit selection only)
- On resolve: immutable snapshot of dataset/version/keys/direct/indirect/units onto the precursor
- Historical reads use snapshot, not live catalog

## DV workbook structure

- One sheet per country (plus `_Other Countries and Territorie`)
- Columns include: CN, description, direct/indirect/total defaults, mark-up totals 2026/2027/2028+, production route
- **No unit labels** in the DV workbook; EcoTrace applies SEE application units `tCO2e/t`
- Route often blank; some CN+null-route duplicates (e.g. cement white/grey) → AMBIGUOUS without description
- Lookup key: `country|cn|route|description` (empty segments allowed)

## Calculation decision

**Implemented** for unambiguous SEE formulas only:

```text
specific_indirect = intensity × electricity_EF          (L52)
total_direct      = quantity_tonnes × specific_direct   (T49)
total_indirect    = quantity_tonnes × specific_indirect (T52)
total             = total_direct + total_indirect
```

- Decimal only
- Direct / indirect / total kept separate
- **Not** rolled into final product totals (aggregation path not productized in EcoTrace yet)
- EU_DEFAULT uses snapshotted specific values × quantity (same formulas); DV unit labelling remains a documented caveat (`unitNote`)

## Readiness

Statuses: `EMPTY` | `INCOMPLETE` | `UNBALANCED` | `UNRESOLVED` | `AMBIGUOUS` | `READY`

Issue codes (server): `PRECURSOR_CN_CODE_REQUIRED`, `PRECURSOR_COUNTRY_REQUIRED`, `PRECURSOR_ROUTE_REQUIRED` (reserved), `PRECURSOR_QUANTITY_REQUIRED`, `PRECURSOR_DISTRIBUTION_*`, `PRECURSOR_TARGET_PRODUCT_INVALID`, `SUPPLIER_EMISSIONS_DATA_REQUIRED`, `SUPPLIER_PROVENANCE_REQUIRED`, `DEFAULT_VALUE_*`, `INCOMPATIBLE_PRECURSOR_UNIT`, `MIXED_PRECURSOR_SOURCE_NOT_SUPPORTED`

## Identity

Separate records for the same material from different suppliers. Do **not** merge by CN. Optional links: purchased-input record, supplier. Required for EU_DEFAULT: CN + country.

## API (binding-scoped + org catalog)

- Catalog search / resolve (`cbam:view`)
- Precursor list/detail/create/patch/archive (`view` / `configure`)
- Product-use CRUD (`configure`)
- Readiness / binding summary (`view`)
- Client must **not** submit calculated embedded emissions when backend can calculate them

## Angular UI

Phase 10B ships the Angular UI on top of this contract: a `Purchased precursors` section at the top of the period-detail **Purchased Inputs** tab. It exposes only `SUPPLIER_DATA` and `EU_DEFAULT`, clears the inactive mode's fields on switch, requires explicit selection of an EU default row, and renders every emission, balance and readiness value straight from the API (no browser math, no product-total roll-up).

## Out of scope

- Excel / SKDM export changes
- Tax calculations
- DEA / IEA / allocation engine changes
- Product-total roll-up of precursor emissions
- Hybrid field-level data sources
