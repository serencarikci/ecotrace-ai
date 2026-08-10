# CBAM / SKDM — Current MVP Scope (Frozen)

**Classification:** `READY_FOR_DOMAIN_VALIDATION`  
**Not claimed:** production-ready, regulatory-ready, official-CBAM-ready

## Implemented workflow

Installation → Reporting Period → Production → Activity Data → Purchased Inputs → Allocation → Factor Resolution → Calculation → SKDM Summary → Internal Excel Export

## Included

- Organization-scoped installations and reporting-period bindings
- Product profile versions (structure only; no CN invent)
- Production / activity / activity properties / purchased inputs
- Allocation methods: DIRECT_ASSIGNMENT, PRODUCTION_QUANTITY_RATIO, MANUAL_RATIO
- Primary/default factor resolution (fail-closed)
- Minimal calculation: `MULTIPLY_ACTIVITY_BY_FACTOR` only
- Internal SKDM workbook export + manifest + period summary
- Permissions `cbam:view` / `cbam:configure`
- Optimistic concurrency (`rowVersion` → 409)
- Audit for major CBAM actions
- Angular SKDM workflow tabs through **Rapor / Excel**

## Explicitly out of scope (frozen)

- CN / AGC classification
- Shipment
- Evidence upload
- Automatic IPCC/DEFRA/EPA numeric import
- Financial CBAM / certificate quantities
- New allocation methods or calculation formulas
- Sector-specific engines
- Official submission API
- Official EU workbook fabrication

## Official workbook

**BLOCKED** pending domain-expert/template delivery. Internal template is development-only.
