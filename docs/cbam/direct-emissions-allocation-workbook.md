# SKDM allocation workbook analysis (Phase 7A gate)

**Status:** `PHASE_7A2_ALLOCATION_ENGINE` (immutable backend direct-emissions allocation implemented; Angular execution UI still out of scope)  
**Date inspected:** 2026-08-29  
**Purpose:** Record exact workbook cells/formulas and the Phase 7A-0 monthly production-basis foundation.

## Accessibility

| File | Path | Bytes | SHA-256 |
|------|------|------:|--------|
| Allocation template | `local-reference/SKDM_Alokasyon_Sablon.xlsx` | 12586 | `62300e30193aa2e696d07977697833431dcf782684cf61cace4e7e5f524cef72` |
| CBAM SEE v2.1 example | `local-reference/CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx` | 1318677 | `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64` |

- Both files open with openpyxl (`data_only=False`).
- Allocation sheet is not password-protected; 41 formula cells readable.
- `local-reference/` is listed in `.git/info/exclude` (not tracked `.gitignore`). Binary workbooks must not be committed.

## Allocation workbook structure

- **Sheets:** exactly one — `Firma Adı`
- **Named ranges:** none
- **Used range:** `A1:H26`

### Conversion factors (user inputs)

| Cell | Meaning | Example value |
|------|---------|---------------|
| `H2` | Doğalgaz yoğunluğu (kg/Sm3) | `0.68` |
| `H3` | Doğalgaz EF (tCO2/ton) | `2.6928` |
| `H4` | Elektrik EF (tCO2/MWh) | `0.439` |

### Monthly activity / production inputs (`A2:F5`)

| Column | Header | Role |
|--------|--------|------|
| `A` | Tarih | Month end date |
| `B` | Elektrik (KWh) | Electricity activity (out of Phase 7A scope) |
| `C` | Doğalgaz (Sm3) | NG volume |
| `D` | Tonaj üretim (Ton) | **Total plant production** (includes non-CBAM) |
| `E` | SKDM kapsamında ithalatçı firmaya giden miktar (Ton) | **CBAM/SKDM quantity** to importer |
| `F` | Toplam Doğalgaz (ton) | Derived NG mass |

Formulas:

- `F3` = `=C3*$H$2/1000` (and `F4`, `F5` likewise)
- `B6:F6` = `=SUM(...)` monthly totals

Example months: Jul/Aug/Sep 2024 with `D ∈ {506,421,337}`, `E ∈ {39.34,29.69,34.56}`.

### Step 1 — attribute fuel to CBAM scope (monthly)

Block `A8:E12`:

| Cell | Formula | Meaning |
|------|---------|---------|
| `B9` | `=IF(D3=0,0,(E3/D3)*F3)` | CBAM-attributed NG mass (ton) for month |
| `C9` | `=IF(D3=0,0,(E3/D3)*(B3/1000))` | CBAM-attributed electricity (MWh) — **out of Phase 7A** |
| `B12` | `=SUM(B9:B11)` | Total CBAM-attributed NG mass |
| `E9` | `=D9*C9` | Electricity tCO2e path — **out of Phase 7A** |

Zero total production (`D=0`) yields zero attributed fuel for that month.

**Non-CBAM treatment (workbook-authoritative):**  
Only the share `E/D` of monthly fuel mass enters the CBAM direct-emission pool. Non-CBAM production (`D−E`) does **not** receive attributed fuel in this template.

**Temporal grain:** Step 1 is **per month**. Aggregate `E6/D6` is **not** equivalent:

- Monthly sum attributed NG (`B12`) ≈ `0.0528853117267947` t
- Aggregate shortcut `E6/D6 * F6` ≈ `0.04797` t ≠ `B12`

### Step 2 — product split of direct emissions

| Cell | Formula | Meaning |
|------|---------|---------|
| `B15` | `=$B$12*$H$3` | **Toplam Doğrudan Emisyon (tCO2e)** — source for product CO2 |
| `B16` | `=$C$12` | Total attributed electricity (MWh) — out of Phase 7A |
| `B26` | `=SUM(B19:B25)` | **Denominator** = sum of product tonnages |
| `C19` | `=IF(B19="","",$B$15*(B19/$B$26))` | Product direct CO2 (and `C20`…`C25`) |
| `D19` | `=IF(B19="","",$B$16*(B19/$B$26))` | Product electricity — out of Phase 7A |

Product rows `B19:B21` example tonnages `39.336`, `34.559`, `29.688` (≈ monthly `E` values; sum `B26 = 103.583`).

**Product allocation denominator:** sum of **CBAM product tonnages** in `B19:B25` only — **not** total plant production `D6`.

**Conceptual product formula (matches workbook):**

```text
share_i = qty_i / Σ qty_j
allocated_direct_CO2_i = B15 × share_i
```

**Balance:** `Σ C19:C21 = B15` (exact with Decimal; cached Excel values match within float noise).

### Natural-gas trace (workbook example)

1. `C3=188` Sm3 → `F3=188×0.68/1000=0.12784` t NG  
2. `B9=(39.34/506)×0.12784≈0.009939181` t attributed NG  
3. Sum months → `B12≈0.052885312` t  
4. `B15=B12×2.6928≈0.142409567` tCO2e  
5. Ürün 1 share `39.336/103.583` → `C19≈0.054080522` tCO2e  

## CBAM SEE workbook (supporting)

Sheets include `Summary_Products`, `Summary_Processes`, `C_Emissions&Energy`, `D_Processes`, etc. Phase 7A does **not** take allocation formulas from SEE; SEE remains classification/communication context. Allocation math above is taken only from `SKDM_Alokasyon_Sablon.xlsx`.

## Mapping to EcoTrace

| Workbook concept | EcoTrace |
|------------------|----------|
| Current direct fossil CO2 | Stationary-combustion current results (`result_value` **tCO2**) |
| Product quantities `B19…` | Production records with Phase 6C profile links |
| Total plant production `D` | **Phase 7A-0** `cbam_monthly_production_basis.total_production_quantity` — workbook label **Tonaj üretim (Ton)** |
| SKDM quantity `E` | **Phase 7A-0** `cbam_monthly_production_basis.cbam_quantity` — workbook label **SKDM kapsamında ithalatçı firmaya giden miktar (Ton)** |
| Monthly `E/D` | Per-row `cbamShare` on each month; **period-wide `sum(E)/sum(D)` is forbidden** for allocation |

### Phase 7A-0 foundation (implemented)

- Binding-scoped monthly rows with canonical `month_start` (first calendar day).
- `D` is **not** derived from CBAM production records.
- `E` is explicit and may be reconciled (read-only) against eligible production; never overwritten.
- Incomplete draft rows allow null `D` or `E` → status `INCOMPLETE`.
- Summary: month coverage, SC activity-date compatibility, production reconciliation (`EXACT_MATCH` / `MISMATCH` / `UNAVAILABLE`).
- **Allocation execution is still out of scope.**

### Phase 7A-1 frontend (implemented)

- Production tab section **Monthly allocation data** for monthly D/E entry (A2–B1 English labels: Total production / Amount sent to the importer).
- Months come from the binding summary; UI shows readable names (e.g. January 2026) and sends canonical `monthStart` unchanged.
- Backend-authoritative `cbamShare`, `allocationBasisReady`, coverage status, blocking codes, SC compatibility, and production reconciliation.
- No period-wide `sum(E)/sum(D)` display; no Calculate/Allocate controls; allocation execution remains unavailable.

### Phase 7A-2 backend allocation engine (implemented)

- Methodology: `STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1` (not generic production ratio).
- Stage 1: for each current SC source result, attribute measures by that month’s `E/D` (`monthly_share`); sum attributed CO2 after monthly attribution (never `sum(E)/sum(D)`).
- Stage 2: split the period CBAM fossil CO2 pool by eligible product-profile groups using `qty_i / Σ qty_j`, with 8-dp largest-remainder conservation.
- Immutable snapshots (monthly basis, source, product), current pointer, `clientRequestId` idempotency, stale detection, monthly-basis delete protection.
- Stored unit remains `tCO2`; workbook reporting metadata exposes `tCO2e` with GWP=1 for CO2.
- API: readiness / executions / results / summary under `.../direct-emissions-allocation/...`.
- **Angular allocation execution UI remains out of scope.**
- Electricity / process / precursor paths remain out of scope.

## Remaining before allocation execution UI / export

1. Angular Direct Emissions / Allocation execution UI for Phase 7A-2.
2. Optional Excel mapping of allocated direct emissions.
3. Electricity / process / precursor paths (explicitly out of Phase 7A).

### tCO2 vs workbook tCO2e

- Stationary-combustion persisted unit remains **`tCO2`** (Phases 1–5).
- Workbook product column may say **tCO2e**; for fossil CO2, GWP=1 so the numeric value is equivalent.
- Do not rename stored SC results; allocation/export may present `tCO2e` as reporting representation with conversion factor **1** for CO2 only.
- CH4 / N2O / biogenic carbon remain out of scope.

## What is already unambiguous

- Product-level method: production-quantity ratio against **sum of participating CBAM product quantities**.
- Direct-emission output unit: workbook **tCO2e** reporting / EcoTrace SC **`tCO2`** storage.
- Balance target: sum of product allocated direct CO2 equals the CBAM-attributed direct source total.
- Electricity path (`C9`/`D19`/`H4`) is explicitly **out of Phase 7A**.
- Process distribution / precursors / Excel export remain out of scope.

## Reuse-versus-dedicated (preview)

Prefer a **dedicated** direct-emissions allocation run (SC current pointers + monthly D/E + production-profile eligibility + immutable snapshot + idempotency), not generic Phase 4A quantity allocation.