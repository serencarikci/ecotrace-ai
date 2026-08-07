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

**Not implemented** — proposal only.

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
Ops: list/create/get/patch/archive. Concurrency: `rowVersion`. Cardinality: D-041.

### Reporting period bindings

`.../reporting-period-bindings` — CBAM workflow + **CBAM lock** (not generic RP lock).  
Transition commands only for **explicitly listed** transitions in workflows.md.  
`approve` / `lock` commands must remain inactive or fail closed until **D-030** is resolved.  
Period approval payload must be able to carry `calculationRunId` when activated.

### Reference-data versions

`/api/v1/cbam/reference-data/versions` (global) + org pin under organization path.

### Product profiles (temporal)

`.../product-profiles` and `.../product-profiles/{id}/versions` — versioned CN/AGC/FU classifications (D-029).

### Production processes / routes (installation-scoped)

`.../installations/{installationId}/processes`  
`.../installations/{installationId}/routes`  

Reporting-period resources may **read** selected/snapshotted configuration; they must **not** host process/route master CRUD.

### Activity records

`.../activity-records` — entity **`CbamActivityRecord`**.  
Ops include submit/accept/reject and **`rejected → draft`** (correction reason, history preserved).

### Inventory

`.../inventory-receipts`  
`.../inventory-lots`  
`.../process-consumptions`  
`.../inventory-reversals`  

### Precursors / complex-goods graphs

`.../precursors` · `.../complex-goods-graphs`

### Allocation

`.../allocation-rule-applications`  
`/api/v1/cbam/allocation-rule-definitions`

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
