# CBAM Phase 4B — Factor Resolution Foundation

**Status:** Implemented (selection only)

Answers:

> Which value should the calculation engine use?

Does **not** answer emission quantities.

## Delivered

| Item | Detail |
|------|--------|
| Migration | `0011_cbam_factor_resolution` |
| Tables | reference sources, factor definitions, factor values, factor resolutions |
| Precedence | RECORD_PRIMARY → ORG_PRIMARY → DEFAULT_REFERENCE → UNRESOLVED |
| Ambiguity | equal-rank candidates → `AMBIGUOUS` (no auto-pick) |
| UI | SKDM dönem detayı → **Faktörler** |

## Related

- [factor-model.md](factor-model.md)
- [primary-data-precedence.md](primary-data-precedence.md)
- [reference-source-model.md](reference-source-model.md)
- [factor-resolution-rules.md](factor-resolution-rules.md)
- [factor-resolution-limitations.md](factor-resolution-limitations.md)
- [phase-4b-implementation-report.md](phase-4b-implementation-report.md)
