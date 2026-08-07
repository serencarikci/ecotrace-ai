# ADR 0001 — Isolated CBAM Bounded Context

- **Status:** Accepted (specification)
- **Date:** 2026-08-07
- **Tags:** cbam, architecture

## Context

EcoTrace AI is a modular monolith with corporate carbon accounting, LCA/PCF, and shared operational master data. A repository audit found **no implemented CBAM/SKDM module**, but reusable infrastructure (identity, tenancy, facilities, Decimal patterns, snapshots, audit).

Product decision: implement CBAM inside the existing repository as an isolated bounded context (`modules/cbam`, UI `features/cbam`), using code name `cbam` and Turkish UI label SKDM.

## Decision

1. Add CBAM as a new bounded context in the modular monolith.
2. Own CBAM tables, workflows, APIs under `/api/v1/cbam`, and Angular feature module.
3. Integrate with existing modules via references and application ports, not by relabeling GHG/LCA results.
4. Do not create a separate repository for v1.

## Consequences

- **Positive:** Shared auth, tenancy, deployment, audit; faster delivery; clear module boundary.
- **Negative:** Discipline required to prevent leakage into LCA/carbon engines; larger monolith surface.
- **Neutral:** Introduces `docs/adr/` (no prior ADR folder existed).

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Separate CBAM repository | Higher integration cost for auth/org/master data; not justified by audit |
| Extend LCA/PCF modules to “support CBAM” | Methodology mismatch; disclaimer already excludes CBAM compliance |
| Delay until full refactor | Existing module boundaries are already adequate |
