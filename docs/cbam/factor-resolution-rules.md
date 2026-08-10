# Factor Resolution Rules (Phase 4B)

## Statuses

- `RESOLVED_PRIMARY`
- `RESOLVED_DEFAULT`
- `UNRESOLVED`
- `AMBIGUOUS`
- `INCOMPATIBLE_UNIT`
- `OUTSIDE_VALIDITY`
- `BLOCKED`

## Validity

When `valid_from` / `valid_until` are set, the source/as-of date must fall inside the range.

## Units

Exact match preferred. Same-dimension scale conversions only where catalogued (`MJ`↔`GJ`, `kg`↔`t`). No density invent.

## Sources

- ACTIVITY_RECORD
- PURCHASED_INPUT_RECORD
- ALLOCATION_RESULT

Resolution never multiplies quantity × factor.
