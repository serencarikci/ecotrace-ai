# ADR 0003 — Snapshot-Based Reproducibility for CBAM

- **Status:** Accepted (specification)
- **Date:** 2026-08-07
- **Tags:** cbam, calculation, audit

## Context

EcoTrace carbon and LCA modules already persist calculation item snapshots (factor versions, GWP, formulas). CBAM results must remain stable after approval/lock even if facilities, products, emission factors, or catalogs later change.

## Decision

1. Every CBAM calculation run builds immutable snapshots of inputs, reference data, factors, rule pack versions, allocation applications, **unit conversion factors** (source/normalized unit, factor value, factor version/stable definition, direction, precision policy), and **precision context** before emitting results.
2. Approved/locked runs and their steps are immutable; recalculation creates a new run and supersedes prior runs per workflow policy (supersede/cancel timing: decision register D-039).
3. Direct foreign keys to mutable master data are allowed for navigation, but **approved results must not depend on live joins** for numeric outcomes.
4. No silent fallback when snapshot ingredients are missing — run status `blocked` with detail code such as `BLOCKED_DOMAIN` (never use `BLOCKED_DOMAIN` as a lifecycle state).
5. Snapshots preserve raw normalized Decimal strings; final presentation rounding remains expert-blocked (D-036 / D-014).
6. Traceability: run → step → input snapshot entry → source CBAM activity/precursor/consumption → evidence link → checksum/version.

## Consequences

- **Positive:** Reproducible audits; safe master-data evolution; verifier-friendly traces.
- **Negative:** Storage growth; explicit supersede UX required.
- **Neutral:** Aligns with existing EcoTrace snapshot culture without sharing carbon/LCA tables.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Live-join factors/products at read time | Approved totals would drift |
| Only store final totals | Insufficient for verification packages |
