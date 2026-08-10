# CBAM Calculation Model (Phase 5)

## Entities

| Entity | Purpose |
|--------|---------|
| `CbamCalculationDefinition` | Explicit formula metadata (`MULTIPLY_ACTIVITY_BY_FACTOR`) |
| `CbamCalculationRun` | One execution for a reporting-period binding |
| `CbamCalculationResult` | Persisted inputs + outcome for one source/resolution |

## Run statuses

`DRAFT` → `RUNNING` → `COMPLETED` | `PARTIALLY_COMPLETED` | `FAILED` | `ARCHIVED`

## Result statuses

- `CALCULATED`
- `BLOCKED` / `UNRESOLVED_FACTOR` / `AMBIGUOUS_FACTOR`
- `INVALID_INPUT` / `INCOMPATIBLE_UNIT` / `UNSUPPORTED_FORMULA`

## Traceability

Each result stores source quantity/unit, factor value/unit, result value/unit, factor resolution id, optional allocation result id, and `input_fingerprint`. Recalculation supersedes prior current rows.
