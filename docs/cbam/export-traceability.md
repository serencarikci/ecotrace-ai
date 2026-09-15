# Export Traceability

Every completed export produces `export-manifest.json` alongside the XLSX.

## Manifest fields

- exportRunId, organizationId, reportingPeriodBindingId
- templateCode, templateVersion, templateChecksum
- mappingVersion, mappingChecksum
- calculationRunId
- generatedAt, applicationVersion
- mappedFields, warnings, artifactChecksum
- traceability: allocationResultIds, factorResolutionIds, calculationResultIds
- officialMappingBlocked, disclaimer

No secrets are included.

## Principles

- Historical exports remain downloadable with the **original** template/mapping versions.
- Manifest checksum is authoritative for semantic traceability.
- Binary XLSX checksum reproducibility may vary with ZIP/container metadata; document accordingly.
- Audit actions: `cbam.export.generated`, `cbam.export.failed`, `cbam.export.downloaded` (+ template lifecycle where used).
