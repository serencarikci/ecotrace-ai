# CBAM Calculation Model (Phase 5)

## Entities

| Entity | Purpose |
|--------|---------|
| `CbamCalculationDefinition` | Explicit formula metadata (`MULTIPLY_ACTIVITY_BY_FACTOR`, `STATIONARY_COMBUSTION_CO2_V1`, `PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_V1`) |
| `CbamCalculationRun` | One execution for a reporting-period binding (shared lifecycle) |
| `CbamCalculationResult` | Persisted inputs + outcome for one source/resolution (factor-based multiply only) |
| `CbamStationaryCombustionResult` | Typed immutable stationary-combustion snapshot (no `factor_resolution_id`) |
| `CbamStationaryCombustionCurrentResult` | Authoritative current-result pointer per activity (Phase 5A) |
| `CbamPurchasedElectricityResult` | Typed immutable purchased-electricity indirect snapshot (Phase 8A) |
| `CbamPurchasedElectricityCurrentResult` | Current-result pointer per activity (Phase 8A) |

## Run statuses

`DRAFT` → `RUNNING` → `COMPLETED` | `PARTIALLY_COMPLETED` | `FAILED` | `ARCHIVED`

## Result statuses

- `CALCULATED`
- `BLOCKED` / `UNRESOLVED_FACTOR` / `AMBIGUOUS_FACTOR`
- `INVALID_INPUT` / `INCOMPATIBLE_UNIT` / `UNSUPPORTED_FORMULA`

## Traceability

Each result stores source quantity/unit, factor value/unit, result value/unit, factor resolution id, optional allocation result id, and `input_fingerprint`. Recalculation supersedes prior current rows.

## Direct-emissions allocation (Phase 7A-2)

Dedicated tables (not generic `PRODUCTION_QUANTITY_RATIO`):

| Entity | Purpose |
|--------|---------|
| `CbamDirectEmissionsAllocationResult` | Completed immutable run totals + methodology/workbook provenance + fingerprint |
| `CbamDeaMonthlyBasisSnapshot` | Frozen monthly D/E + share |
| `CbamDeaSourceSnapshot` | Frozen SC source measures + monthly CBAM/non-CBAM attribution |
| `CbamDeaProductAllocation` | Frozen product-profile group share + raw/final CO2 |
| `CbamDirectEmissionsAllocationCurrent` | Current pointer per org/binding/methodology |

Stage 1 attributes each current SC source by that month’s `E/D`. Stage 2 splits the CBAM pool by eligible product-profile quantities with 8-decimal largest-remainder conservation. Stored unit: `tCO2` (workbook reporting metadata: `tCO2e`, GWP=1).

## Purchased electricity indirect emissions (Phase 8A)

Facility-level only (no product allocation):

```text
indirect_emissions_tCO2e = electricity_MWh × factor_tCO2e_per_MWh
```

- Factor modes: `PLATFORM_DEFAULT` (fail-closed via `ELECTRICITY_GRID_EMISSION_FACTOR`) or `MANUAL` (mandatory provenance).
- Exported electricity is persisted separately and **not** subtracted from purchased consumption.
- Result unit: `tCO2e`. Details: [purchased-electricity-indirect-emissions.md](purchased-electricity-indirect-emissions.md).
