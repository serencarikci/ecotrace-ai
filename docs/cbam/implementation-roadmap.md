# CBAM Implementation Roadmap

Dependency-ordered phases for the existing EcoTrace modular monolith.  
Does **not** re-implement identity, tenancy, Decimal math utilities, audit, or generic period master data.

## Required dependency order (canonical)

1. CBAM skeleton and permissions  
2. Installation / product-profile versions / period bindings (+ evidence decision D-042)  
3. Reference-data structures (empty/versioned; no invented CN/AGC)  
4. Processes, routes, boundaries, and flows (**installation-scoped**)  
5. `CbamActivityRecord` activity collection  
6. Inventory receipts, lots, and process consumption  
7. Precursors and complex-goods graph  
8. Allocation rules and allocation applications  
9. Deterministic calculation engine and snapshots  
10. Shipments and shipment-level calculation  
11. Reports, approval, locking, revisions, and verification package  
12. Pilot and expert-approved golden tests  

### Calculation scope notes

- Core **product-specific** embedded-emission calculation may run **without** a shipment (phase 9 can succeed for product scope before phase 10).
- **Shipment-level** embedded emissions require phase 10.
- A calculation that **requires** inventory consumption must be **`blocked`** until consumption data exists — no fake/provisional consumption.
- Idempotency foundation (D-040) lands before the first REQUIRED operation (staged-import confirm, calculation request, report generation, verification-package generation).

---

## Phase 0 — Specification freeze

| Item | Content |
|------|---------|
| Goal | ADRs + ownership + decision register acknowledged |
| Docs | `docs/cbam/*`, `docs/adr/0001–0004` |
| Acceptance | BLOCKED_DOMAIN list known; F-* corrections applied |
| Out of scope | any code |

## Phase 1 — Module skeleton, permissions, idempotency foundation

| Item | Content |
|------|---------|
| Goal | Empty `modules/cbam`; RBAC helpers; feature flag; **idempotency-store design/skeleton** for REQUIRED ops (D-040) |
| Reusable | identity, org_access, CamelModel, audit |
| New | package layout; optional unmounted routers; idempotency table/design owned by CBAM |
| Docs | api-conventions CBAM path note |
| Tests | authz helpers; **architecture forbidden-import test** (planned) |
| Acceptance | no LCA/carbon imports; routes preferably not public until phase 2 |
| Out of scope | domain tables, calculations, inventing roles beyond baseline helpers |

### Phase 1 implementation status

| Deliverable | Status |
|-------------|--------|
| `apps/api/src/ecotrace/modules/cbam/` package | Done |
| `GET /api/v1/cbam/organizations/{organizationId}/module-status` | Done (foundation status only; not a calculation/compliance endpoint) |
| CBAM permission vocabulary + `require_cbam_*` helpers | Done (baseline EcoTrace roles; D-019/D-038 roles not invented) |
| Architecture forbidden-import test | Done |
| Frontend `features/cbam` SKDM shell + `/app/cbam` | Done |
| Feature flag | Not added (repository has no standard feature-flag mechanism) |
| Idempotency DB table / retention / replay (D-040) | **BLOCKED_DECISION** — deferred; no Phase 1 REQUIRED mutating op yet |
| Domain tables / migrations / calculations | Out of scope (not started) |

Later phases remain incomplete.

## Phase 2 — Foundation aggregates

| Item | Content |
|------|---------|
| Goal | Installation profiles (cardinality per D-041 pilot constraint), **temporal product-profile versions**, period bindings, evidence links |
| Reusable | facilities, reporting_periods, products refs |
| New | `cbam_installation_profiles`, `cbam_product_profile_versions`, `cbam_reporting_period_bindings`, `cbam_evidence_links` |
| Evidence | D-042: extract shared port **or** CBAM-owned evidence service (pattern from `attachment_service`, not internal import) |
| BE | CRUD; `draft→data_collection` only for periods; **do not activate** final approve/lock (D-030) |
| FE | installation-scoped setup; periods dashboard shell |
| Acceptance | no columns on `products`/`facilities`; CBAM lock fields on binding only |
| Out of scope | CN content, calculations |

## Phase 3 — Reference data versioning (structure only)

| Item | Content |
|------|---------|
| Goal | Versioned catalog tables without inventing CN/AGC values |
| New | `cbam_reference_data_versions`, CN/AGC tables, org pins |
| Acceptance | publish/pin; content import explicit later |
| Out of scope | inventing codes |

## Phase 4 — Process, route, boundary, flows

| Item | Content |
|------|---------|
| Goal | **Installation-scoped** process/route masters |
| FE | under `app/cbam/installations/:installationId/...` — not under period ownership |
| Acceptance | periods reference/snapshot only |
| Out of scope | formulas; sharing policy beyond structure (D-034) |

## Phase 5 — CBAM activity records

| Item | Content |
|------|---------|
| Goal | Period-scoped **`CbamActivityRecord`** with provenance |
| Table | `cbam_activity_records` |
| API | `activity-records` |
| FE | CBAM activity records screens |
| Reusable | unit_conversion (snapshot factors per D-037) |
| Acceptance | no write to corporate `activity_records`; `rejected→draft` with history |
| Out of scope | Excel; calc |

## Phase 6 — Inventory receipts and process consumption

| Item | Content |
|------|---------|
| Goal | Receipt ≠ consumption; lots; reversals; available/consumed quantities |
| New | receipt/lot/consumption/reversal tables |
| Acceptance | conservation structural checks; over-consumption blocked; no provisional fill |
| Decisions | D-033 |
| Prerequisite for | phase 9 when consumption required |

## Phase 7 — Precursors and complex goods

| Item | Content |
|------|---------|
| Goal | Lots, declarations, acyclic graph |
| Tests | cycle detection |
| Decisions | D-009, D-023 |

## Phase 8 — Allocation rules and applications

| Item | Content |
|------|---------|
| Goal | Definitions + applications; unknown methods → `blocked`/`BLOCKED_DOMAIN` |
| Decisions | D-010, D-032 |
| Acceptance | no silent factor normalization |

## Phase 9 — Deterministic calculation engine and snapshots

| Item | Content |
|------|---------|
| Goal | Immutable runs/steps; product SEE without requiring shipments |
| Reusable | Decimal helpers, unit conversion only |
| Forbidden | carbon/LCA/PCF engines and ORM |
| Behavior | missing required consumption → `blocked`; status≠`BLOCKED_DOMAIN` |
| Idempotency | calculation request REQUIRED (D-040) |
| Decisions | D-007/008/014/036/037/039 content may still block |
| FE | calculation + trace (run→step→snapshot→source→evidence) |
| Out of scope | inventing formulas; activating unresolved D-030 lock as complete |

## Phase 10 — Shipments and shipment-level calculation

| Item | Content |
|------|---------|
| Goal | Shipments; shipment SEE boundary |
| Imports/exports | CSV first; **spreadsheet/CSV formula injection protection is a new CBAM requirement** (do not claim it already exists). Existing CSV header/UTF-8/row-limit patterns may be reused only where code evidence supports them. |
| Idempotency | staged-import confirmation REQUIRED |
| Decisions | D-016, D-021 |

## Phase 11 — Reports, approval, locking, revisions, verification package

| Item | Content |
|------|---------|
| Goal | Reports + package + full period workflow **when D-030 resolved** |
| Until D-030 | states may exist; final approve/lock transitions remain inactive |
| Idempotency | report generation REQUIRED; verification-package generation REQUIRED |
| Security | download authz; verifier read-only structure D-038; no public links by default |
| Decisions | D-017, D-018, D-027, D-030, D-031, D-038 |

## Phase 12 — Pilot and expert-approved golden calculations

| Item | Content |
|------|---------|
| Goal | One pilot sector E2E with expert-signed expected results |
| Prerequisites | pilot BLOCKED_DOMAIN items closed for that scope |
| Tests | golden SEE; injection tests for import/export; forbidden-import architecture test |
| Out of scope | all sectors; compliance certification claims |

---

## Phase dependency graph

```mermaid
flowchart TD
  P0[0 Spec] --> P1[1 Skeleton + idempotency]
  P1 --> P2[2 Foundation profiles]
  P2 --> P3[3 Reference structure]
  P2 --> P4[4 Process/Route installation-scoped]
  P4 --> P5[5 CbamActivityRecord]
  P5 --> P6[6 Inventory receipt/consumption]
  P5 --> P7[7 Precursors]
  P4 --> P8[8 Allocation]
  P3 --> P9[9 Engine + snapshots]
  P6 --> P9
  P7 --> P9
  P8 --> P9
  P9 --> P10[10 Shipments]
  P9 --> P11[11 Reports/Lock/Package]
  P10 --> P11
  P11 --> P12[12 Pilot + golden]
```
