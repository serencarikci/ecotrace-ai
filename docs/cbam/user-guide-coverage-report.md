# User Guide Coverage & Verification Report

**Status: COMPLETE**  
**Screenshot coverage (main required set): 30/30 files present · 30 distinct hashes among required evidence set (history / completed-download / unbalanced / stale all unique)**  
**Commit policy:** documentation-focused; LibreOffice recalc env hardening only; no commit/push in this task

## 1. Documentation files

### User guide
- `docs/cbam/user-guide/01-getting-started.md` … `16-complete-example-workflow.md`
- `docs/cbam/user-guide/glossary.md`
- `docs/cbam/user-guide/README.md`
- `docs/cbam/user-guide/assets/` (real PNG captures; optimized)
- `docs/cbam/user-guide/inventories/` (field, action, API, table inventories + A2–B1 + LibreOffice notes)

### Technical
- `docs/cbam/technical-ui-data-traceability.md`
- `docs/cbam/data-relationships-and-lifecycle.md`
- `docs/cbam/user-guide-coverage-report.md` (this file)

### Corrected / deprecated authority
- `docs/cbam/frontend-feature-map.md` — deprecated as route authority; lists implemented routes only
- `docs/cbam/mvp-limitations.md` — Official Excel generation implemented; Docker API may lack LibreOffice

## 2. Local review environment (verified this pass)

| Service | Result |
|---------|--------|
| PostgreSQL (local review DB on `127.0.0.1:5433`) | Up; 53 `cbam_*` tables; review bindings present |
| FastAPI local (`:8010`) | Health 200; used for screenshots via Playwright API rewrite (no `environment.ts` port commit) |
| Angular (`ng serve` `:4201`) | Reachable; SKDM after org select via SPA navigation |
| LibreOffice | Local `soffice` (`LibreOffice 26.8.0.3`); deep codesign OK after cask restore; Official SEE suite run twice |
| Docker `ecotrace-api:8001` | Not modified in this task |

Credentials are **not** written into documentation.

## 3. Screens / screenshots

**Reachable screens discovered / documented: 6 routes + 12 period tabs = 18 / 18.**

Main screenshots required: **30** · present: **30**.

State captures: empty, incomplete, ready, history, view-only, locked, validation error, failed execution, unbalanced, stale, completed-download — with **unique** hashes for history vs completed-download and unbalanced vs stale.

PNG totals: **40** files · **~3.8 MB** after optimization · **0** images &gt; 500 KB.

SHA-256: **40** images · **35** unique hashes · **5** intentional alias groups · **0** accidental duplicates.

## 4. Field / action inventories (exact)

| Metric | Count |
|--------|------:|
| Visible fields discovered | **419** |
| Fields mapped / documented | **419** |
| Fields unexplained | **0** |
| User actions discovered / mapped / documented | **148** |
| Actions unexplained | **0** |

Authoritative: `inventories/fields.csv`, `actions.csv`, `inventory-summary.json`.

## 5. API reconciliation (exact)

| Metric | Count |
|--------|------:|
| Frontend HTTP methods | **99** |
| Unique frontend endpoint keys | **99** |
| CBAM backend OpenAPI operations | **155** |
| FRONTEND_USED | **99** |
| BACKEND_ONLY_VALID (justified) | **56** |
| UNMAPPED | **0** |

## 6. Tables

| Metric | Count |
|--------|------:|
| Active `cbam_*` tables | **53** |
| Documented in `table-dictionary.md` | **53** |
| Legacy CBAM tables | **0** |

Migration head: `0032_cbam_prec_audit`.

## 7. Validation scans (docs)

Relative links, screenshot existence/reference, orphans, duplicate hashes, secret/credential/path scans, A2–B1 terminology: see this pass validation logs under `.tmp-validation/doc-pass4/`.

## 8. Application regression (this pass)

| Check | Result |
|-------|--------|
| Official SEE + LibreOffice (full unit+acceptance) | **24 passed** twice (`PYTEST1_EXIT:0`, `PYTEST2_EXIT:0`; 0 skipped) |
| macOS codesign `--deep` | **OK** before and after both full runs; **0** new `.pyc` in app bundle |
| Architecture tests | **24 passed** |
| Router import | `router_ok 155` |
| Ruff (`recalc.py`) | All checks passed |
| Mypy (`recalc.py`) | exit 0 |
| FE focused PEE/OSE specs | **33 SUCCESS** |
| FE CBAM Karma | **233 SUCCESS** |
| FE lint (CBAM) | All files pass linting |
| FE `tsc` app + spec | exit 0 |
| FE production build | **BUILD_EXIT:0** → `apps/web/dist/web` |

## 9. Completeness verdict

| Deliverable | Complete? |
|-------------|-----------|
| User Guide status | **COMPLETE** |
| Main screenshots | **Yes** (30/30; required evidence hashes distinct) |
| Field-level technical traceability | **Yes** (419/419) |
| Action-level traceability | **Yes** (148/148) |
| API categories | **Yes** |
| A2–B1 language | **Yes** (86/86 corrected; **0** unresolved) |

## 10. Gap closure table (all 11)

| # | Gap | Required action | Evidence | Status |
|---|-----|-----------------|----------|--------|
| 1 | Dedicated Official Excel completed/downloadable screenshot | Distinct completed/download UI | `14e-…` unique vs `14c`/`17-state-history`; Download enabled | **CLOSED** |
| 2 | View-only period screenshot | Capture view-only | `16-view-only-period.png` unique; ch.15 | **CLOSED** |
| 3 | Locked-period screenshot | Capture locked | `17-state-locked.png` unique; ch.15 | **CLOSED** |
| 4 | Distinct Purchased Precursors | Unique vs Purchased Inputs | `10b` unique vs `10` | **CLOSED** |
| 5 | Distinct DEA | Unique vs Allocation | `12b` unique vs `12` | **CLOSED** |
| 6 | Distinct Official readiness | Unique vs Report | `14b` unique vs `14` | **CLOSED** |
| 7 | State shots: validation / unbalanced / stale / failed | Distinct captures | `17-state-stale` ≠ unbalanced; banner + Out of date | **CLOSED** |
| 8 | Field UI→DB rows | 414→419 mapped | `fields.csv` 419/419 | **CLOSED** |
| 9 | Action HTTP/table rows | 148 mapped | `actions.csv` 148/148 | **CLOSED** |
| 10 | Embed screenshots + alt | Chapters embed + alts | README gallery + ch.15 states | **CLOSED** |
| 11 | Re-run FE/BE suite | Paste exact counts | §8 + validation logs | **CLOSED** |

## 11. Safe to commit / deploy?

- **Safe to commit?** Documentation + `recalc.py` env isolation are reviewable. Do **not** commit `.tmp-validation/` or credentials.
- **Safe to deploy for external review?** **No public deploy in this task.** Docker API may still lack LibreOffice; not a public regulatory claim.

## 12. Official Excel / stale capture notes (this pass)

- Generated real Official Excel run: `generationStatus=COMPLETED`, `formulaParityStatus=PASSED`, artifact present; UI shows **Download current official Excel**.
- Stale created via supported production-record PATCH; backend `currentIsStale=true` with `PRODUCTION_RECORDS_CHANGED` (and related allocation-stale reasons); UI shows Out of date + stale banner; not unbalanced.
- Review production quantity restored; DEA/IEA/PEE re-executed; Official Excel readiness returned Ready.
