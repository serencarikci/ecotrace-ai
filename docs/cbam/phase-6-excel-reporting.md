# Phase 6 — Excel Mapping & SKDM Report Generation

**Status:** Implemented (internal template / mapping infrastructure)

Phase 6 adds the **output layer** for the existing CBAM workflow. It maps approved EcoTrace data into an Excel-compatible export model, populates an internal development workbook, and generates an internal **SKDM Dönem Özeti**.

## Flow

```
User Data → Production / Activity / Purchased Inputs
         → Allocation → Factor Resolution → Calculation (Phase 5)
         → Excel Mapping → Excel Output → SKDM Period Summary
```

Phase 5 remains the sole calculation engine. Export **consumes** calculation results; it does not reimplement emission math.

## Deliverables

| Item | Notes |
|------|--------|
| `CbamExportTemplate` / `CbamExportMapping` | Template + allow-listed mappings |
| `CbamExportRun` / `CbamExportArtifact` | Run metadata + file artifacts (XLSX, manifest, JSON/HTML summary) |
| Migration `0013_cbam_excel_export` | Additive tables only |
| Internal workbook | `ECOTRACE_SKDM_INTERNAL` — not an EU template |
| Readiness | READY / READY_WITH_WARNINGS / NOT_READY |
| UI | Period detail tab **Rapor / Excel** |

## Official workbook

**BLOCKED:** Official CBAM workbook mapping pending domain-expert/template delivery.

No official EU/SKDM submission format was fabricated.

## Related docs

- [excel-template-model.md](excel-template-model.md)
- [excel-mapping.md](excel-mapping.md)
- [export-readiness.md](export-readiness.md)
- [export-traceability.md](export-traceability.md)
- [internal-skdm-template.md](internal-skdm-template.md)
- [reporting-limitations.md](reporting-limitations.md)
- [phase-6-implementation-report.md](phase-6-implementation-report.md)
