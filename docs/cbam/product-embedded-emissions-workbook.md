# Product embedded-emissions roll-up (Phase 10C backend)

**Status:** `PHASE_10C_BACKEND`
**Date:** 2026-08-30
**Methodology code:** `CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1` (version `1.0.0`)
**Frontend:** out of scope
**Excel export:** out of scope
**Tax:** out of scope
**HYBRID precursor mode:** out of scope

## Authoritative workbook

- File: `CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx`
- SHA-256: `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64`
- Primary sheet: `D_Processes` (Process 1 block, stride 65)
- Consumer sheet: `Summary_Products` (columns I / J / K)

## Formula graph

The roll-up is a read-only combination of values that other engines already produced. It
never recalculates direct allocation, indirect allocation or precursor math.

```text
own_direct   = T54  DEA product fossil CO2      (tCO2, numerically tCO2e at GWP = 1)
             + T58  measurable heat attributed  (= L57*L58 - M57*M58)
             + T62  waste gas attributed        (= L61*EF_NG - M61*EF_NG*0.667)
             + T72  exported electricity        (= -L71*L72 → always 0 in V1)

own_indirect = T66  IEA product allocated indirect emissions (tCO2e)

precursor_direct(k→p)   = product_use_tonnes(k, p) × specific_direct(k)
precursor_indirect(k→p) = product_use_tonnes(k, p) × specific_indirect(k)

total_direct   = own_direct   + Σ precursor_direct
total_indirect = own_indirect + Σ precursor_indirect
total_embedded = total_direct + total_indirect

denominator       = process produced quantity (L24 → TotProd_) converted to tonnes
specific_direct   = total_direct   / denominator     → Summary_Products!I
specific_indirect = total_indirect / denominator     → Summary_Products!J
specific_total    = total_embedded / denominator     → Summary_Products!K = SUM(I:J)
```

### Signs

| Cell | Formula | Sign behaviour |
|------|---------|----------------|
| `T54` | `=IF(G11="","",L54)` | positive; allocated direct emissions of the process |
| `T58` | `=IF(G11="","",SUM(L57*L58-M57*M58))` | imported heat adds, exported heat subtracts |
| `T62` | `=IF(G11="","",SUM(L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667))` | imported waste gas adds, exported waste gas credits at 66.7% |
| `T66` | `=IF(G11="","",SUM(L65)*SUM(L66))` | positive; electricity × electricity EF |
| `T72` | `=IF(G11="","",-SUM(L71)*SUM(L72))` | negative by construction; **direct** bucket only |
| `S72` | `=CONST_CNTR_EmbedEmDir&G11` | confirms `T72` feeds `EmbedEmDir_`, never the indirect total |

## Denominator

The specific-emission denominator is the **process produced quantity** (`L24` → `TotProd_`)
converted to tonnes. Marketed quantity is never used, and the sum of production records is
never used as the denominator either.

Production records are reconciled, not substituted:

- No active production records for the profile → the process produced quantity stands alone.
- Active records present → both figures are exposed; if they differ at exact `Decimal`
  precision the product is blocked with `PRODUCT_DENOMINATOR_MISMATCH`.
- A missing or non-positive denominator fails closed (`PRODUCT_DENOMINATOR_MISSING`,
  `PRODUCT_DENOMINATOR_ZERO`). No division is ever attempted against zero.

## Units: tCO2 vs tCO2e

Direct-emissions allocation persists fossil CO2 in **tCO2**. The roll-up reports **tCO2e**
using numeric equivalence at GWP = 1 for CO2: no conversion factor is applied and no
historical DEA field is renamed. The source unit stays visible in the snapshot as
`deaSourceUnit = tCO2`, alongside `workbookGas = CO2`, `workbookGwp = 1`.

Absolute values are `tCO2e`; specific values are `tCO2e/t`.

## Precision

Raw values are persisted at `NUMERIC(36, 18)` and the reporting mirrors at `NUMERIC(24, 8)`.
All identities (`total_direct = own + precursor`, `total_embedded = direct + indirect`,
`specific = total / denominator`) are asserted on the **raw** Decimal values before any
quantization, so rounding never hides a broken sum.

## V1 limitations

### T72 exported electricity is always zero

`T72 = -L71*L72` needs a process-level exported electricity quantity and emission factor.
EcoTrace does not model `L71`/`L72` on the production process, and the facility-level
purchased-electricity export must not be attributed to a single product. V1 therefore
snapshots `exportedElectricityDirectTco2e = 0` with the note code
`PROCESS_LEVEL_EXPORTED_ELECTRICITY_INPUTS_NOT_MODELED`. When a facility-level export is
present the readiness response raises that code as **informational** — never as an
allocation. Indirect emissions are untouched by export in every case.

### No internal process-to-process Leontief

The workbook solves a Leontief system across process-as-precursor relations. EcoTrace has
no process-as-precursor concept, so that block is identically zero and the system collapses
into the direct sum of purchased-precursor contributions shown above. The note code is
`INTERNAL_PROCESS_PRECURSOR_LEONTIEF_NOT_MODELED`.

Consequence for validation: workbook `Summary_Products` Product 1
(`I10 = 0.868957674443175`, `J10 = 0.37707768433481187`, `K10 = 1.2460353587779869`) is
produced by the full four-precursor Leontief inverse and is **not** reproducible by V1. It
is asserted in the test suite as a reference value with that caveat documented, not as an
engine expectation.

## Scope and eligibility

Execution is **binding-scoped**: one immutable result carries N product rows, mirroring the
direct-allocation pattern. A product-profile version is eligible when all of the following
hold; otherwise it contributes blocking codes and the whole execution fails closed (an
empty success is never created).

1. Exactly one draft process links that `productProfileVersionId`
   (`PROCESS_AMBIGUOUS_FOR_PRODUCT` when several do).
2. The process uses the Conventional method (`PROCESS_METHOD_UNSUPPORTED`) and is `READY`
   (`PROCESS_NOT_READY`).
3. A current, non-stale direct allocation exists and has a row for the profile
   (`DIRECT_EMISSIONS_ALLOCATION_NOT_READY`, `DIRECT_EMISSIONS_ALLOCATION_STALE`,
   `DEA_PRODUCT_ROW_MISSING`).
4. A current, non-stale indirect allocation exists and has a row for the profile
   (`INDIRECT_EMISSIONS_ALLOCATION_NOT_READY`, `INDIRECT_EMISSIONS_ALLOCATION_STALE`,
   `IEA_PRODUCT_ROW_MISSING`).
5. Every purchased precursor with a product use targeting the profile is `READY` and carries
   both specific values (`PRECURSOR_NOT_READY`, `PRECURSOR_SPECIFIC_VALUES_MISSING`,
   `PRECURSOR_USE_UNIT_INVALID`).
6. The profile is classification-ready and linkable (`PRODUCT_PROFILE_NOT_LINKABLE`).
7. The denominator is positive and reconciles with production records (see above).

A precursor use that targets a product with no process is reported as
`PROCESS_MISSING_FOR_PRODUCT`. When nothing is eligible the readiness response carries
`PRODUCT_EMBEDDED_EMISSIONS_NO_ELIGIBLE_PRODUCTS`.

## Idempotency, current pointer, staleness

The fingerprint covers methodology and workbook identity, the direct/indirect current
result ids and their per-product values, the process id, row version, produced quantity and
heat/waste-gas flags and inputs, the precursor ids, row versions, mode, specific values and
default-snapshot identity, the product-use ids, quantities, units and targets, and the
production-record quantity set.

- First success returns `201`; the same key with the same fingerprint replays `200`; the
  same key with a different fingerprint returns `409 IDEMPOTENCY_KEY_REUSED`; concurrent
  identical requests produce exactly one result.
- A successful execution advances the current pointer. A failed execution leaves the
  previous pointer untouched and writes no result row.
- Staleness is evaluated live for the current result only. Detail responses always return
  the immutable snapshot; superseded results are never reported as stale.
- Row versions participate in the fingerprint but **not** in the stale evaluation, so
  renaming a process or a precursor does not invalidate a result. Material changes do:
  allocation results, per-product allocated values, produced quantity, denominator,
  heat/waste-gas inputs, the precursor and product-use sets, specific values, default
  snapshot identity, and production records.

## Snapshot integrity

Result, product and contribution rows are snapshots, not links. They deliberately carry no
foreign key to `cbam_production_processes`, `cbam_purchased_precursors` or
`cbam_purchased_precursor_product_uses`, so those drafts remain editable and deletable after
a roll-up has been executed. Foreign keys are kept only against immutable rows (results,
allocation results, product-profile versions).

## API

All routes are binding-scoped under
`/api/v1/cbam/organizations/{orgId}/reporting-period-bindings/{bindingId}/product-embedded-emissions`:

| Method | Path | Permission |
|--------|------|------------|
| GET | `/readiness` | `cbam:view` |
| POST | `/executions` | `cbam:configure` |
| GET | `/results` | `cbam:view` |
| GET | `/results/{resultId}` | `cbam:view` |
| GET | `/summary` | `cbam:view` |

The execution body accepts `clientRequestId` only; every other field is rejected, because
all totals are server-authoritative.

## Out of scope

- Angular frontend
- Excel / SKDM export
- Tax calculations
- Any change to the direct, indirect or precursor calculation engines
- HYBRID precursor data-source mode
- Process-as-precursor (internal Leontief) chains
