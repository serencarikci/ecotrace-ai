# Purchased Inputs (Phase 3)

`CbamPurchasedInputRecord` captures purchased material/precursor quantities that may later participate in embedded-emission calculations.

## Distinctions

| Field | Meaning |
|-------|---------|
| `quantity` / `unit` | Purchased / received quantity |
| `consumed_quantity` / `consumed_unit` | Explicitly declared period consumption |

Phase 3 validates `0 <= consumed <= purchased` **only** when units match exactly. No unit conversion, FIFO/LIFO, or stock ledger (B-09 / B-10).

## Embedded emissions

If a supplier provides an embedded-emission value, store it as declared PRIMARY information:

- `embedded_emission_value`
- `embedded_emission_unit` (free-form declared unit text)
- `embedded_emission_source_type`

If not provided, leave value null (`NOT_PROVIDED`). Do not fetch or guess a default factor (B-11).
