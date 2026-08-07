# ADR 0004 — Composition Instead of Polluting Generic Product/Facility Models

- **Status:** Accepted (specification)
- **Date:** 2026-08-07
- **Tags:** cbam, data-model

## Context

CBAM needs installation-specific attributes, CN codes, aggregated goods categories, and functional units. EcoTrace already has `facilities` and `products` used by operations, carbon, LCA, and DPP. Adding many CBAM columns to those tables would couple unrelated contexts and complicate non-CBAM tenants/features.

## Decision

1. Do **not** add CBAM-specific columns to `facilities` or `products` for convenience.
2. Own CBAM association/profile tables that reference existing UUIDs: installation profiles (cardinality per D-041) and **temporal** product-profile versions (CN/AGC effective dating per D-029).
3. Prefer CBAM-owned `CbamActivityRecord`, evidence, inventory receipt/consumption, calculation, and report tables over overloading corporate `activity_records` / carbon inventory tables.
4. Optional one-way import adapters may copy values into CBAM-owned records; they must not create live coupling.

## Consequences

- **Positive:** Clean bounded context; safer migrations; generic modules remain CBAM-agnostic.
- **Negative:** Extra joins; profile synchronization UX (user must link facility/product).
- **Neutral:** Matches ownership matrix in `docs/cbam/ownership.md`.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Add `cn_code` to `products` | Pollutes product model; unused by non-CBAM flows |
| Treat `Facility` as CBAM installation | Missing CBAM semantics; risks breaking ops assumptions |
| Reuse `LcaSystemBoundary` | Different methodology and lifecycle |
