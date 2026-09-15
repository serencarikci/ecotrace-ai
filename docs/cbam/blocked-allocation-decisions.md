# BLOCKED — Allocation Decisions

Phase 4A implements a **generic quantity-allocation foundation** only
(`DIRECT_ASSIGNMENT`, `PRODUCTION_QUANTITY_RATIO`, `MANUAL_RATIO`).

It does **not** resolve regulatory-specific allocation alternatives.

## Implemented (moved out of BLOCKED)

| ID | Topic | Resolution in Phase 4A |
|----|-------|------------------------|
| B-07 (partial) | Basic allocation methods + basis | Explicit methods above; production-quantity ratio uses selected production records |
| B-08 (partial) | Multi-product shared resources | Explicit rules per installation/product scope; no automatic full assignment |

Stored fields now include `allocation_ratio` and `allocated_quantity` for **quantities only**.

## Still BLOCKED / unresolved

| ID | Topic |
|----|-------|
| B-07b | Regulatory-specific allocation alternatives beyond generic methods |
| B-08b | Multi-stage production allocation |
| B-09 | Purchased-vs-consumed inventory treatment beyond explicit capture |
| B-10 | Opening and closing stock treatment |
| B-11 | Customer / export allocation |
| B-12 | Shipment-scope allocation |
| B-13 | Inventory valuation method (FIFO / LIFO / weighted average) |
| B-14 | Sector-specific allocation formulas |
| B-15 | Energy-content / economic / revenue allocation |

## Explicit non-goals (do not invent)

- Allocated emissions / CO2e from allocation
- Using export/customer share ratios (e.g. 30/500) as silent formulas
- Shared-resource automatic split without an explicit rule
- Inventory valuation methods (FIFO/LIFO/weighted average)

## Required inputs preserved for later phases

- Total production records
- Activity consumption records
- Purchased vs consumed quantities when explicitly entered
- Reporting period binding / installation / product profile version
- Allocation rules and quantity results from Phase 4A
