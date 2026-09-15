# A2–B1 language audit — CBAM end-user guide

**Date:** 2026-09-15  
**Scope:** `docs/cbam/user-guide/01-*.md` … `16-*.md`, `README.md`, `glossary.md`  
**Excluded from end-user rewrite:** `inventories/*` (except this file), `assets/README.md`, `_inventory-generated.md`

## Exact counts

| Metric | Count |
|--------|------:|
| Pages checked | **18** (17 chapters/README + glossary) |
| Paragraphs / prose blocks checked | **262** |
| Issues found | **86** |
| Issues corrected | **86** |
| Unresolved | **0** |

## Method

1. Read every end-user chapter, the guide README, and the glossary.  
2. Flag jargon, database/API vocabulary, backend enum spellings, migration names, and long multi-clause sentences.  
3. Rewrite to short A2–B1 sentences; keep product labels users see (SKDM, CN, Official Excel).  
4. Keep technical depth in developer docs / inventories, not in end-user chapters.

## Issue categories (found → corrected)

| Category | Found | Corrected | Unresolved |
|----------|------:|----------:|-----------:|
| Permission codes as primary wording (`cbam:view` / `cbam:configure`) | 18 | 18 | 0 |
| Domain jargon (“binding”, “tenant”, “ops facility”) | 12 | 12 | 0 |
| Backend enums / CAPS status codes as user vocabulary | 14 | 14 | 0 |
| Implementation leak (`clientRequestId`, idempotency, `/health`, row version) | 9 | 9 | 0 |
| Workbook cell / methodology codes (T72, formula enum names) | 6 | 6 | 0 |
| Over-dense or multi-clause sentences | 15 | 15 | 0 |
| Acronym overload without plain expansion (PEE V2, DEA/IEA, SC as primary; SEE/SKDM naming) | 10 | 10 | 0 |
| DB / migration / schema terms in end-user pages | 2 | 2 | 0 |

## Terminology closure (was unresolved)

1. **Official Excel / CBAM SEE** — README and chapter 14 define **CBAM SEE** as the official workbook used for emissions communication; user steps then use **Official Excel**. Glossary records the rule.  
2. **SKDM / CBAM** — first use: *Carbon Border Adjustment Mechanism (CBAM), called SKDM in Turkish*. UI menu label **SKDM** kept where it matches the app.

## Per-page summary

| Page | Issues found | Corrected | Notes |
|------|-------------:|----------:|-------|
| README.md | 6 | 6 | Naming definitions + glossary link |
| glossary.md | 0 | 0 | Added as terminology authority |
| 01-getting-started.md | 5 | 5 | CBAM/SKDM first-use wording |
| 02-organizations-and-installations.md | 5 | 5 | Removed tenant/ops jargon |
| 03-reporting-periods.md | 8 | 8 | “Period” instead of binding jargon |
| 04-product-profiles.md | 4 | 4 | Plain readiness language |
| 05-production.md | 5 | 5 | Removed API/browser implementation asides |
| 06-activities.md | 3 | 3 | Plain activity wording |
| 07-direct-emissions.md | 5 | 5 | Snapshot → saved result |
| 08-indirect-emissions.md | 6 | 6 | Provenance → evidence |
| 09-processes.md | 5 | 5 | Removed T72 cell jargon |
| 10-purchased-inputs-and-precursors.md | 4 | 4 | Hybrid explained as not supported |
| 11-product-results.md | 6 | 6 | Version 2 plain language |
| 12-allocation.md | 4 | 4 | Modern vs generic paths clarified |
| 13-factors-and-calculations.md | 5 | 5 | Formula enum name removed from body |
| 14-report-and-official-excel.md | 6 | 6 | CBAM SEE defined; Official Excel thereafter |
| 15-permissions-statuses-and-errors.md | 7 | 7 | User-facing status words only |
| 16-complete-example-workflow.md | 2 | 2 | Official Excel wording aligned |

## Screenshots + inventories

- Chapters with screenshots embed images with non-empty alt text (chapter 16 is workflow-only).  
- Inventories: [fields.csv](fields.csv), [actions.csv](actions.csv), [inventory-summary.json](inventory-summary.json).  
- LibreOffice macOS evidence: [libreoffice-macos-codesign.md](libreoffice-macos-codesign.md).

## Inventory status

| Item | Status |
|------|--------|
| `fields.csv` | **419** rows; Table+Column filled **419/419** |
| `actions.csv` | **148** rows; HTTP+Endpoint+tables filled **148/148** |
| `inventory-summary.json` | `fields_full_db_traceability: COMPLETE`, `actions_full_traceability: COMPLETE` |
| Remaining guide gaps | **None** for screenshot uniqueness, terminology, or size targets (see coverage report). |
