# Primary vs Default / Reference Data (Phase 3)

## `data_source_type`

| Value | Meaning |
|-------|---------|
| `PRIMARY` | Customer-measured or supplier-provided actual value |
| `DEFAULT_REFERENCE` | Later calculation may resolve a recognized default/reference (source TBD — B-04) |
| `UNKNOWN` | Source not yet established |

## UI copy (TR)

- **Birincil Veri:** Firma tarafından ölçülen veya tedarikçi tarafından sağlanan gerçek veri.
- **Varsayılan Referans:** Bir sonraki hesaplama aşamasında standart kaynaktan belirlenmesi beklenen değer.

## Phase 3 limits

- No IPCC/DEFRA/EPA selection is claimed.
- No evidence-file upload (D-042 / B-06).
- PRIMARY may carry `source_reference`, `measurement_method`, `supplier_name`, `certificate_reference`.
- Optional property overrides (`NET_CALORIFIC_VALUE`, `GROSS_CALORIFIC_VALUE`) only when `PRIMARY`; no invented defaults.
