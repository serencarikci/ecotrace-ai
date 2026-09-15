# CBAM Calculation Formulas (Phase 5)

## Supported

### `MULTIPLY_ACTIVITY_BY_FACTOR`

```
result = activity_quantity × factor_value
```

Enabled only when:

1. Calculation definition `calculation_type = MULTIPLY_ACTIVITY_BY_FACTOR`
2. Factor resolution is `RESOLVED_PRIMARY` or `RESOLVED_DEFAULT`
3. Factor unit is an explicit intensity unit (e.g. `kgCO2e/kWh`)
4. Source unit is dimensionally compatible with the factor denominator

`formula_version`: `multiply-activity-by-factor-v1`

## Not supported

- Arbitrary expression eval
- Sector-specific process equations
- Calorific × oxidation × carbon-content chains
- Implicit CO2 → CO2e / GWP application
- Inferred density conversions
