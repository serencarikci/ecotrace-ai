# CBAM Phase 3 — Basic Data Collection Foundation

**Status:** Implemented (data capture only; no calculation)

This phase collects operational SKDM inputs under a reporting-period binding. It does **not** calculate emissions, allocate shared resources, resolve factors, generate Excel, or produce CBAM reports.

> Note: The historical roadmap numbered “Phase 3” as reference-data versioning. This implementation follows the approved product prompt for **Basic Data Collection Foundation** and advances activity-style capture before CN catalog content.

## Implemented

- Production quantity records (`CbamProductionRecord`)
- Activity records (`CbamActivityRecord`) with controlled activity types/units
- Purchased input records (`CbamPurchasedInputRecord`) with purchased vs consumed distinction
- Optional activity property overrides (calorific value codes only; no defaults)
- Primary / default-reference / unknown source typing
- Organization isolation, audit, `row_version`, SKDM period UI tabs

## Not implemented

- Allocation, emission factors, IPCC/DEFRA/EPA/APCC lookup
- Carbon calculation, Excel, CBAM report
- CN/AGC, shipment, evidence upload (D-042)
- Stock ledger / FIFO / opening-closing stock
- Sector-specific process formulas

## Entry point

SKDM → Dönemler → binding detail → tabs: Üretim / Faaliyet Verileri / Satın Alınan Girdiler

Writable when binding status is `draft` or `data_collection`. Locked/approved remain fail-closed (D-030).
