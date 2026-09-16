# EcoTrace AI — CBAM / SKDM User Guide

**Status: COMPLETE** (see [coverage report](../user-guide-coverage-report.md))  
**Audience:** sustainability analysts and reviewers who prepare Carbon Border Adjustment Mechanism (CBAM), called SKDM in Turkish, period data  
**Language:** English (A2–B1)  
**Source of truth:** current Angular + FastAPI implementation (not older phase proposals)  
**Classification:** MVP documentation — not a claim of regulatory or submission readiness

**CBAM SEE** is the official workbook used for emissions communication. In EcoTrace, the **Official Excel** screen fills that workbook from validated period results. In the product UI, the module title may show **SKDM**. Routes and APIs use `cbam`. After these definitions, this guide uses **Official Excel** for user steps and **SKDM** when matching on-screen menu labels. See the [Glossary](glossary.md).

## Screenshots (real app captures)

Demo data only. Alt text is on each image below and in [assets/README.md](assets/README.md).

| Screen | Image |
|--------|-------|
| Sign in | ![Sign in page](assets/01-login.png) |
| Dashboard | ![Dashboard](assets/02-dashboard.png) |
| SKDM home | ![SKDM shell](assets/02b-skdm-shell.png) |
| Organizations | ![Organizations](assets/03-organizations.png) |
| Installations | ![Installations list](assets/04-installations-list.png) |
| Installation detail | ![Installation detail](assets/05-installation-detail.png) |
| Reporting periods | ![Reporting periods](assets/06-reporting-periods-list.png) |
| Period detail | ![Period detail](assets/07-reporting-period-detail.png) |
| Product Profiles | ![Product Profiles](assets/04-product-profiles.png) |
| Production | ![Production](assets/05-production.png) |
| Monthly allocation data | ![Monthly allocation data](assets/05b-monthly-allocation-data.png) |
| Activities | ![Activities](assets/06-activities.png) |
| Direct Emissions | ![Direct Emissions](assets/07-direct-emissions.png) |
| Indirect Emissions | ![Indirect Emissions](assets/08-indirect-emissions.png) |
| Processes | ![Processes](assets/09-processes.png) |
| Purchased Inputs | ![Purchased Inputs](assets/10-purchased-inputs.png) |
| Purchased Precursors | ![Purchased Precursors](assets/10b-purchased-precursors.png) |
| Product Results | ![Product Results](assets/11-product-results.png) |
| Allocation | ![Allocation](assets/12-allocation.png) |
| Direct emissions allocation | ![Direct emissions allocation](assets/12b-direct-emissions-allocation.png) |
| Indirect emissions allocation | ![Indirect emissions allocation](assets/12c-indirect-emissions-allocation.png) |
| Factors | ![Factors](assets/13-factors.png) |
| Calculation | ![Calculation](assets/13b-calculation.png) |
| Report / Excel | ![Report Excel](assets/14-report-excel.png) |
| Official Excel readiness | ![Official Excel readiness](assets/14b-official-excel-readiness.png) |
| Official Excel history | ![Official Excel history](assets/14c-official-excel-history.png) |
| Internal Excel | ![Internal Excel](assets/14d-internal-excel.png) |
| Official Excel completed download | ![Official Excel completed download](assets/14e-official-excel-completed-download.png) |
| Empty period | ![Empty period](assets/15-period-empty-state.png) |
| View-only period | ![View-only period](assets/16-view-only-period.png) |
| Locked state | ![Locked state](assets/17-state-locked.png) |

## How to use this guide

1. Start with [Getting started](01-getting-started.md).
2. Follow the screens in order, or jump from the table below.
3. Use [Complete example workflow](16-complete-example-workflow.md) for an end-to-end walkthrough.
4. Field / action / API inventories: [inventories/](inventories/) · language audit: [inventories/a2-b1-language-audit.md](inventories/a2-b1-language-audit.md).
5. Developers: [Technical UI→data traceability](../technical-ui-data-traceability.md) and [Data relationships & lifecycle](../data-relationships-and-lifecycle.md).

## Demo scenario used in examples

| Item | Demo value |
|------|------------|
| Organization | EcoTrace Demo Industries |
| Installation | LOCAL CBAM Review — Steel Screws & Nuts |
| Period | Review period covering steel screw/nut production |
| Products | Steel screws and nuts with CN codes in the catalog |
| Fuels | Natural gas (stationary combustion) |
| Electricity | Purchased electricity with an explicit factor and evidence |

Use only local demo data. Do not paste real customer data into documentation.

## Screen map (reachable)

| Screen | Route / place | Guide chapter |
|--------|---------------|---------------|
| Login | `/login` | [01](01-getting-started.md) |
| Dashboard / nav | `/app/dashboard` | [01](01-getting-started.md) |
| Organizations | `/app/organizations` | [02](02-organizations-and-installations.md) |
| SKDM shell | `/app/cbam` | [01](01-getting-started.md) |
| Installations list | `/app/cbam/installations` | [02](02-organizations-and-installations.md) |
| New installation | `/app/cbam/installations/new` | [02](02-organizations-and-installations.md) |
| Installation detail | `/app/cbam/installations/:id` | [02](02-organizations-and-installations.md) |
| Reporting periods | `/app/cbam/periods` | [03](03-reporting-periods.md) |
| Period detail (hub) | `/app/cbam/periods/:bindingId` | [03](03-reporting-periods.md) |
| Product Profiles tab | Period detail | [04](04-product-profiles.md) |
| Production tab | Period detail | [05](05-production.md) |
| Monthly allocation data | Inside Production | [05](05-production.md) / [12](12-allocation.md) |
| Activities tab | Period detail | [06](06-activities.md) |
| Direct Emissions tab | Period detail | [07](07-direct-emissions.md) |
| Indirect Emissions tab | Period detail | [08](08-indirect-emissions.md) |
| Processes tab | Period detail | [09](09-processes.md) |
| Purchased Inputs tab | Period detail | [10](10-purchased-inputs-and-precursors.md) |
| Purchased precursors | Inside Purchased Inputs | [10](10-purchased-inputs-and-precursors.md) |
| Product Results tab | Period detail | [11](11-product-results.md) |
| Allocation tab | Period detail | [12](12-allocation.md) |
| Factors tab | Period detail | [13](13-factors-and-calculations.md) |
| Calculation tab | Period detail | [13](13-factors-and-calculations.md) |
| Report / Excel tab | Period detail | [14](14-report-and-official-excel.md) |
| Official Excel section | Inside Report / Excel | [14](14-report-and-official-excel.md) |
| Permissions & errors | — | [15](15-permissions-statuses-and-errors.md) |

## Chapters

1. [Getting started](01-getting-started.md)
2. [Organizations and installations](02-organizations-and-installations.md)
3. [Reporting periods](03-reporting-periods.md)
4. [Product profiles](04-product-profiles.md)
5. [Production](05-production.md)
6. [Activities](06-activities.md)
7. [Direct emissions](07-direct-emissions.md)
8. [Indirect emissions](08-indirect-emissions.md)
9. [Processes](09-processes.md)
10. [Purchased inputs and precursors](10-purchased-inputs-and-precursors.md)
11. [Product results](11-product-results.md)
12. [Allocation](12-allocation.md)
13. [Factors and calculations](13-factors-and-calculations.md)
14. [Report and Official Excel](14-report-and-official-excel.md)
15. [Permissions, statuses, and errors](15-permissions-statuses-and-errors.md)
16. [Complete example workflow](16-complete-example-workflow.md)
17. [Glossary](glossary.md)

## Related technical docs

- [Coverage & verification report](../user-guide-coverage-report.md)
- [Technical UI→data traceability](../technical-ui-data-traceability.md)
- [Data relationships and lifecycle](../data-relationships-and-lifecycle.md)
- [Current MVP scope](../current-scope.md)
- [Official SEE export (technical)](../official-see-export.md)
- [Inventories](inventories/) · [A2–B1 language audit](inventories/a2-b1-language-audit.md) · [LibreOffice macOS codesign](inventories/libreoffice-macos-codesign.md)

## Screenshot note

Screenshots live under [`assets/`](assets/). Distinct evidence is required for Official Excel history, completed download, unbalanced, and stale states.
