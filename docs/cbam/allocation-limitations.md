# CBAM Allocation Limitations (Phase 4A)

## What Phase 4A does

- Persist explicit allocation rules
- Compute and persist allocated **quantities**
- Recalculate with supersession (`is_current` / `superseded_at`)

## What Phase 4A does **not** do

- Multiply allocated quantities by emission factors
- Resolve IPCC / DEFRA / EPA / APCC factors
- Calculate CO2 / CO2e / embedded emissions
- Generate Excel or CBAM reports
- Implement CN / AGC classification
- Implement shipment or customer/export allocation
- Convert fuel quantity to energy unless an exact existing conversion already exists (none used here)
- Infer missing purchased `consumed_quantity` from purchased quantity
- Silent mutation of historical allocation result rows

## Purchased inputs

When allocating purchased inputs:

- use `consumed_quantity` when present
- if absent → fail closed (`CONSUMED_QUANTITY_REQUIRED`)

## Technical example (not a regulatory claim)

- Total production 500 t
- Target production 100 t
- Electricity 100 MWh

→ ratio `0.2`, allocated electricity `20 MWh`

This is a **technical quantity-allocation example only**, not a complete CBAM regulatory calculation.
