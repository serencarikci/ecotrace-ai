# CBAM Allocation Model (Phase 4A)

## Aggregates

### CbamAllocationRule

Mutable rule defining how a quantity share is derived for a scope:

- organization + reporting period binding + installation
- optional product profile version
- method + resolved `allocation_ratio`
- for production ratio: numerator/denominator production record IDs and snapshot quantities
- for manual ratio: rationale + source reference (required)
- status: `DRAFT` | `ACTIVE` | `ARCHIVED`
- optimistic concurrency via `row_version`

Only **one ACTIVE** rule per scope `(org, binding, installation, product_profile_version_id)` is allowed.

ACTIVE rules with retained results are not silently mutated; create a new DRAFT and activate after archiving the previous ACTIVE rule.

### CbamAllocationResult

Immutable (append/supersede) result of applying one ACTIVE rule to one source record:

- source type/id, source quantity/unit
- allocation ratio used
- allocated quantity/unit (same unit as source)
- `calculation_version` = `allocation-quantity-v1`
- `is_current` / `superseded_at` for explicit recalculation supersession

Source records are never overwritten.

## Scope dimensions (this phase)

Implemented:

- organization
- reporting period binding
- installation
- product profile version (optional)

Not implemented:

- customer / export
- shipment
- CN / AGC target dimensions
