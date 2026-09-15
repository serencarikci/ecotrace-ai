# Excel Template Model

## Entity: `CbamExportTemplate`

| Field | Notes |
|-------|--------|
| organization_id | Nullable — platform templates use `NULL` |
| code / name / version | Identity + immutability of used versions |
| template_type | `INTERNAL_SKDM`, `OFFICIAL_CBAM_TEMPLATE`, `CUSTOMER_TEMPLATE` |
| mapping_version | Explicit mapping version tied to the template |
| storage_uri | Relative URI under report storage (no DB binary) |
| checksum | SHA-256 of template file |
| status | `DRAFT` / `ACTIVE` / `ARCHIVED` |

## Rules

- ACTIVE template must have a valid `.xlsx` file and checksum.
- Active templates are not silently replaced; new workbook → new version.
- `.xlsm` / macros are rejected.
- Official CBAM templates are not seeded; type remains available for future delivery.

## Storage layout

```
cbam/templates/{template_code}/{version}/template.xlsx
cbam/organizations/{organization_id}/periods/{binding_id}/exports/{export_run_id}/...
```

Raw server paths are never exposed via API.
