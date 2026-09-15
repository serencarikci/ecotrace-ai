# Field discovery count change (414 → 419)

**Old accepted count:** 414  
**New discovered count:** 419  
**Delta:** 5

## Exact reason

A later HTML template harvest re-scanned `apps/web/src/app/features/cbam/**/*.html` and counted additional visible UI nodes that the earlier **414** freeze did not include:

1. Extra readiness / status / metric display blocks (`class="…"` status panels) on DEA, IEA, Product Results, Official SEE, and CBAM shell.
2. Additional table-column headers and readonly metric grids harvested as distinct field rows.
3. Precursor / production-process form controls that were added or split in templates after the original inventory freeze.

All **419** rows are documented in `fields.csv` with the full acceptance column set; **unexplained = 0**.

Actions remain **148** (unchanged target).
