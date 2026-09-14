# CBAM Factor Model (Phase 4B)

## Concepts (kept separate)

1. **Activity data** — e.g. 500 L diesel  
2. **Activity property** — e.g. measured NCV on `CbamActivityProperty` (reused)  
3. **Emission factor** — future conversion factor (metadata + explicit values only)  
4. **Primary value** — customer/supplier measured or documented  
5. **Default reference** — configured reference when primary unavailable  
6. **Resolution** — deterministic selection of a candidate

## Tables

- `cbam_reference_sources` — origin metadata (IPCC/DEFRA/EPA codes seeded without numerics)
- `cbam_factor_definitions` — semantic types (`NET_CALORIFIC_VALUE`, `GENERIC_EMISSION_FACTOR`, `SUPPLIER_EMBEDDED_EMISSION`, `ELECTRICITY_GRID_EMISSION_FACTOR`)
- `cbam_factor_values` — explicit DRAFT/ACTIVE/ARCHIVED numeric candidates
- `cbam_factor_resolutions` — historical selection records (`is_current` / `superseded_at`)

Stationary-combustion fuel NCV / fossil CO2 / oxidation / optional density catalogs are **not** stored as factor values. See [stationary-combustion-fuel-catalog.md](stationary-combustion-fuel-catalog.md).

**Phase 8A electricity:** reuses `ELECTRICITY_GRID_EMISSION_FACTOR` as the platform-default extension point. No numeric Turkey/default value is seeded until authoritative provenance exists. Manual execution path requires provenance on the request (not a duplicate factor subsystem). See [purchased-electricity-indirect-emissions.md](purchased-electricity-indirect-emissions.md).
