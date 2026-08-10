# BLOCKED — Calculation / Factor Decisions

Phase 5 implements a **minimal** `MULTIPLY_ACTIVITY_BY_FACTOR` engine using already-resolved factors. It is not a full regulatory CBAM calculation framework.

## Implemented (partial)

| ID | Topic | Phase note |
|----|-------|------------|
| B-05 (partial) | Primary-data precedence | Phase 4B selection |
| B-04 (partial) | Source catalog metadata | IPCC/DEFRA/EPA **names only** |
| B-19 (partial) | Explicit multiply | Phase 5: only when definition + units compatible |

## Still BLOCKED / unresolved

| ID | Topic |
|----|-------|
| B-01 | Mapping of Category 1 / 2 / 4.1-like groupings to final SKDM regulatory model |
| B-02 | Authoritative activity-type list |
| B-03 | Authoritative unit list |
| B-04b | Authoritative default factor source per activity + approved dataset versions |
| B-05b | Exact IPCC/DEFRA/EPA precedence for all parameters |
| B-06 | Required evidence for primary values (also D-042) |
| B-11 | Supplier-provided embedded-emission units and full semantics |
| B-12 | Sector-specific process inputs and formulas |
| B-13 | Biogenic CO2 treatment / GWP tables / CO2 vs CO2e |
| B-14 | Waste / recycling scenarios |
| B-15 | **Official** Excel workbook mapping (internal template/mapping is Phase 6; official remains BLOCKED) |
| B-16 | Geographic electricity factors |
| B-17 | Oxidation factors |
| B-18 | Embedded emission fallback rules |
| B-20 | Final regulatory CBAM totals / certificate liability / financial obligation |

## Must not be implemented until confirmed

- Unapproved sector equations / multi-step calorific chains
- Automatic external factor download/import
- Implicit GWP / CO2→CO2e conversion
- Official CBAM workbook / regulatory submission format
- CN/AGC classification content
- Certificate quantity / financial CBAM obligation
