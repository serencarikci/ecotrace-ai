# LibreOffice macOS `__pycache__` / codesign — evidence (2026-09-15)

## Root cause

Document Foundation’s macOS LibreOffice package **ships sealed** `__pycache__` directories inside:

`/Applications/LibreOffice.app/Contents/Frameworks/LibreOfficePython.framework/...`

`codesign -d` on that framework reports sealed resources including those bytecode files (~3452 sealed files). Therefore:

1. **Deleting** Frameworks `__pycache__` breaks deep verification (`file missing`).
2. **Extra / rewritten** `.pyc` beside the sealed set also breaks deep verification (`sealed resource … invalid`).
3. EcoTrace Official Excel uses **`soffice` headless convert** with an isolated `UserInstallation` profile under a temp directory. It does **not** import `LibreOfficePython`.

## What this repository does

- Resolves soffice explicitly (`/Applications/LibreOffice.app/Contents/MacOS/soffice` or `LIBREOFFICE_SOFFICE_PATH`).
- Uses a unique writable UserInstallation profile per recalc.
- Sets `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPYCACHEPREFIX` under the temp root, and `HOME`/`TMPDIR` to the temp root so any incidental Python bytecode stays **outside** the app bundle.
- Does **not** add speculative in-bundle cleanup.

## External / host evidence

- After a clean `brew reinstall --cask libreoffice`, deep codesign passes and **42** `__pycache__` dirs exist again (sealed).
- Two consecutive Official SEE pytest runs (unit + acceptance) leave **0** new `.pyc` under `/Applications/LibreOffice.app`.
- Project grep finds **no** imports of `LibreOfficePython` / Frameworks paths.

If deep codesign fails again on a developer Mac, restore the sealed app with a LibreOffice reinstall — do **not** delete sealed Frameworks `__pycache__` as a routine step.

## Recurrence prevention

| Control | Status |
|---------|--------|
| Isolated LO profile + temp dirs | Yes (`recalc.py`) |
| No writes into signed bundle from EcoTrace | Proven (0 new pyc after suites) |
| Manual `__pycache__` wipe as permanent fix | **Rejected** (removes sealed resources) |
| Speculative cleanup inside `/Applications` | **Not added** |
