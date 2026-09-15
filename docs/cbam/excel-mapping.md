# Excel Mapping

## Entity: `CbamExportMapping`

One application field → one workbook destination.

| Field | Notes |
|-------|--------|
| source_type | ORGANIZATION, INSTALLATION, REPORTING_PERIOD, PRODUCT, PRODUCTION_RECORD, ACTIVITY_RECORD, PURCHASED_INPUT, ALLOCATION_RESULT, FACTOR_RESOLUTION, CALCULATION_RESULT, CALCULATED_SUMMARY, CONSTANT |
| source_path | Allow-listed path only (e.g. `organization.name`, `calculation.rows`) |
| destination_type | CELL, NAMED_RANGE, TABLE_COLUMN, REPEATING_ROW |
| destination_reference | A1, named range, or `startRow\|col1,col2,...` for repeating rows |
| transformation_code | NONE, DECIMAL_TO_NUMBER, DATE_TO_EXCEL_DATE, DATETIME_TO_EXCEL_DATETIME, ENUM_TO_DISPLAY_LABEL, UNIT_DISPLAY, BOOLEAN_TO_YES_NO |

## Constraints

- No `eval`, no arbitrary Python expressions.
- Source resolver is an explicit allow-list (no unrestricted ORM traversal).
- Transformations are display/coercion only — **not** emission formulas.
- Completed exports preserve mapping checksum/version; mappings used by history are not mutated in place.

## Formula cells

Mapped writes refuse to overwrite cells whose value starts with `=`. Export fails if formula count/content changes unexpectedly.
