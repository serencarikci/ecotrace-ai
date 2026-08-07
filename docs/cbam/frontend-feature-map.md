# CBAM Frontend Feature Map

Proposed location: `apps/web/src/app/features/cbam/`

Follow existing Angular 19 standalone + lazy routes + role guards patterns (`app.routes.ts`, `roles.util.ts`).

**UI language note:** Navigation and page titles may show **SKDM**; code, routes, and API clients use `cbam`.

**Not implemented** — map only.

## Canonical naming

| Concept | UI / code label |
|---------|-----------------|
| Activity entity | **CBAM activity records** (API `activity-records`, domain `CbamActivityRecord`) |
| Do not use as entity name | `CbamActivityData`, `CbamActivity` |

## Route structure (proposed)

Under authenticated shell `app/`:

```
app/cbam
  app/cbam/installations
  app/cbam/installations/new
  app/cbam/installations/:installationId
  app/cbam/installations/:installationId/setup
  app/cbam/installations/:installationId/processes
  app/cbam/installations/:installationId/processes/:processId
  app/cbam/installations/:installationId/routes
  app/cbam/installations/:installationId/routes/:routeId
  app/cbam/product-profiles
  app/cbam/product-profiles/:profileId/versions
  app/cbam/periods
  app/cbam/periods/:bindingId
  app/cbam/periods/:bindingId/dashboard
  app/cbam/periods/:bindingId/configuration   # read-only selected/snapshotted process/route refs
  app/cbam/periods/:bindingId/activity-records
  app/cbam/periods/:bindingId/inventory
  app/cbam/periods/:bindingId/precursors
  app/cbam/periods/:bindingId/allocation
  app/cbam/periods/:bindingId/shipments
  app/cbam/periods/:bindingId/evidence
  app/cbam/periods/:bindingId/validation
  app/cbam/periods/:bindingId/calculations
  app/cbam/periods/:bindingId/calculations/:runId
  app/cbam/periods/:bindingId/calculations/:runId/trace
  app/cbam/periods/:bindingId/approvals
  app/cbam/periods/:bindingId/reports
  app/cbam/periods/:bindingId/verification-package
  app/cbam/reference
```

### Ownership alignment (F-05)

- Process and route **setup** is **installation-scoped**.
- Reporting-period screens may **display** selected or snapshotted configuration; they must **not** redefine process/route master ownership.

Public routes: none for CBAM.

## User roles (baseline)

Reuse existing roles; add `canReadCbam`, `canWriteCbam`, `canReviewCbam`, `canApproveCbam`, `canLockCbam` in a future `cbam-roles.util.ts` (final mapping D-019).

| UI area | viewer | analyst | sustainability_manager | organization_admin | system_admin |
|---------|--------|---------|------------------------|--------------------|--------------|
| Dashboards / traces | R | R | R | R | R |
| Data entry | — | RW | RW | RW | RW |
| Expert review | — | — | RW | RW | RW |
| Approve / lock | — | — | A/L* | A/L* | A/L* |
| Unlock / revise | — | — | — | Y | Y |
| Reference publish | — | — | — | — | Y |
| Verifier read-only | structural support D-038 | | | | |

\* Final approve/lock activation gated by **D-030** — UI must not present these as production-complete until resolved.

## Navigation

Shell nav group **SKDM** (feature-flagged): Tesisler (installations), Ürün profilleri, Dönemler, Referans (admin). Not under Carbon Inventories or LCA menus.

## Screen map

| Screen | Purpose |
|--------|---------|
| Installation setup wizard | Select facility → CBAM profile (D-041 pilot cardinality) |
| Process & route setup | **Installation-scoped** masters, boundaries, flows |
| Product profile versions | Temporal CN/AGC/FU versions (D-029) |
| Reporting-period dashboard | Binding status, completeness, findings, latest run, CBAM lock state |
| Period configuration (read-only) | Show snapshotted/selected process/route refs |
| CBAM activity records | Typed entry; rejection reopen with history |
| Inventory | Receipts, lots, consumptions, reversals |
| Precursor collection | Lots, declarations, graph |
| Allocation configuration | Applications; show `BLOCKED_DOMAIN` detail codes clearly |
| Shipment management | Optional for product SEE; required for shipment SEE |
| Evidence management | Per D-042 storage choice |
| Validation & findings | |
| Calculation trace | status `blocked` + detail code; navigate run→step→snapshot→source→evidence |
| Approval & locking | Disabled/incomplete until D-030; revision reason modal |
| Reports / verification package | |

## UX constraints

- Provenance badges (`actual` / `default` / `alternative_default`)
- Disable edits when CBAM binding `locked` (independent of generic RP lock)
- Never present corporate inventory or LCA/PCF totals as SKDM results
- Empty catalogs: regulatory content awaits expert configuration
- Do not label run status as `BLOCKED_DOMAIN`; show status `blocked` with detail code
