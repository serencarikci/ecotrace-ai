# ADR 0002 — Separate CBAM Calculation Engine

- **Status:** Accepted (specification)
- **Date:** 2026-08-07
- **Tags:** cbam, calculation

## Context

Existing engines:

- `carbon_accounting` / `carbon_inventory` — corporate Scope 1/2/3 activity × factor
- `lifecycle_assessment` / `product_carbon_footprint` — ISO-inspired LCA/PCF with explicit non-CBAM disclaimer

CBAM requires embedded emissions, precursors, process allocation, actual/default provenance, and shipment-level results under CBAM rule packs. Reusing LCA/carbon entrypoints would create false compliance signals.

## Decision

1. Implement a **dedicated** CBAM calculation engine under `modules/cbam`.
2. Forbid importing carbon inventory / LCA / PCF calculation entrypoints for producing CBAM SEE results.
3. Allow only pure shared utilities (Decimal helpers, unit conversion, auth/audit).
4. Unknown or unspecified regulatory formulas mark runs with status `blocked` and detail code `BLOCKED_DOMAIN` rather than guessing.

## Consequences

- **Positive:** Clear compliance boundary; independent versioning of rule packs; safer evolution of GHG vs CBAM.
- **Negative:** Some duplicated orchestration patterns (validate → snapshot → compute → persist).
- **Neutral:** Factor registry may be read via port and **snapshotted**, never live-joined into approved results.

## Anti-corruption enforcement (specification)

Inside `modules/cbam`, importing ORM models or calculation engines from `carbon_accounting`, `carbon_inventory`, `lifecycle_assessment`, or `product_carbon_footprint` is forbidden, as is writing to those modules’ tables. Cross-module access must use approved ports/contracts; calculation inputs must be copied into CBAM snapshots. A future architecture/CI test should detect forbidden imports (not implemented in the documentation-only phase).

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Call `compute_emission_result` as CBAM core | Wrong methodology framing; easy to mislabel Scope/PCF as SEE |
| Single “universal” engine | Premature; high coupling; audit showed divergent needs |
