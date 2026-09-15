# Official CBAM SEE Excel export (Phase 12A backend + Phase 12B UI)

**Status:** `MVP_ACCEPTANCE_PASSED` (2026-08-31) — real API → LibreOffice → authenticated download → reopened workbook path accepted  
**Date:** 2026-08-31  
**LibreOffice:** `/Applications/LibreOffice.app/Contents/MacOS/soffice` (26.8.0.3)  
**Frontend download UI (Phase 12B):** **Complete** — `app-cbam-official-see-export` in Report / Excel (internal Excel preserved)

### Acceptance progress
- Surgical XLSX ZIP/XML writer (`package_writer.py`) — does **not** use `openpyxl.save`
- Package inventory asserts `cfRule` / `extLst` counts are preserved on data sheets **after write**
- Post-LibreOffice package deltas gated by `LO_REGENERATED_OR_OPTIONAL_PARTS` allowlist (`assert_package_acceptable_after_libreoffice`)
- Steel Summary_Products mapping (P/Q/R/S/T/U/X) for slots 0..9 via `manifest_steel_patch_v1.json`
- Process master column F clearing via `manifest_process_f_patch_v1.json`
- LibreOffice at `/Applications/LibreOffice.app/Contents/MacOS/soffice` with unique UserInstallation, formula-cache strip before convert
- Expanded formula-error scan: manifest OUTPUT + `Summary_Communication` F/G/I/J/K + `Summary_Products` F/I/J/K/P for used slots
- I/J/K compare uses `workbook_places_for_cell` → format `0.000` ⇒ **3** decimal places (half-up); expected values from immutable PEE V2 DB snapshot only
- Publish only after LO recalc + OUTPUT parity + formula-error scan + package allowlist + leakage; staging file never becomes the artifact
- Golden: CN `73181595` + `73181699` (both in EcoTrace catalog and workbook `Parameters_CNCodes`)
- Angular Official Excel: readiness from official endpoint only; generate with in-memory `clientRequestId`; history + Blob download; view may download, configure may generate

### Golden acceptance artifact (not committed)
- Path: `/tmp/ecotrace-see-golden-acceptance/`
- Report: `report.json` (PEE decimals, 3 dp, sha256, mismatches)

## Template identity

| Field | Value |
|-------|--------|
| File | `CBAM SEE V2.1_Example Steel 3 Screws and nuts_final Dosyasının Kopyası- (1) (1).xlsx` |
| Path | `local-reference/` (authoritative; copy-on-ensure into export storage) |
| SHA-256 | `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64` |
| Mapping version | `official-see-mapping-v1` |
| Manifest | `mapping/manifest_v1.json` + `mapping/manifest_steel_patch_v1.json` |

## Writer policy

- Base = original template ZIP bytes; only mapped INPUT/CLEAR_EXAMPLE cells + sharedStrings + surgical `calcPr` are rewritten.
- Styles, drawings, theme, CF `extLst`, relationships stay byte-identical where untouched.
- openpyxl may be used **read-only** for forensics / leakage / formula map checks — never `save` for official artifacts.

## Steel columns (Summary_Products rows 10–19)

| Col | Field | Notes |
|-----|--------|--------|
| P | `reducing_agent` | Official labels: Coal or coke / Natural gas / Biogas / Hydrogen (`CONST_ReducingAgent`) |
| Q | `steel_mill_identification_number` | |
| R | `percent_mn` | null→blank; explicit 0→0 |
| S | `percent_cr` | |
| T | `percent_ni` | |
| U | `percent_other_alloys` | |
| X | `percent_other_materials` | (V is % carbon — not mapped; no coating) |

## Recalc engine

- Prefer `/Applications/LibreOffice.app/Contents/MacOS/soffice`, then `LIBREOFFICE_SOFFICE_PATH`, then `PATH`
- Unique `UserInstallation` profile per run; timeout; kill process group on hang; cleanup profile+tmpdir
- Strip cached `<v>` on formula cells before convert so LO recomputes (otherwise stale InputOutput caches break parity)

## Artifact lifecycle

1. Assess readiness (fail closed)
2. Verify template SHA → copy-on-ensure
3. Surgical clear/write to **staging** xlsx
4. LibreOffice recalc → OUTPUT parity (+ formula-error tokens fail) → package allowlist → leakage
5. Publish recalculated file + Postgres metadata
6. Download only when `COMPLETED` **and** `formula_parity_status=PASSED`

## Production / operational requirements

Minimum for Official SEE export in a real deployment:

| Requirement | Expectation |
|-------------|-------------|
| LibreOffice | Desktop/server `soffice` binary reachable without an interactive shell PATH. Prefer explicit `/Applications/LibreOffice.app/Contents/MacOS/soffice` (macOS) or `LIBREOFFICE_SOFFICE_PATH`. **Version tested in acceptance:** LibreOffice **26.8.0.3**. |
| Writable dirs | API process must write `REPORT_STORAGE_PATH` (artifacts), plus OS temp for LO `UserInstallation` profiles and staging. |
| Cleanup / retention | Each run uses a unique LO profile + temp dir; cleanup on success and failure. Successful artifacts persist under report storage with Postgres metadata; failed runs must **not** publish a downloadable artifact. Prior successful artifacts remain after a later failed generation. |
| API worker permissions | Process user needs execute on `soffice`, read on the official template, write/delete on temp + report storage. No interactive desktop session required. |
| Timeout / resources | LO convert is CPU/IO heavy; generation HTTP timeout should allow several minutes (acceptance used ≤600s). Kill process group on hang. |
| Failure monitoring | Alert on readiness `sofficeAvailable=false`, generation `FAILED`, repeated formula-parity failures, and storage write errors. |
| Template identity | Deploy with template SHA-256 `83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64` and mapping `official-see-mapping-v1`. UI shows `templateVersion`, `mappingVersion`, and `templateSha256` from readiness — do not hard-code labels that can disagree with the API. |
| Health / readiness | Platform `/health` and `/ready` remain DB-centric. Official SEE **period readiness** reports `sofficeAvailable`; when LibreOffice is missing, readiness is not Ready and generate fails closed without publishing an artifact. |

## UI version labels

Official Excel readiness shows separately:

- **Template version** ← `templateVersion` (human-readable, e.g. `CBAM_SEE_V2.1`)
- **Mapping version** ← `mappingVersion`
- **Template checksum** ← prefix of `templateSha256`

Run history uses the same `templateVersion` / `mappingVersion` fields from the run DTO.

## Out of scope

PDF, CSV, tax calculations, HYBRID precursors, Process Emissions, Mass Balance.
