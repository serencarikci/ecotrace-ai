# 16. Complete example workflow

**Previous:** [Permissions, statuses, and errors](15-permissions-statuses-and-errors.md) · **Home:** [README](README.md)

Use the demo organization, steel screws & nuts installation, and one reporting period.

| Step | Action | Required input | Expected result | Blocking if… | Next |
|------|--------|----------------|-----------------|--------------|------|
| 1 | Sign in | Demo reviewer account | Dashboard | Bad credentials | Org |
| 2 | Select organization | Demo org | Correct company context | Wrong org | Installations |
| 3 | Create/open installation | Facility, code, name, timezone | Active installation | Missing facility | Periods |
| 4 | Create draft period + open data collection | Reporting period | Writable period | No period | Profiles |
| 5 | Create & publish product profiles | CN + required steel fields | Classification ready | CN fields incomplete | Production |
| 6 | Enter production records | Profile-linked quantities | Production rows | Profile not ready | Monthly D/E |
| 7 | Enter monthly D and E | Monthly tonnes | Allocation basis ready | Missing months | Activities |
| 8 | Enter fuel activity | Natural gas qty/unit/date | Activity row | Bad unit | Direct emissions |
| 9 | Calculate direct emissions | Activity + density if volume | Current fuel result | Density/params | Electricity |
| 10 | Enter electricity activity | kWh/MWh | Activity row | Bad unit | Indirect |
| 11 | Calculate indirect emissions | Factor + evidence | Current electricity result | Default missing without manual | Allocation |
| 12 | Allocate direct emissions | Ready fuel result + D/E | Current direct allocation | Incomplete D/E | Indirect allocation |
| 13 | Allocate indirect emissions | Ready electricity result + D/E | Current indirect allocation | Incomplete D/E | Processes |
| 14 | Define conventional process | Name, produced qty | Process draft | — | Distribution |
| 15 | Balance product distribution | Uses + non-CBAM | Remaining 0 / ready | Unbalanced | Heat/waste gas/exported electricity |
| 16 | Enter heat / waste gas / exported electricity if needed | Conditional fields | Saved process | Invalid lists | Precursors |
| 17 | Enter purchased precursors | Supplier or EU default | Draft precursor | Ambiguous default | Uses |
| 18 | Balance precursor uses | Product tonnes | Ready precursor | Unbalanced | Product Results |
| 19 | Calculate Product Embedded Emissions (v2) | All readiness green | Current product results | Any blocker section | Review |
| 20 | Review product results | — | Specific & absolute values | Out-of-date inputs | Report |
| 21 | Check Official Excel readiness | — | Ready | Missing product results/capacity/LibreOffice | Generate |
| 22 | Generate Official Excel | Edit permission | Processing → Completed | LibreOffice/formula check | Download |
| 23 | Wait for validation | — | File published | Failed run | Fix & retry |
| 24 | Download validated workbook | View or edit | `.xlsx` file | Not completed | Archive records |

## Supported vs not supported (MVP)

**Supported:** fossil stationary combustion; purchased electricity; monthly D/E; direct and indirect allocation; conventional processes; measurable heat; waste gas; process exported electricity; supplier & EU default precursors; internal product flows; product embedded emissions version 2; Official Excel generation (when LibreOffice is available on the API host).

**Not supported:** biogenic carbon; tax; Process Emissions method; Mass Balance method; hybrid precursor mode; automatic unverified Turkey electricity default; beyond-template capacity.

## Calculations in plain language

- **Fuel → direct CO₂:** energy content and fossil factor produce facility fossil CO₂.  
- **Electricity → indirect CO₂e:** MWh × factor.  
- **Monthly E/D:** share of each month’s emissions that is CBAM-relevant.  
- **Allocation:** that shared pool is split to products by production quantities.  
- **Processes:** tell how produced tonnes move between products (and optional heat/waste gas/electricity).  
- **Precursors:** bought inputs add embedded emissions (supplier numbers or EU defaults).  
- **Product embedded emissions (v2):** combines the above, including internal flows, into per-product results.  
- **Official Excel:** copies validated results into the CBAM SEE workbook and checks formulas before download.

## Inventories

Field and action lists: [inventories/](inventories/). Language audit: [inventories/a2-b1-language-audit.md](inventories/a2-b1-language-audit.md).
