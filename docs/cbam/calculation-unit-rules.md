# CBAM Calculation Unit Rules (Phase 5)

## Intensity units

Factor units must be explicit intensity forms:

`{result_unit}/{per_unit}`

Examples (allow-listed):

- `kgCO2e/kWh`, `tCO2e/MWh`, `kgCO2e/L`, `tCO2e/t`

CO2 and CO2e remain distinct labels. No silent conversion.

## Compatibility

Source unit must match the factor denominator exactly or via documented same-dimension scale pairs:

- `kWh` ↔ `MWh`
- `kg` ↔ `t`
- `MJ` ↔ `GJ`

Rejected without invent:

- `L` × `kgCO2e/kWh`
- density assumptions
- calorific assumptions

## Aggregation

Same-unit technical sum of `CALCULATED` results is optional and labeled **Toplam Hesaplanan Değer** — never “Final CBAM Emissions”.
