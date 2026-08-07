# CBAM Context Ownership Matrix

Prefer composition and references over adding CBAM columns to generic tables (`products`, `facilities`, etc.).

## Decision legend

| Decision | Meaning |
|----------|---------|
| OWNED_BY_CBAM | Created and mutated only inside `modules/cbam` |
| REFERENCED_FROM_EXISTING_MODULE | CBAM stores foreign UUID only; source owns lifecycle |
| REUSED_THROUGH_INTERFACE | Read/write via application service or port; no shared tables |
| EXTENDED_IN_EXISTING_MODULE | Existing module gains CBAM-agnostic capability used by CBAM |
| NOT_REUSED | Must not be used for CBAM results or compliance claims |
| PATTERN_ONLY | Copy established security/validation patterns; no existing shared port |

## Ownership table

| Concept | Decision | Current source | Proposed owner | Integration | Coupling risk | Migration risk | Reason |
|---------|----------|----------------|----------------|-------------|---------------|----------------|--------|
| organization | REFERENCED_FROM_EXISTING_MODULE | `organizations` | organizations | FK `organization_id` | Low | Low | Tenancy root |
| user and membership | REFERENCED_FROM_EXISTING_MODULE | `identity`, `organizations` | identity/orgs | actor IDs + `org_access` | Low | Low | Central auth |
| permissions / roles | EXTENDED_IN_EXISTING_MODULE | `identity` + `org_access` | identity + CBAM helpers | New `require_cbam_*` beside existing `require_*` | Medium | Low | SoD without forking auth (D-019) |
| facility | REFERENCED_FROM_EXISTING_MODULE | `facilities` | facilities | installation profile → `facility_id` | Medium | Low | No facility column pollution; cardinality D-041 |
| CBAM installation | OWNED_BY_CBAM | — | cbam | Profile table | Low | Low | CBAM-specific attributes |
| reporting period (generic) | REFERENCED_FROM_EXISTING_MODULE | `reporting_periods` | reporting_periods | binding → `reporting_period_id` | Medium | Medium | Dates/code only |
| CBAM period workflow/lock | OWNED_BY_CBAM | — | cbam | `CbamReportingPeriodBinding` | Low | Low | **CBAM lock source of truth**; generic lock not authoritative (D-031) |
| product | REFERENCED_FROM_EXISTING_MODULE | `products` | products | temporal product-profile versions → `product_id` | Medium | Low | CN/AGC on CBAM versions (D-029) |
| material | REFERENCED_FROM_EXISTING_MODULE | `materials` | materials | Optional FK on flows/lots | Low | Low | Master data |
| supplier | REFERENCED_FROM_EXISTING_MODULE | `suppliers` | suppliers | Precursor links | Low | Low | Master data |
| corporate activity record | REUSED_THROUGH_INTERFACE | `activity_data` | activity_data (read) | Optional one-way import **copy** into CBAM | High if live-joined | Medium | Semantics differ |
| **CbamActivityRecord** | OWNED_BY_CBAM | — | cbam | `cbam_activity_records` | Low | Low | Canonical CBAM activity entity |
| emission factor (corporate) | REUSED_THROUGH_INTERFACE | `emission_factors` | emission_factors + CBAM factor sets | Read port + **always snapshot** | High | Medium | Not CBAM default catalog |
| evidence storage | PATTERN_ONLY / OWNED_BY_CBAM | pattern in `activity_data.attachment_service` | cbam evidence (+ optional future shared port) | **No shared storage port exists today.** Do not import `activity_data` ORM/internals. Choose extract shared port **or** CBAM-owned service (D-042) | Medium | Low | F-11 correction |
| audit log | REUSED_THROUGH_INTERFACE | `shared.application.audit` | shared | `write_audit_log` / `cbam.*` | Low | Low | Existing table |
| approval workflow | OWNED_BY_CBAM | patterns elsewhere | cbam | `CbamApproval` | Medium | Low | Separate from carbon inventory; D-030 |
| calculation snapshot | OWNED_BY_CBAM | pattern from carbon/LCA | cbam | CBAM run/step JSON | Low | Low | Must not share carbon/LCA item tables |
| CN / AGC / CBAM FU | OWNED_BY_CBAM | — | cbam | Versioned catalogs + profile versions | Low | Low | Distinct from `LcaFunctionalUnit` |
| production process / route | OWNED_BY_CBAM | — | cbam | **Installation-scoped** masters | Low | Low | Periods do not own masters |
| process/system boundary | OWNED_BY_CBAM | — | cbam | Not `LcaSystemBoundary` | Medium | Low | Methodology differs |
| inventory receipt/lot/consumption | OWNED_BY_CBAM | — | cbam | Separate from corporate activity | Low | Low | D-033 |
| precursor / lot / graph | OWNED_BY_CBAM | — | cbam | Precursor model | Low | Low | Missing today |
| shipment | OWNED_BY_CBAM | — | cbam | Export/shipment | Low | Low | Missing today |
| allocation rule | OWNED_BY_CBAM | — | cbam | Not LCA allocation_factor | High if confused | Low | D-032 |
| CBAM calculation rule pack | OWNED_BY_CBAM | — | cbam | Versioned packs | Low | Low | Content blocked |
| CBAM calculation run | OWNED_BY_CBAM | — | cbam | Immutable runs/steps | Low | Low | Separate engines |
| operator emissions report | OWNED_BY_CBAM | — | cbam | Not analytics CSV | Low | Low | |
| verification package | OWNED_BY_CBAM | — | cbam | Evidence+traces bundle | Low | Low | D-038 |
| idempotency store | OWNED_BY_CBAM (new) | — | cbam (+ optional shared later) | New capability; not present repo-wide (D-040) | Medium | Low | F-15 |

## Explicit non-reuse

| Existing capability | Decision | Reason |
|---------------------|----------|--------|
| `carbon_accounting` / `carbon_inventory` results | NOT_REUSED | Scope inventory ≠ SEE |
| `lifecycle_assessment` runs / items / engines | NOT_REUSED | Disclaimer excludes CBAM |
| `product_carbon_footprint` | NOT_REUSED | PCF ≠ SEE |
| AI agents / copilot for compliance numbers | NOT_REUSED | Non-deterministic |
| Claiming existing spreadsheet-formula sanitization | NOT_REUSED | Not evidenced in code; CBAM must add explicit policy (F-12) |

## Extension / pattern notes

| Item | Where | Scope |
|------|-------|-------|
| CBAM permission helpers | `org_access` or cbam-local wrappers | Role checks only |
| Decimal/unit utilities | `reference_data.unit_conversion` | Pure functions + **snapshot** conversion factors |
| Evidence storage | D-042 | Port extract **or** CBAM-owned pattern copy — decide explicitly |
| CSV validation (headers/UTF-8/row limits) | `data_imports` patterns | Reuse only where code supports; **formula injection is new** |
| Idempotency | New CBAM capability | Before first REQUIRED op (D-040) |
