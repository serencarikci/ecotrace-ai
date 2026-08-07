# CBAM / SKDM — Bounded Context (Specification)

**Status:** Specification only — not implemented  
**Code namespace:** `cbam`  
**UI label (TR):** SKDM  
**Proposed backend:** `apps/api/src/ecotrace/modules/cbam/`  
**Proposed frontend:** `apps/web/src/app/features/cbam/`

EcoTrace AI does **not** currently contain a CBAM/SKDM module. This document set defines an isolated bounded context to be added inside the existing modular monolith without relabeling corporate carbon accounting, LCA, or PCF as CBAM.

## Non-goals (current phase)

- No application code, migrations, seeds, APIs, or UI routes
- No invented CN codes, production routes, emission factors, or regulatory formulas
- No reuse of LCA/PCF/Scope engines as CBAM calculation results

## Document index

| Document | Purpose |
|----------|---------|
| [cbam/ownership.md](cbam/ownership.md) | Context ownership matrix |
| [cbam/domain-model.md](cbam/domain-model.md) | Domain aggregates and entities |
| [cbam/context-boundaries.md](cbam/context-boundaries.md) | Integration with existing modules |
| [cbam/calculation-architecture.md](cbam/calculation-architecture.md) | Separate calculation engine boundaries |
| [cbam/workflows.md](cbam/workflows.md) | Lifecycles, permissions, SoD |
| [cbam/api-boundaries.md](cbam/api-boundaries.md) | `/api/v1/cbam` resource proposal |
| [cbam/frontend-feature-map.md](cbam/frontend-feature-map.md) | Angular feature map |
| [cbam/implementation-roadmap.md](cbam/implementation-roadmap.md) | Dependency-ordered phases |
| [cbam/domain-decisions.md](cbam/domain-decisions.md) | Expert decision register |
| [adr/0001-isolated-cbam-bounded-context.md](adr/0001-isolated-cbam-bounded-context.md) | ADR: isolated context |
| [adr/0002-separate-cbam-calculation-engine.md](adr/0002-separate-cbam-calculation-engine.md) | ADR: separate engine |
| [adr/0003-cbam-snapshot-based-reproducibility.md](adr/0003-cbam-snapshot-based-reproducibility.md) | ADR: snapshots |
| [adr/0004-cbam-composition-over-polluting-generic-models.md](adr/0004-cbam-composition-over-polluting-generic-models.md) | ADR: composition |

## Architectural stance

```mermaid
flowchart TB
  subgraph existing [Existing EcoTrace contexts]
    ID[identity / organizations]
    FAC[facilities / operational_assets]
    ACT[activity_data / reporting_periods]
    EF[emission_factors]
    CA[carbon_accounting / carbon_inventory]
    LCA[lifecycle_assessment / PCF]
    PR[products / materials / suppliers]
  end
  subgraph cbam [CBAM bounded context]
    MOD[modules/cbam]
    ENG[cbam calculation engine]
    SNAP[immutable calculation snapshots]
  end
  ID -->|reference IDs| MOD
  FAC -->|facility_id reference| MOD
  PR -->|product/material/supplier IDs| MOD
  ACT -.->|optional import adapter only| MOD
  EF -.->|optional factor read via port + snapshot| ENG
  CA -.->|NO shared results| ENG
  LCA -.->|NO shared results| ENG
  MOD --> ENG --> SNAP
```

## Naming

| Layer | Convention |
|-------|------------|
| Source / DB / API | `cbam` |
| Turkish UI copy | SKDM where user-facing |
| Tables (proposed) | `cbam_*` |
| Routes (proposed) | `/api/v1/cbam/organizations/{organizationId}/...` (bounded-context-first exception; see api-conventions) |
| Canonical activity entity | `CbamActivityRecord` / `cbam_activity_records` / API `activity-records` |

## Key architectural rules (post-review)

- CBAM lock owned by `CbamReportingPeriodBinding` (generic ReportingPeriod lock is not source of truth).
- Processes/routes are **installation-scoped**; periods reference/snapshot only.
- Product classifications are **temporal versions** (not a permanent unique `(org, product)` only).
- Calculation status `blocked` + detail code `BLOCKED_DOMAIN` (never a lifecycle state named BLOCKED_DOMAIN).
- Inventory receipt ≠ process consumption; engine blocks when required consumption is missing.
- No reuse of carbon/LCA/PCF engines or their ORM models inside `modules/cbam`.
- No claim of an existing shared attachment port or existing spreadsheet-formula sanitization.

## Convention conflicts noted

See [cbam/context-boundaries.md](cbam/context-boundaries.md#convention-conflicts) and [api-conventions.md](api-conventions.md).

## Related existing docs

- [architecture.md](architecture.md)
- [carbon-accounting.md](carbon-accounting.md) — corporate GHG; **not** CBAM
- [lca-pcf-dpp.md](lca-pcf-dpp.md) — product LCA/PCF; **not** CBAM
- [api-conventions.md](api-conventions.md)
