# Conventional production processes (Phase 9A / 9B / 9C)

**Status:** `PHASE_9A_BACKEND` + `PHASE_9B_ANGULAR` + `PHASE_9C_IEA_PRODUCT_ELECTRICITY` + `PHASE_10D_PROCESS_T72`  
**Date:** 2026-08-30  
**Frontend:** Angular **Processes** tab — Conventional only; no client math  
**Phase 9C:** Process `indirectEmissionsAllocation` exposes immutable current IEA product-row `allocatedElectricityMwh` + `allocatedIndirectEmissionsTco2e` by exact `productProfileVersionId` match (no migration)  
**Phase 10D:** Process-level exported electricity (`hasExportedElectricity`, L71/L72) with server `attributedDirectTco2e` (T72) and facility reconciliation  
**Still out of scope:** precursors / Excel export / Process Emissions / Mass Balance methods / product-summary FE

## Authoritative workbook

- File: `CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx`
- SHA-256: `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64`
- Primary sheet: `D_Processes` (Process 1 block starts row 11; stride 65)
- English labels: `Translations` column **C** (column B is language-selected display)

## Process field map (Process 1)

| Concept | Cell(s) | Notes |
|---------|---------|-------|
| Process index | `C11` | 1-based slot |
| Process name | `G11` | From `CNTR_List_ExistProdProcNames` (`A_InstData!T83:T92`) |
| Product / goods | `L11` | Aggregated goods from `CNTR_List_ExistProdProc` |
| Route amounts | `L16:L23` | Unit via `K16` / goods unit list |
| Produced total | `L24` | `=SUM(L16:L23)` — **process-specific** |
| Marketed | `L27` | Good to market |
| Market share | `L28` | Derived `L27/L24` — do not ask user |
| All to market | `L29` | Derived boolean — do not ask user |
| Use in other CBAM processes | `E32:E40` + `L32:L40` | Target process name + quantity |
| Non-CBAM use | `L41` | Consumed for non-CBAM goods |
| Control / remaining | `L42` | `=L24-SUM(L27,L32:L41)` must be **0** |
| Heat applicable | `K50` | True/False |
| Waste gas applicable | `L50` | True/False |
| Indirect relevance | `M50` | Goods-driven formula, not user flag |
| DirEm* | `L54` | Workbook entry; EcoTrace uses **current DEA** read-only |
| Heat import/export | `L57`/`M57` | TJ |
| Heat EF | `L58`/`M58` | tCO2/TJ |
| Heat attributed | `T58` | `=L57*L58-M57*M58` |
| Waste gas amounts | `L61`/`M61` | TJ |
| Waste gas EF UI | `L62`/`M62` | Decimal-validated but **not used by T62** |
| Waste gas attributed | `T62` | `=L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667` (`CONST_EFNatGas=56.1`) |
| Electricity consumption | `L65` | MWh — EcoTrace uses **current IEA** |
| Electricity EF / source | `L66`/`L67` | Source list `CONST_ElecSource` |
| Indirect emissions | `T66` | `=L65*L66` — not re-entered |
| Exported electricity | `L71`/`L72`/`T72` | `T72=-L71*L72`; **not** subtracted from `T66` |

## Supported calculation method

- **Active:** `CONVENTIONAL` only (standard SEE D_Processes attribution inputs)
- **Disabled enums (DB/API reject):** `PROCESS_EMISSIONS`, `MASS_BALANCE`
- Do **not** confuse these with source-stream `CONST_MonitoringApproach` (Combustion / Process emissions / Mass Balance on `C_Emissions&Energy`)
- Do **not** confuse Mass Balance **method** with product-quantity **distribution balance** (`L42`)

## Product distribution formula

```text
produced (L24)
  = marketed (L27)
  + Σ use in other CBAM products (L32:L40)
  + non-CBAM (L41)
remaining (L42) = produced − distributed
```

- Exact Decimal compare after mass-unit normalization to tonnes
- **No** invented business tolerance (e.g. 0.01)
- Draft save allowed while unbalanced; readiness blocked (`UNBALANCED` / `PRODUCT_DISTRIBUTION_UNBALANCED`)
- Typed relation: source profile (process) → target profile + quantity + unit
- Derived `marketShare` / `allToMarket` exposed read-only

## Production quantity source

Workbook `L16:L23→L24` is **process-block input**, distinct from EcoTrace `cbam_production_records`.

Phase 9A therefore:

- Persists explicit `produced_quantity` (+ unit) on the process
- Exposes reconciliation vs sum of active production records for the linked profile
- Never silently overwrites either source

## Direct / indirect allocation

- Read-only current DEA / IEA product allocation for the process profile
- Missing or stale current allocation → blocking readiness codes
- Historical result IDs remain referenceable via current pointer (`currentResultId`)
- Does **not** modify DEA/IEA engines

## Measurable heat

- Conditional on `hasMeasurableHeat`
- Persist amounts, units (TJ), EFs (tCO2/TJ), provenance
- When `false`, related fields must be null
- Attribution: workbook `T58` implemented as calculated view

## Waste gas

- Conditional on `hasWasteGas`
- Persist imported/exported TJ (+ provenance)
- Attribution uses workbook `CONST_EFNatGas=56.1` and export factor `0.667`
- Documented: `L62`/`M62` UI cells are not inputs to `T62`

## Exported electricity

### Facility (purchased-electricity) export — read-only context

- Reused from purchased-electricity current/immutable totals (`exported_electricity_mwh`)
- Exposed read-only on process responses as `exportedElectricity`
- Not subtracted from indirect consumption/allocation

### Process-level export (Phase 10D — workbook L71/L72 → T72)

- Conditional on `hasExportedElectricity`
- Persist quantity (MWh), emission factor (tCO2/MWh), provenance
- When `false`, related fields must be null
- Server calculates `attributedDirectTco2e = -(quantity_mwh × emission_factor)` (`T72=-L71*L72`); may be negative; **direct** bucket only
- Angular never multiplies qty×EF
- Installation reconciliation compares Σ process L71 vs facility export (MATCHED / MISMATCHED / NOT_COMPARABLE); EcoTrace never copies facility into process or divides a facility total across processes
- Feeds product embedded-emissions V2 own direct; V1 still forces T72 = 0

## Data quality

Lists extracted from workbook (English `Translations!C`):

- `CONST_DataQuality` (C1875–C1879)
- `CONST_DataVerification` (C1880–C1882)
- `CONST_DataQualityJustification` (C1883–C1884, C638)
- `CONST_ElecSource` (Parameters `B15:H15`)
- `CONST_MonitoringApproach` (informational; source streams)

**Note:** DQ fields appear on `C_Emissions&Energy`, not `D_Processes`. Phase 9A persists optional process DQ codes validated against extracted lists; they are **not** required for process READY in this phase (`DATA_QUALITY_ANSWER_REQUIRED` reserved).

## API (binding-scoped)

- `GET .../production-processes/metadata` and `.../controlled-lists`
- `GET/POST .../bindings/{id}/production-processes`
- `GET/PATCH .../production-processes/{processId}`
- `GET .../readiness`, `GET .../summary`
- `POST .../archive`
- Product-use CRUD under `.../product-uses`

Permissions: `cbam:view` reads; `cbam:configure` mutations.

## Out of scope

- Angular frontend
- Precursor embedded emissions
- Process Emissions / Mass Balance calculation methods
- Excel export changes
- DEA/IEA math changes
