# Product embedded-emissions roll-up V2 (Phase 10D backend)

**Status:** `PHASE_10D_BACKEND` (+ Processes Angular T72 fields)  
**Date:** 2026-08-30  
**Methodology code:** `CBAM_PRODUCT_EMBEDDED_EMISSIONS_V2` (version `2.0.0`)  
**Default:** V2 (V1 remains callable for regression / history)  
**Frontend:** Processes tab exported-electricity inputs only; **product-summary FE out of scope**  
**Excel export:** out of scope  
**Tax / HYBRID precursor mode:** out of scope

## What V2 adds over V1

1. **Process-level exported electricity (T72)** — workbook `D_Processes!T72 = -L71*L72` from process quantity × EF (may be negative). Reduces attributed **direct** emissions only (`S72=EmbedEmDir_`). Facility purchased-electricity export is reconciled, never copied into or divided across processes.
2. **Internal CBAM product flows (Leontief)** — process product-uses between READY Conventional processes form matrix  
   `A[consumer][supplier] = qty / TotProd(consumer)`. Specific embedded emissions solve `(I - A) · SEE = base` with exact Decimal arithmetic. Marketed (L27) and non-CBAM (L41) never enter `A`. Purchased precursors stay outside the internal matrix.

V1 history keeps a separate current pointer (`CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1`). Promoting V2 never rewrites a V1 result. Period summary prefers the V2 current when present, otherwise V1.

## Authoritative workbook

- File: `CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx`
- SHA-256: `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64`
- Primary sheet: `D_Processes`
- Consumer sheet: `Summary_Products`

## Formula graph (V2)

```text
own_direct   = T54 + T58 + T62 + T72
own_indirect = T66
purchased_*  = Σ product_use_tonnes × precursor specific (unchanged from V1)
base_SEE     = (own + purchased) / TotProd_
SEE          = (I - A)^-1 · base_SEE
internal_*   = Σ qty × supplier_SEE   (reconstructed from contributions)
total_*      = own_* + purchased_* + internal_*
specific_*   = total_* / TotProd_     → Summary_Products I/J/K
```

## Blocking / stale additions

| Code | Meaning |
|------|---------|
| `INTERNAL_PRODUCT_FLOW_SINGULAR` | `(I - A)` singular |
| `INTERNAL_PRODUCT_FLOW_SELF_REFERENCE` | process consumes its own CBAM output |
| `PROCESS_EXPORTED_ELECTRICITY_*` | incomplete L71/L72 / provenance / reconciliation mismatch (process readiness) |
| `PROCESS_EXPORTED_ELECTRICITY_CHANGED` | T72 inputs changed vs snapshot |
| `INTERNAL_PRODUCT_FLOW_*_CHANGED` | internal product-use set/quantity changed |

## API

- `POST .../product-embedded-emissions/executions` accepts optional `methodologyCode` (default V2).
- Immutable result + product rows snapshot T72 inputs, `internalDirect/Indirect`, and `cbam_product_embedded_emissions_internal_contributions`.
- Notes for V2 claim T72/Leontief **are** modeled (V1 notes remain on V1 results).

## Out of scope (still)

- Product-summary Angular section
- Excel export of V2 roll-up
- Tax / certificate calculation
- HYBRID precursor mode
