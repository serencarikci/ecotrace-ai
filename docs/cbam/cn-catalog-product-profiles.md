# CBAM CN catalog and product profiles (Phase 6A)

## Authoritative source

Official CBAM SEE communication template (workbook version **2.1**).

- Dataset code: `CBAM_SEE_CN_CODES`
- Dataset version: `SEE_V2.1`
- Seed artifact: `apps/api/src/ecotrace/modules/cbam/data/cbam_see_v2_1_cn_catalog.json`
- Extraction: `apps/api/scripts/extract_cbam_see_cn_catalog.py` (does **not** commit the binary workbook)

CN catalog is separate from IPCC stationary-combustion fuels, DVs, and CBAM benchmarks.

## CN codes

- Stored as text; leading zeroes preserved; display formatting kept separately from normalized code
- Source locator: workbook `CNKEY` + `Parameters_CNCodes` row
- Category/header rows are not seeded
- Active search excludes inactive rows; historical rows remain auditable

## Product identity

Reuses organization-scoped `products.id`. CBAM `cbam_product_profile_versions` holds versioned classification snapshots (CN fields copied at selection time).

## Steel-specific fields (Iron or steel products)

From SEE `Parameters_Constants` special-parameter matrix / `Summary_Products`:

- Main reducing agent (controlled: Coal or coke, Natural gas, Biogas, Hydrogen)
- Steel mill identification number
- Optional composition percentages: `% Mn`, `% Cr`, `% Ni`, `% other alloys`, `% other materials`

Blank percentages stay **null** (not zero). Entered values must be 0–100. Partial sets ≤100 are allowed. When all applicable composition fields are present, their sum must equal 100.

The workbook does **not** define a separate coating input on product summary; coating is not modeled as a product-profile field.

### Field applicability (Phase 6A+)

Authoritative per-CN `fieldApplicability` is persisted on each `cbam_cn_codes` row (workbook-derived at extract/seed time) and exposed on:

- `GET .../cn-codes/{cn_code_id}` → `CnCodeResponse.fieldApplicability`
- product profile read/create/update responses → `ProductProfileResponse.fieldApplicability` (from the referenced immutable CN row)

All seven keys are always present as booleans. Clients must not infer applicability from sector name, CN prefixes, labels, or `missingRequirements`.

The same persisted map drives `classificationReady`, profile validation, and fail-closed write rules:

- Explicit writes of non-applicable special fields → `422 VALIDATION_ERROR` with `*_NOT_APPLICABLE`
- Changing a **draft** profile’s CN code clears leftover non-applicable special-field values (no hidden stale steel values)
- Published profiles remain immutable

## Frontend (Phase 6B)

Period-detail tab **Product Profiles** (before Production):

- Lists organization products (existing products API); empty state links to `/app/products`
- CN search via catalog API (debounce, no free-text CN submit)
- Conditional special fields from `fieldApplicability` only
- Reducing material options from `REDUCING_AGENT` controlled list
- Draft save / publish / create new version / archive; readiness from server only
- No coating field; allocation remains out of scope

## Lifecycle and readiness

Statuses: `draft` → `active` (publish) / `superseded` / `archived`. Exactly one `active` version per org+product. `classificationReady`, `missingRequirements`, and `validationIssues` are computed server-side.

Allocation and product-level emission calculation remain out of scope.

## Production linkage (Phase 6C)

Production records store an immutable `product_profile_version_id` (nullable for legacy rows only).

| Write path | Rule |
| --- | --- |
| Create / re-link | Must reference an **active** and **classificationReady** profile in the same organization. Draft, superseded, and archived versions are rejected. |
| Historical read | After a newer version is published, older production rows keep their original version id. Status becomes `OUTDATED` when the linked version is superseded or archived; rows stay readable. Publishing does **not** rewrite historical production. |
| Legacy null | Readable as `MISSING`; blocks binding allocation-profile readiness; user may explicitly PATCH a valid profile. Newest profile is never auto-assigned. |

Authoritative response fields: `profileLinkStatus`, `profileLinkIssueCodes`, plus profile identity snapshots. Period-wide counts: `GET .../production-profile-link-summary` (`eligibleRecordCount`, `missingProfileCount`, `outdatedProfileCount`, `invalidProfileCount`, `allocationProfileReady`). Do not derive readiness from a paginated production page.

Allocation formulas remain out of scope.
