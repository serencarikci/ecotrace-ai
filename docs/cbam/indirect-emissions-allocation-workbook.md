# Purchased-electricity indirect-emissions allocation (Phase 8C)

**Status:** Backend complete — Angular allocation UI out of scope  
**Methodology:** `PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1`  
**Workbook:** `local-reference/SKDM_Alokasyon_Sablon.xlsx`  
**SHA-256:** `62300e30193aa2e696d07977697833431dcf782684cf61cace4e7e5f524cef72`

## Workbook cells (electricity path)

| Role | Cells / formulas |
|------|------------------|
| Monthly electricity (kWh) | `B3:B5` |
| Total production D (t) | `D3:D5` |
| CBAM quantity E (t) | `E3:E5` |
| Electricity EF | `H4` (example `0.439`) |
| Stage 1 CBAM MWh | `C9=IF(D3=0,0,(E3/D3)*(B3/1000))` (and `C10`/`C11`) |
| Stage 1 monthly tCO2e | `E9=D9*C9` with `D9=$H$4` |
| Period CBAM electricity pool | `C12=SUM(C9:C11)`; export cell `B16=$C$12` |
| Period electricity tCO2e | `E12=C12*D12` |
| Product quantity | `B19:B21` (example `39.336` / `34.559` / `29.688`); denom `B26=SUM(B19:B25)` |
| Product electricity split | `D19=$B$16*(B19/$B$26)` (and `D20`/`D21`) |

**Not equivalent:** period-wide `sum(E)/sum(D)` × facility electricity.

**Product tCO2e:** the workbook has no separate product electricity-emissions column; EcoTrace allocates the immutable Phase 8A `indirect_emissions_tco2e` pool with the **same product share** as MWh (SEE-style reporting).

**Exported electricity:** not present in the SKDM product-allocation block. EcoTrace snapshots it separately from Phase 8A results, does **not** subtract it from purchased electricity, and does **not** distribute it to products.

## Two-stage methodology (confirmed)

### Stage 1 — monthly CBAM attribution

```text
monthly_cbam_electricity_MWh
  = PE.electricity_mwh × (monthly_E / monthly_D)

monthly_cbam_indirect_emissions_tCO2e
  = PE.indirect_emissions_tco2e × (monthly_E / monthly_D)
```

Facility totals = CBAM + non-CBAM for both MWh and tCO2e. Inputs are **immutable current Phase 8A snapshots** (never live factor recalculation).

### Stage 2 — product allocation

```text
product_share = product_quantity / period_product_denominator
product_electricity = period_cbam_electricity × product_share
product_indirect_emissions = period_cbam_indirect_emissions × product_share
```

Groups = immutable `product_profile_version_id`. Deterministic largest-remainder reconciliation at result quantum (`0.00000001`).

## Semantics

| Quantity | Unit | Notes |
|----------|------|--------|
| Electricity | MWh | Canonical; kWh sources snapshotted with original unit |
| Indirect emissions | tCO2e | Allocated from PE snapshot, not recomputed |
| Exported electricity | MWh | Separate; not in pools |

Balance:

- `sum(final product electricity) = final CBAM electricity pool`
- `sum(final product indirect emissions) = final CBAM indirect-emissions pool`
- Unbalanced results cannot become `COMPLETED` / current

## Persistence / current / stale / idempotency

- Immutable history + binding current pointer
- Successful recalculation replaces current; failed execution preserves current
- No automatic recalculation
- Stale when PE current/result material, activity qty/unit/date, factor snapshot, monthly D/E, production set/qty/unit/date, linked profile version, or methodology/workbook change
- Newer product-profile publication alone does **not** stale (production still links old immutable version)
- `clientRequestId` required: first success `201`, exact replay `200`, changed inputs `409`

## API (binding-scoped)

- `GET .../indirect-emissions-allocation/readiness` — `cbam:view`
- `POST .../indirect-emissions-allocation/executions` — `cbam:configure`
- `GET .../indirect-emissions-allocation/results` — `cbam:view`
- `GET .../indirect-emissions-allocation/results/{id}` — `cbam:view`
- `GET .../indirect-emissions-allocation/summary` — `cbam:view`

Client must not send source totals, shares, or allocated values.

## Out of scope

- Angular allocation UI
- Process / precursor allocation
- Excel export of allocated electricity
- Modification of Phase 8A PE calculation results
