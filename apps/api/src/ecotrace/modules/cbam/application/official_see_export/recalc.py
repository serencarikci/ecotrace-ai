"""LibreOffice headless recalculation adapter (fail-closed when missing)."""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_RECALCULATION_ENGINE_UNAVAILABLE,
)

# Prefer explicit macOS app path (Phase 12A+ acceptance environment).
_EXPLICIT_SOFFICE = Path('/Applications/LibreOffice.app/Contents/MacOS/soffice')


class RecalculationEngineUnavailable(BusinessRuleError):  # noqa: N818
    def __init__(self, message: str = 'LibreOffice recalculation engine is unavailable.') -> None:
        super().__init__(
            message,
            code=CODE_RECALCULATION_ENGINE_UNAVAILABLE,
            details=[{'code': CODE_RECALCULATION_ENGINE_UNAVAILABLE}],
        )


def resolve_soffice_path() -> Path | None:
    """Resolve soffice binary: explicit path first, then env, then PATH, then common Linux paths."""
    for candidate in (
        _EXPLICIT_SOFFICE,
        Path(os.environ['LIBREOFFICE_SOFFICE_PATH'])
        if os.environ.get('LIBREOFFICE_SOFFICE_PATH')
        else None,
    ):
        if candidate is None:
            continue
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    which = shutil.which('soffice')
    if which:
        return Path(which)

    for candidate in (
        Path('/usr/bin/soffice'),
        Path('/usr/lib/libreoffice/program/soffice'),
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def soffice_available() -> bool:
    return resolve_soffice_path() is not None


def _kill_process_tree(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        with contextlib.suppress(ProcessLookupError, OSError):
            proc.kill()
    with contextlib.suppress(Exception):
        proc.wait(timeout=5)

def strip_cached_formula_values(xlsx_path: Path) -> int:
    """Remove cached ``<v>`` results from formula cells so LO must recalculate.

    LibreOffice ``--convert-to`` often reuses stale cached values; clearing them
    forces a real recalc pass after EcoTrace INPUT patches.
    """
    stripped = 0
    # Match <f>...</f><v>...</v> or <f .../><v>...</v> (and empty v)
    pattern = re.compile(
        r'(<f\b[^>]*(?:/>|>.*?</f>))(\s*)(<v(?:\s[^>]*)?>.*?</v>|<v\s*/>)',
        re.DOTALL,
    )

    with zipfile.ZipFile(xlsx_path, 'r') as zin:
        patches: dict[str, bytes] = {}
        for name in zin.namelist():
            if not (
                name.startswith('xl/worksheets/sheet') and name.endswith('.xml')
            ):
                continue
            original = zin.read(name).decode('utf-8')
            new_xml, n = pattern.subn(r'\1', original)
            if n:
                stripped += n
                patches[name] = new_xml.encode('utf-8')
        if not patches:
            return 0
        tmp = xlsx_path.with_suffix('.strip-tmp.xlsx')
        with zipfile.ZipFile(tmp, 'w') as zout:
            for info in zin.infolist():
                data = patches.get(info.filename, zin.read(info.filename))
                zout.writestr(info, data)
    tmp.replace(xlsx_path)
    return stripped


def recalculate_workbook(source_xlsx: Path, *, timeout_seconds: int = 300) -> Path:
    """Recalculate ``source_xlsx`` via LibreOffice headless in a temp directory.

    Uses a unique UserInstallation profile per run. Returns the path to the
    recalculated workbook (same basename under temp outdir).
    Caller owns cleanup of the returned path's parent temp dir via ``cleanup_recalc_dir``.
    """
    soffice = resolve_soffice_path()
    if soffice is None:
        raise RecalculationEngineUnavailable()

    if not source_xlsx.is_file():
        raise RecalculationEngineUnavailable('Workbook for recalculation is missing.')

    tmp_root = Path(tempfile.mkdtemp(prefix='ecotrace-see-recalc-'))
    profile_dir = tmp_root / f'lo-profile-{uuid.uuid4().hex}'
    profile_dir.mkdir(parents=True, exist_ok=True)
    proc: subprocess.Popen[bytes] | None = None
    try:
        work_copy = tmp_root / source_xlsx.name
        shutil.copy2(source_xlsx, work_copy)
        strip_cached_formula_values(work_copy)
        out_dir = tmp_root / 'out'
        out_dir.mkdir(parents=True, exist_ok=True)

        # file:/// URI for UserInstallation (required by LO on macOS/Linux).
        profile_uri = profile_dir.resolve().as_uri()
        convert_cmd = [
            str(soffice),
            '--headless',
            '--norestore',
            '--nolockcheck',
            '--nodefault',
            f'-env:UserInstallation={profile_uri}',
            '--convert-to',
            'xlsx',
            '--outdir',
            str(out_dir),
            str(work_copy),
        ]
        try:
            proc = subprocess.Popen(
                convert_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(tmp_root),
                start_new_session=True,
            )
            try:
                _stdout, stderr = proc.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                _kill_process_tree(proc)
                shutil.rmtree(tmp_root, ignore_errors=True)
                raise RecalculationEngineUnavailable(
                    f'LibreOffice recalculation timed out after {timeout_seconds}s'
                ) from exc
        except OSError as exc:
            _kill_process_tree(proc)
            shutil.rmtree(tmp_root, ignore_errors=True)
            raise RecalculationEngineUnavailable(
                f'LibreOffice recalculation failed: {exc}'
            ) from exc

        if proc.returncode != 0:
            detail = (stderr or b'').decode('utf-8', errors='replace')[:500]
            shutil.rmtree(tmp_root, ignore_errors=True)
            raise RecalculationEngineUnavailable(
                f'LibreOffice recalculation exited with an error. {detail}'.strip()
            )

        produced = out_dir / source_xlsx.name
        if not produced.is_file():
            candidates = list(out_dir.glob('*.xlsx'))
            if not candidates:
                shutil.rmtree(tmp_root, ignore_errors=True)
                raise RecalculationEngineUnavailable(
                    'LibreOffice did not produce a recalculated workbook.'
                )
            produced = candidates[0]

        # Brief settle — LO sometimes still holds profile locks briefly.
        time.sleep(0.05)
        return produced
    except RecalculationEngineUnavailable:
        raise
    except Exception as exc:
        _kill_process_tree(proc)
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise RecalculationEngineUnavailable(
            f'LibreOffice recalculation failed: {exc}'
        ) from exc


def cleanup_recalc_dir(path: Path | None) -> None:
    if path is None:
        return
    # produced = tmp_root/out/file.xlsx → remove tmp_root
    root = path.parent.parent if path.parent.name == 'out' else path.parent
    shutil.rmtree(root, ignore_errors=True)
