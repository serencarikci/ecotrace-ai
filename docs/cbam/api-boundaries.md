# CBAM API Boundary Proposal

## Path convention (F-17)

Base prefix: `/api/v1/cbam`

Tenant resources:

`/api/v1/cbam/organizations/{organizationId}/...`

This is a **deliberate bounded-context-first exception** to the older organization-first layout used by non-CBAM modules. It does **not** change existing non-CBAM endpoint conventions.

Rules:

- `organizationId` from the URL is **never trusted** without membership and permission checks (`ensure_org_access` / CBAM helpers).
- Unauthorized / cross-tenant access follows the existing **404 non-disclosure** policy.
- See also [api-conventions.md](../api-conventions.md).

**Phase 1 implemented endpoint (foundation only):**

`GET /api/v1/cbam/organizations/{organizationId}/module-status`

Confirms module registration and authorization (`cbam:view`). Response fields include `enforcedPermissions` (currently only `cbam:view`). Explicitly reports that domain functionality, calculation, and reporting are **not** implemented and that **no compliance claim** is made. Future permission codes may exist as documentation vocabulary only; they are not implied by this endpoint. All other resource groups below remain proposal-only.

## Cross-cutting API rules

| Concern | Rule |
|---------|------|
| Pagination | `page`, `pageSize` on list endpoints |
| Optimistic concurrency | mutable updates require `rowVersion`; mismatch → 409 CONFLICT |
| Errors | standard EcoTrace envelope; detail codes include `BLOCKED_DOMAIN` when applicable |
| Authz | path org + CBAM permission helpers |
| No client-side SEE math | clients only trigger server runs |
| Locked CBAM binding | mutations → `BUSINESS_RULE_ERROR` / 409; independent of generic RP lock |
| Idempotency | **New CBAM capability** — no general platform Idempotency-Key store exists today (D-040) |

### Idempotency matrix (D-040)

| Operation | Requirement |
|-----------|-------------|
| Staged-import confirmation | REQUIRED |
| Calculation request | REQUIRED |
| Report generation | REQUIRED |
| Verification-package generation | REQUIRED |
| Retryable background operations | RECOMMENDED |
| Simple GETs | NOT_REQUIRED |
| Final approve/lock activation | BLOCKED_DECISION until D-030 |

Place idempotency foundation in roadmap phase 1 before the first REQUIRED operation ships.

---

## Resource groups

### Installations

`.../installations` — CBAM installation profiles linked to facilities.  
Ops: list/create/get/patch/activate/archive. Concurrency: `rowVersion`. Cardinality: D-041 (pilot).  
**Phase 2:** implemented.

### Reporting period bindings

`.../reporting-period-bindings` — CBAM workflow + **CBAM lock** (not generic RP lock).  
Transition commands only for **explicitly listed** transitions in workflows.md.  
`approve` / `lock` commands must remain inactive or fail closed until **D-030** is resolved.  
Period approval payload must be able to carry `calculationRunId` when activated.  
**Phase 2:** list/create/get/patch/`open-data-collection`/archive (draft cleanup); further transitions blocked.

### Reference-data versions

`/api/v1/cbam/reference-data/versions` (global) + org pin under organization path.

### Product profiles (temporal)

`.../product-profile-versions` — Phase 2 foundation (product ref + version/lifecycle/temporal; **no CN/AGC/FU**; `classificationReady` always false).  
Future CN-bearing shape may use `.../product-profiles` nesting (D-029); not implemented yet.

### Production processes / routes (installation-scoped)

`.../installations/{installationId}/processes`  
`.../installations/{installationId}/routes`  

Reporting-period resources may **read** selected/snapshotted configuration; they must **not** host process/route master CRUD.

### Production / activity / purchased inputs (Phase 3)

Under `.../reporting-period-bindings/{bindingId}/`:

- `production-records`
- `activity-records`
- `purchased-inputs`

Plus detail/archive under `.../production-records/{id}`, `.../activity-records/{id}`, `.../purchased-inputs/{id}`.  
Catalogs: `.../activity-types`, `.../units`, `.../activity-property-types`.  
**Phase 3:** create/list/get/patch/archive only — **no** emission calculation, submit/accept workflow, or Excel.

Future activity workflow ops (submit/accept/reject and **`rejected → draft`**) remain later-phase.

### Allocation (Phase 4A)

Under `.../reporting-period-bindings/{bindingId}/`:

- `allocation-rules` (GET/POST)
- `allocation-results` (GET)

Under org root:

- `allocation-rules/{ruleId}` (GET/PATCH)
- `allocation-rules/{ruleId}/activate`
- `allocation-rules/{ruleId}/archive`
- `allocation-rules/{ruleId}/allocate/activity-records/{activityRecordId}`
- `allocation-rules/{ruleId}/allocate/purchased-inputs/{inputRecordId}`
- `allocation-results/{resultId}` (GET)
- `allocation-results/{resultId}/recalculate`

Permissions: `cbam:view` for GET; `cbam:configure` for mutations/allocate/recalculate.  
**Phase 4A:** quantity allocation only — **no** emission factors, CO2e, Excel, or report generation.

### Factor resolution (Phase 4B)

Under org root:

- `reference-sources` (GET/POST) · `reference-sources/{sourceId}` (GET/PATCH) · `.../archive`
- `factor-definitions` (GET) · `factor-definitions/{id}` (GET)
- `factor-definitions/{id}/values` (GET/POST)
- `factor-values/{id}` (GET/PATCH) · `.../activate` · `.../archive`
- `activity-records/{id}/properties` (POST — primary property reuse)
- `activity-records/{id}/factor-resolutions/{factorDefinitionCode}/resolve` (POST)
- `purchased-inputs/{id}/factor-resolutions/{factorDefinitionCode}/resolve` (POST)
- `allocation-results/{id}/factor-resolutions/{factorDefinitionCode}/resolve` (POST)
- `factor-resolutions/{id}` (GET)
- `reporting-period-bindings/{bindingId}/factor-resolutions` (GET)

Permissions: `cbam:view` for GET; `cbam:configure` for org-level factor values and resolve/re-resolve.  
**Phase 4B:** selection metadata only — **no** automatic IPCC/DEFRA/EPA import, Excel, or report generation. Seeded reference sources are **names/metadata only**.

### Calculation (Phase 5)

Under org root:

- `calculation-definitions` (GET)
- `reporting-period-bindings/{bindingId}/calculation-runs` (GET/POST)
- `calculation-runs/{runId}` (GET)
- `calculation-runs/{runId}/execute` (POST)
- `calculation-runs/{runId}/results` (GET)
- `calculation-results/{resultId}` (GET)
- `calculation-results/{resultId}/recalculate` (POST)

Permissions: `cbam:view` for GET; `cbam:configure` for create/execute/recalculate.  
**Phase 5:** minimal `MULTIPLY_ACTIVITY_BY_FACTOR` only — **no** official regulatory totals, CN, shipment, certificate/financial liability, or guessed sector formulas.

### Export / reporting (Phase 6)

Under org root:

- `export-templates` (GET)
- `export-templates/{templateId}` (GET)
- `reporting-period-bindings/{bindingId}/export-readiness` (GET)
- `reporting-period-bindings/{bindingId}/summary` (GET)
- `reporting-period-bindings/{bindingId}/exports` (GET/POST)
- `exports/{exportRunId}` (GET)
- `exports/{exportRunId}/artifacts` (GET)
- `export-artifacts/{artifactId}/download` (GET)

Permissions: `cbam:view` for readiness/summary/history/download; `cbam:configure` for create export.  
**Phase 6:** internal SKDM workbook + summary only. Official CBAM workbook mapping remains **BLOCKED**. Export does not recalculate Phase 5 results.

### Inventory

`.../inventory-receipts`  
`.../inventory-lots`  
`.../process-consumptions`  
`.../inventory-reversals`  

### Precursors / complex-goods graphs

`.../precursors` · `.../complex-goods-graphs`

### Shipments

`.../shipments` — required for shipment-level SEE; not required for core product SEE.

### Evidence

`.../evidence` or nested under entity — CBAM-owned metadata; storage per D-042.

### Validation

`.../reporting-period-bindings/{id}/validate` → findings.

### Calculation runs

`.../reporting-period-bindings/{id}/calculation-runs`  

Ops: POST run (idempotent REQUIRED), list, get, steps, compare, approve (gated by D-030).  

Responses for `blocked` runs include: `status: blocked`, `blockingCode` (e.g. `BLOCKED_DOMAIN`), `blockingDecisionIds`, `affected`, `message`, `blockedAt`.

Cancel endpoint: **not activated** until D-039; must not map cancel to `failed`.

### Findings / approvals / reports / verification packages

As before; report/package POST idempotency REQUIRED; approve/lock activation gated by D-030.
