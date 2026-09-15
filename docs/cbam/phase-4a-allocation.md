# CBAM Phase 4A — Allocation Foundation

**Status:** Implemented (quantity allocation only)

Phase 4A answers only:

> How much of this production/activity/input quantity belongs to this allocation scope?

It does **not** multiply by emission factors, compute CO2e, generate Excel/CBAM reports, or implement CN/shipment logic.

## Delivered

| Item | Detail |
|------|--------|
| Migration | `0010_cbam_allocation_foundation` |
| Tables | `cbam_allocation_rules`, `cbam_allocation_results` |
| Methods | `DIRECT_ASSIGNMENT`, `PRODUCTION_QUANTITY_RATIO`, `MANUAL_RATIO` |
| Sources | `ACTIVITY_RECORD`, `PURCHASED_INPUT_RECORD` |
| Formula | `allocated_quantity = source_quantity * allocation_ratio` (Decimal) |
| UI | SKDM dönem detayı → **Alokasyon** tab |

## Related docs

- [allocation-model.md](allocation-model.md)
- [allocation-methods.md](allocation-methods.md)
- [allocation-limitations.md](allocation-limitations.md)
- [blocked-allocation-decisions.md](blocked-allocation-decisions.md)
- [phase-4a-implementation-report.md](phase-4a-implementation-report.md)
