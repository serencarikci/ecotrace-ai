# Export Readiness

`GET .../reporting-period-bindings/{bindingId}/export-readiness`

## Statuses

| Status | Meaning |
|--------|---------|
| READY | All required checks OK |
| READY_WITH_WARNINGS | Exportable; non-blocking warnings present |
| NOT_READY | Blocking missing prerequisites |

## Checklist codes

| Code | Label (UI) |
|------|------------|
| production | Üretim verisi |
| activity | Faaliyet verisi |
| purchased | Satın alınan girdiler |
| allocation | Alokasyon |
| factors | Faktör çözümleme |
| calculation | Hesaplama |
| mappings | Excel eşlemeleri |

Each check: `OK` / `WARNING` / `MISSING`.

## Policy (Phase 6)

- Activity data required.
- Calculation run must be `COMPLETED` or `PARTIALLY_COMPLETED` with at least one `CALCULATED` result.
- Missing production/purchased/allocation may warn (non-blocking) depending on check.
- Internal template always sets `officialMappingBlocked=true` and adds an official-mapping warning → typical status `READY_WITH_WARNINGS`.
- BLOCKED calculation results are never treated as zero for readiness or export.
