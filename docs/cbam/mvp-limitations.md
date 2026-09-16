# SKDM MVP Limitations

> **Status note (2026-09):** This file describes **remaining MVP limitations**.  
> Official SEE Excel export is **implemented and accepted** for the local/demo path.  
> Authoritative current scope: [current-scope.md](current-scope.md) and [official-see-export.md](official-see-export.md).

## Implemented (do not mark as blocked)

- Official SEE Excel generation, LibreOffice recalculation, parity validation, authenticated download (Phase 12A/12B)
- Product Embedded Emissions V2
- Purchased precursors (supplier data + EU default)
- Direct and indirect emissions allocation (DEA / IEA)
- Conventional production processes (measurable heat, waste gas, process exported electricity)
- Stationary combustion direct emissions UI + APIs
- Purchased electricity indirect emissions UI + APIs

## Technical limitations (accepted)

- Only one **generic** calculation formula family for the Factors/Calculation path: `MULTIPLY_ACTIVITY_BY_FACTOR`
- Generic allocation methods remain limited to the three implemented rule types
- Same-unit technical totals are optional and non-regulatory
- Binary XLSX checksum may vary with ZIP metadata; manifest is authoritative for Official SEE
- No PDF generation in the CBAM module
- No approve/lock period workflow UI yet (locked status may exist in data model; full workflow not productized)
- Dedicated idempotency store (D-040) deferred; execution endpoints use `clientRequestId` patterns instead
- **Official SEE needs LibreOffice 26.8 on the API host.** The supported `apps/api/Dockerfile` installs Document Foundation LibreOffice 26.8 (aarch64 SHA pinned). Older Debian LibreOffice packages are rejected. GitHub Actions on amd64 does not build/run the golden LibreOffice job yet.
- Schema migration head for CBAM review DB: **`0032_cbam_prec_audit`** (`0032_cbam_precursor_audit_cols.py`)

## Explicitly out of scope (not defects)

- Biogenic carbon
- Tax / certificate quantity calculation
- Process Emissions calculation method
- Mass Balance calculation method
- HYBRID precursor source mode
- Automatic verified Turkey electricity default when provenance is unavailable
- Official EU submission API
- Capacity beyond Official SEE template slot/process limits

## Regulatory / domain open questions

See [domain-expert-open-questions.md](domain-expert-open-questions.md).

## Security posture (MVP)

- Tenant isolation via organization scope + 404 non-disclosure
- Export path traversal guards
- `.xlsm` rejected
- Spreadsheet formula-injection neutralization for exported data text
- Template formulas preserved and not overwritten by data writes

## Classification constraints

Do not label the module:

- PRODUCTION_READY  
- REGULATORY_READY  
- OFFICIAL_CBAM_READY (as a regulatory submission claim)

Official SEE **file generation** is available in the product; that is not the same as regulatory certification of the operator’s filing.
