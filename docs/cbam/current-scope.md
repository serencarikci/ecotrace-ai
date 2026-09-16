# CBAM / SKDM — Current MVP Scope (Frozen)

**Classification:** `MVP_ACCEPTANCE_PASSED` (Official SEE path 2026-08-31)
**Not claimed:** regulatory-ready, official-CBAM submission-ready

## Implemented workflow (current product path)

Installation → Reporting Period → Product Profiles → Production (+ monthly D/E) → Activities → Direct Emissions → Indirect Emissions → Processes → Purchased Inputs / Precursors → Product Results (PEE V2) → Allocation (DEA / IEA) → Factors / Calculation (generic path) → Report / Excel (**Official SEE** + Internal Excel)

> Older bullets below may say “Excel export / allocation / precursors still out of scope” for the phase in which they were written. Those lines are historical phase notes. **Later phases supersede them:** PEE V2, precursors, DEA/IEA, and Official SEE are implemented. Migration head: `0032_cbam_prec_audit`. The supported Docker API image ships **TDF LibreOffice 26.8** for Official SEE; GitHub Actions does not yet run the golden LO job on amd64.

## Included

- Organization-scoped installations and reporting-period bindings
- Product profile versions (structure only; no CN invent)
- Production / activity / activity properties / purchased inputs
- Allocation methods: DIRECT_ASSIGNMENT, PRODUCTION_QUANTITY_RATIO, MANUAL_RATIO
- Primary/default factor resolution (fail-closed)
- Minimal calculation: `MULTIPLY_ACTIVITY_BY_FACTOR` only
- Stationary-combustion domain math `STATIONARY_COMBUSTION_CO2_V1` (Phase 1)
- Stationary-combustion fuel reference catalog (Phase 2; NATURAL_GAS IPCC 2006 seed; density null)
- Stationary-combustion orchestration + immutable typed result snapshot (Phase 3)
- Stationary-combustion REST API for fuel discovery, execution, and result retrieval (Phase 4A; no UI)
- Stationary-combustion **Direct Emissions** Angular tab (Phase 4B + 5B): eligible fuel-use selection from activity-coverage API, published reference values, explicit density for volume fuels, `clientRequestId` idempotent execution, result list/detail with Current/History/Out of date, period summary/readiness/totals from backend; per-activity CTA from coverageStatus (not history page); activity creation stays in Activities; full A→E wizard redesign remains future work
- Stationary-combustion **current-result pointer** + period summary/readiness API + paginated activity-coverage API (Phase 5A/5B; period totals only; no monthly breakdown; no allocation)
- CBAM **CN-code catalog** + versioned **product-profile classification** (Phase 6A / 6A+; SEE workbook seed; steel special parameters; authoritative per-CN `fieldApplicability`; computed `classificationReady`; allocation still unavailable)
- CBAM **Product Profiles** Angular tab (Phase 6B): period-detail tab before Production; org products list; CN search; draft/publish/new-version/archive; server-authoritative applicability and readiness; no coating field; allocation still out of scope
- CBAM **Production ↔ Product Profile** integration (Phase 6C): production writes require an active `classificationReady` profile version; historical immutable references remain readable after supersede/archive (`profileLinkStatus` READY|OUTDATED|MISSING|INVALID); legacy null links stay readable and explicitly linkable; binding-scoped `production-profile-link-summary`; no automatic newest-profile assignment; **allocation still out of scope**
- CBAM **direct-emissions allocation workbook gate (Phase 7A analysis):** `docs/cbam/direct-emissions-allocation-workbook.md`
- CBAM **monthly production-basis D/E inputs (Phase 7A-0):** binding-scoped monthly rows for workbook **Tonaj üretim** (D) and **SKDM kapsamında ithalatçı firmaya giden miktar** (E); month coverage summary; SC date compatibility; production reconciliation; **allocation execution still out of scope**
- CBAM **Monthly allocation data** Angular section (Phase 7A-1): Production tab entry for monthly D (Total production) and E (Amount sent to the importer); backend-authoritative `cbamShare`, month coverage, `allocationBasisReady`, production reconciliation warnings, and stationary-combustion compatibility; **no Calculate/Allocate controls; no period-wide sum(E)/sum(D); allocation execution still out of scope**
- CBAM **direct-emissions allocation engine (Phase 7A-2):** dedicated `STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1` two-stage monthly E/D attribution + product-profile quantity split; immutable snapshots; current/history/stale; idempotent executions; **Angular allocation UI still out of scope**
- CBAM **Direct emissions allocation** Angular section (Phase 7A-3): Allocation tab section (alongside preserved generic allocation rules); backend-authoritative readiness/summary/history/detail; `clientRequestId` calculate / calculate-again / update; current/history/stale from `isCurrent`/`isStale`; stored totals in **tCO2** (workbook display may show tCO2e for fossil CO2); no client-side allocation math; electricity / process / precursor allocation and Excel export remain out of scope
- CBAM **purchased-electricity indirect emissions backend (Phase 8A):** methodology `PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1`; `electricity_MWh × factor → tCO2e`; manual factor with mandatory provenance; platform-default extension point **without** seeding unverified Turkey `0.439`; exported electricity stored separately (not subtracted); immutable snapshots + current/history/stale + `clientRequestId` idempotency; **Angular UI and product allocation still out of scope**
- CBAM **Indirect Emissions** Angular tab (Phase 8B): period-detail tab after Direct Emissions; eligible `ELECTRICITY` kWh/MWh activity selection; `PLATFORM_DEFAULT` / `MANUAL` factor sources (no hard-coded Turkey factor; verified default missing message); exported electricity separate optional fields; backend-authoritative tCO2e summary/history/detail; `clientRequestId` calculate / calculate-again / update; **product allocation still out of scope**
- CBAM **purchased-electricity indirect-emissions allocation backend (Phase 8C):** methodology `PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1`; two-stage monthly E/D attribution of immutable PE MWh + tCO2e snapshots + product-profile quantity split; exported electricity snapshotted separately (not subtracted / not allocated); current/history/stale + `clientRequestId` idempotency; **Angular allocation UI still out of scope**
- CBAM **Indirect emissions allocation** Angular section (Phase 8D): Allocation tab section after Direct emissions allocation and before Generic allocation rules; backend-authoritative readiness/summary/history/detail; `clientRequestId` calculate / calculate-again / update; MWh + tCO2e display (no browser math); exported electricity shown separately; process / precursor / Excel export remain out of scope
- CBAM **Conventional production processes backend (Phase 9A):** binding-scoped `CONVENTIONAL` process drafts with product-quantity distribution balance (exact Decimal; draft save allowed while unbalanced; readiness blocked when remaining ≠ 0); typed use-in-other-CBAM-product relations; read-only current DEA/IEA + exported electricity reuse; conditional measurable heat / waste-gas inputs with workbook formulas; workbook-extracted controlled lists; **precursors, Process Emissions/Mass Balance methods, Excel export out of scope**
- CBAM **Processes** Angular tab (Phase 9B): period-detail tab after Indirect Emissions and before Purchased Inputs; Conventional-only create/edit/archive drafts; product distribution (market / other-CBAM rows / non-CBAM); backend-authoritative balance and readiness; read-only DEA/IEA + facility exported electricity with allocation deep-links; conditional measurable heat / waste gas / process exported electricity (Phase 10D T72) with null clearing; controlled-list data quality; no client emissions/balance/heat/waste-gas/T72 math; precursors / Excel / Process Emissions / Mass Balance / product-summary UI remain out of scope
- CBAM **Process ↔ IEA product electricity contract (Phase 9C):** Conventional Process responses expose immutable current IEA product-row `allocatedElectricityMwh` + `allocatedIndirectEmissionsTco2e` matched strictly by `productProfileVersionId` (fail-closed when missing; stale current values nulled); Angular Processes tab displays both read-only; no new calculation or migration
- CBAM **Purchased precursors backend (Phase 10A):** binding-scoped precursor drafts with `SUPPLIER_DATA` | `EU_DEFAULT` (no hybrid); versioned immutable EU default-value catalog from `DVs_as_adopted_v20260204` (12532 rows); resolver RESOLVED/UNRESOLVED/AMBIGUOUS; immutable default snapshots; typed product-profile distribution + non-CBAM balance (exact Decimal); standalone embedded-emission calc from SEE formulas (not rolled into product totals); readiness EMPTY…READY; Excel export / tax / DEA-IEA changes out of scope
- CBAM **Purchased precursors** Angular section (Phase 10B): Purchased Inputs tab section above the generic purchased-input table; create/edit/archive drafts with `Supplier data` | `EU default` modes only (no hybrid; switching a mode clears the other mode's fields before save); CN autocomplete identity; EU default catalog search + resolve with explicit row selection (never auto-select, `Other countries` opt-in) and immutable saved snapshots; product-use distribution CRUD with backend-authoritative balance (unbalanced drafts still saveable); read-only calculated embedded emissions incl. rollup note; no client-side emission or balance math; Excel export / product roll-up remain out of scope
- CBAM **Product embedded-emissions roll-up backend (Phase 10C):** binding-scoped immutable roll-up (`CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1`) that combines current DEA product fossil CO2 (T54), process measurable heat (T58) and waste gas (T62) with current IEA product indirect emissions (T66) and purchased-precursor contributions (product-use tonnes × specific direct/indirect); absolute tCO2e + specific tCO2e/t over the process produced quantity (`L24`, production records reconciled not substituted); exported electricity T72 always 0 with `PROCESS_LEVEL_EXPORTED_ELECTRICITY_INPUTS_NOT_MODELED`; no internal process-as-precursor Leontief; readiness/execute/list/detail/summary with DEA-style idempotency, current pointer and stale reasons; **Angular, Excel export, tax and HYBRID precursor mode out of scope**
- CBAM **Product embedded-emissions V2 + process T72 (Phase 10D):** default methodology `CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2` with exact Decimal Leontief internal product-flow propagation and process-level exported electricity (`T72=-L71*L72`, may be negative, direct bucket only); V1 remains callable with a separate current pointer; Processes Angular adds conditional exported-electricity fields (qty MWh, EF, provenance) with server-only T72 and reconciliation warning; **product-summary Angular and Excel export still out of scope**
- CBAM **Product Results** Angular tab (Phase 11A): period-detail lazy tab after Purchased Inputs and before Allocation; backend-authoritative PEE readiness/summary/history/detail; `clientRequestId` calculate / calculate-again / update (V2 default, no methodology picker); product table + own/precursor/internal/T72 breakdown from immutable result only; Current/History/Out of date; blocking-section deep-links; no client emissions math; **Excel export / tax / HYBRID still out of scope**
- CBAM **Official SEE Excel export (Phase 12A backend + Phase 12B Angular download UI):** surgical ZIP/XML writer; DB-backed PEE V2 ↔ LibreOffice I/J/K parity; Report / Excel tab **Official Excel** section (readiness, generate with `clientRequestId`, history, authenticated download); internal Excel export preserved; PDF/CSV/tax/HYBRID/Process Emissions/Mass Balance out of scope
- Internal SKDM workbook export + manifest + period summary
- Permissions `cbam:view` / `cbam:configure`
- Optimistic concurrency (`rowVersion` → 409)
- Audit for major CBAM actions
- Angular SKDM workflow tabs through **Rapor / Excel** (includes Product Profiles, Direct Emissions, Indirect Emissions, Processes, Product Results, and Official Excel download)

## Explicitly out of scope (frozen)

- CN / AGC classification
- Shipment
- Evidence upload
- Automatic IPCC/DEFRA/EPA numeric import
- Financial CBAM / certificate quantities
- New allocation methods or calculation formulas
- Sector-specific engines
- Official submission API
- Official EU workbook fabrication

## Official workbook

**Phase 12A + 12B accepted** (backend publish/download + Angular Official Excel UI on Report / Excel). See `docs/cbam/official-see-export.md`.
