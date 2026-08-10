# CBAM Allocation Methods (Phase 4A)

Only these methods are supported:

## DIRECT_ASSIGNMENT

- Meaning: the source belongs fully to the selected allocation target.
- Ratio: always `1.0`.
- Must be an explicit user choice; never inferred automatically.

## PRODUCTION_QUANTITY_RATIO

```
allocation_ratio = target_production_quantity / allocation_base_production_quantity
```

Rules:

- numerator and denominator must use the **exact same unit** (no silent conversion)
- denominator > 0
- 0 ≤ numerator ≤ denominator
- both production records in the same organization, binding, and installation
- stored snapshot: numerator/denominator quantities + unit + ratio

Do not derive numerator from shipment/export values (not implemented).

## MANUAL_RATIO

- User-entered ratio in `[0, 1]`
- Requires non-empty `rationale` and `source_reference`
- Must not be described as regulatory-approved

## Explicitly not implemented

Revenue / economic / energy-content allocation, mass-balance inventory methods, FIFO/LIFO/weighted average, customer/export/shipment allocation, sector-specific formulas.
