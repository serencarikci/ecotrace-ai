# CBAM Frontend Feature Map

> **DEPRECATED as route authority (2026-09).**  
> Use [user-guide/README.md](user-guide/README.md) and [technical-ui-data-traceability.md](technical-ui-data-traceability.md) for current screens.  
> This file is retained only as historical proposal context. Do not treat listed routes below as implemented unless they appear in `apps/web/src/app/app.routes.ts`.

**UI language note:** Navigation and page titles may show **SKDM**; code, routes, and API clients use `cbam`.

## Implemented routes (authoritative)

From `app.routes.ts`:

| Route | Component |
|-------|-----------|
| `/app/cbam` | `CbamShellComponent` |
| `/app/cbam/installations` | `CbamInstallationListComponent` |
| `/app/cbam/installations/new` | `CbamInstallationFormComponent` |
| `/app/cbam/installations/:installationId` | `CbamInstallationDetailComponent` |
| `/app/cbam/periods` | `CbamPeriodListComponent` |
| `/app/cbam/periods/:bindingId` | `CbamPeriodDetailComponent` |

Period detail hosts these tabs (exact UI labels): Product Profiles, Production, Activities, Direct Emissions, Indirect Emissions, Processes, Purchased Inputs, Product Results, Allocation, Factors, Calculation, Report / Excel.

Embedded child UIs (implemented — do not document as missing): monthly allocation data, stationary combustion, purchased electricity, production processes, purchased precursors, product embedded emissions (PEE V2), direct/indirect emissions allocation, Official SEE Excel (readiness / generate / history / download).

**Not blocked:** Official SEE Excel export is present on the Report / Excel tab. Runtime requires LibreOffice **26.8** on the API host (TDF image). GitHub CI does not claim golden LibreOffice parity yet.

## Permissions

- View CBAM screens: roles covered by `canViewCbam` / viewer+analyst+manager+admin patterns (`cbam:view` enforced on API)
- Configure / mutate: `canConfigureCbam` → system admin, organization admin, sustainability manager (`cbam:configure` on API)

## Historical proposal (not registered)

The following paths were proposed in earlier phases and are **not** present in `app.routes.ts`:

- `/app/cbam/product-profiles` (standalone)
- `/app/cbam/installations/:id/setup|processes|routes`
- `/app/cbam/periods/:id/dashboard|configuration|shipments|evidence|validation|approvals|verification-package`
- Standalone `/app/cbam/reference`

Do not document these as live operator screens.
