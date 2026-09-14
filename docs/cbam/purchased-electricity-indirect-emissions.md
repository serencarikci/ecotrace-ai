# Purchased electricity indirect emissions (Phase 8A)

**Status:** `PHASE_8A_BACKEND_FOUNDATION`  
**Date:** 2026-08-29  
**Frontend / product allocation:** out of scope

## Workbook cells and formulas

### SKDM allocation template (`SKDM_Alokasyon_Sablon.xlsx`)

| Cell | Role |
|------|------|
| `B2` / `B3:B5` | Electricity input **kWh** (monthly) |
| `H4` | Electricity EF **0.439** labeled `tCO2/MWh` — **no source/provenance in file** |
| `C9` | `=IF(D3=0,0,(E3/D3)*(B3/1000))` CBAM-attributed MWh (E/D) — **allocation, not Phase 8A calc** |
| `D9` | `=$H$4` |
| `E9` | `=D9*C9` → attributed MWh × EF → electricity tCO2e |
| `E12` | `=C12*D12` period attributed electricity emissions |
| `B16` | `=$C$12` total attributed electricity MWh (SEE export input) |
| `D19…` | Product electricity split — **out of Phase 8A** |

Facility-level (no E/D) path used by Phase 8A:

```text
indirect_emissions_tCO2e = electricity_MWh × factor_(tCO2e|tCO2)_per_MWh
```

with `electricity_MWh = kWh / 1000` when input is kWh.

### CBAM SEE v2.1 (`D_Processes`)

| Cell | Role |
|------|------|
| `L65` | Electricity consumption **MWh** |
| `L66` | Emission factor **tCO2/MWh** (example 0.439) |
| `T66` | `=SUM(L65)*SUM(L66)` → **indirect emissions** |
| `L71` | Electricity **exported** MWh (example 0) |
| `T72` | `=-SUM(L71)*SUM(L72)` → separate **negative direct** embed path |

**Exported electricity is not subtracted from consumption in `T66`.** Phase 8A stores export separately and does not include it in the indirect product.

## Units

- Canonical calculation unit: **MWh**
- Accepted quantity units: `kWh`, `MWh` only (GJ/MJ/mass/volume rejected)
- Result unit: **tCO2e** (not fossil `tCO2`)
- Factor units: electricity intensity allow-list including workbook `tCO2/MWh` and preferred `tCO2e/MWh`

## Factor source priority

1. `PLATFORM_DEFAULT` — resolve unique active `DEFAULT_REFERENCE` `CbamFactorValue` for definition `ELECTRICITY_GRID_EMISSION_FACTOR` covering the reference date. Zero matches → `UNRESOLVED_PLATFORM_DEFAULT`. Multiple → `AMBIGUOUS_PLATFORM_DEFAULT`.
2. `MANUAL` — explicit value (≥ 0), compatible unit, and mandatory provenance (source name/document, dataset/version, reference description).

**No Turkey/default numeric seed.** Workbook `0.439` lacks authoritative provenance → informational code `TURKEY_ELECTRICITY_DEFAULT_FACTOR_PROVENANCE_MISSING`.

Blank factor must not become zero; unresolved platform default must not fall back to zero.

## Snapshot / current / stale / idempotency

- Immutable `cbam_purchased_electricity_results`
- Current pointer per activity: `cbam_purchased_electricity_current_results`
- Stale when activity quantity/unit/date/type/status diverges from snapshot
- `clientRequestId` + fingerprint: same → replay; same key + changed material → `IDEMPOTENCY_KEY_REUSED`
- Failed execution does not replace current

## Out of scope

- Angular UI
- Product allocation of electricity
- Process / heat / waste gas / precursors
- Excel export wiring
