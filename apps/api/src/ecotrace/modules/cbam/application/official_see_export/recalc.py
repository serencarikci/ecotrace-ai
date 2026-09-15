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

# Local macOS acceptance path (never required in Linux containers).
_MACOS_SOFFICE = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
_LINUX_SOFFICE_CANDIDATES = (
    Path("/usr/bin/soffice"),
    Path("/usr/lib/libreoffice/program/soffice"),
    Path("/opt/libreoffice26.8/program/soffice"),
    Path("/opt/libreoffice25.8/program/soffice"),
)


class RecalculationEngineUnavailable(BusinessRuleError):  # noqa: N818
    def __init__(self, message: str = "LibreOffice recalculation engine is unavailable.") -> None:
        super().__init__(
            message,
            code=CODE_RECALCULATION_ENGINE_UNAVAILABLE,
            details=[{"code": CODE_RECALCULATION_ENGINE_UNAVAILABLE}],
        )


def resolve_soffice_path() -> Path | None:
    """Resolve soffice: env → Linux paths → PATH → macOS app (local only)."""
    env_path = os.environ.get("LIBREOFFICE_SOFFICE_PATH")
    ordered: list[Path] = []
    if env_path:
        ordered.append(Path(env_path))
    ordered.extend(_LINUX_SOFFICE_CANDIDATES)
    which = shutil.which("soffice")
    if which:
        ordered.append(Path(which))
    ordered.append(_MACOS_SOFFICE)

    seen: set[str] = set()
    for candidate in ordered:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
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
    pattern = re.compile(
        r"(<f\b[^>]*(?:/>|>.*?</f>))(\s*)(<v(?:\s[^>]*)?>.*?</v>|<v\s*/>)",
        re.DOTALL,
    )

    with zipfile.ZipFile(xlsx_path, "r") as zin:
        patches: dict[str, bytes] = {}
        for name in zin.namelist():
            if not (name.startswith("xl/worksheets/sheet") and name.endswith(".xml")):
                continue
            original = zin.read(name).decode("utf-8")
            new_xml, n = pattern.subn(r"\1", original)
            if n:
                stripped += n
                patches[name] = new_xml.encode("utf-8")
        if not patches:
            return 0
        tmp = xlsx_path.with_suffix(".strip-tmp.xlsx")
        with zipfile.ZipFile(tmp, "w") as zout:
            for info in zin.infolist():
                data = patches.get(info.filename, zin.read(info.filename))
                zout.writestr(info, data)
    tmp.replace(xlsx_path)
    return stripped


def recalculate_workbook(source_xlsx: Path, *, timeout_seconds: int | None = None) -> Path:
    """Recalculate ``source_xlsx`` via LibreOffice headless in a temp directory.

    Uses a unique UserInstallation profile per run. Returns the path to the
    recalculated workbook (same basename under temp outdir).
    Caller owns cleanup of the returned path's parent temp dir via ``cleanup_recalc_dir``.
    """
    soffice = resolve_soffice_path()
    if soffice is None:
        raise RecalculationEngineUnavailable()

    if not source_xlsx.is_file():
        raise RecalculationEngineUnavailable("Workbook for recalculation is missing.")

    if timeout_seconds is None:
        raw = os.environ.get("LIBREOFFICE_RECALC_TIMEOUT_SECONDS", "300")
        try:
            timeout_seconds = max(30, int(raw))
        except ValueError:
            timeout_seconds = 300

    tmp_root = Path(tempfile.mkdtemp(prefix="ecotrace-see-recalc-"))
    profile_dir = tmp_root / f"lo-profile-{uuid.uuid4().hex}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    proc: subprocess.Popen[bytes] | None = None
    try:
        work_copy = tmp_root / source_xlsx.name
        shutil.copy2(source_xlsx, work_copy)
        strip_cached_formula_values(work_copy)
        out_dir = tmp_root / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        profile_uri = profile_dir.resolve().as_uri()
        # Keep all writable state outside the signed/installed LibreOffice tree.
        pycache_dir = tmp_root / "pycache"
        pycache_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPYCACHEPREFIX"] = str(pycache_dir)
        env["HOME"] = str(tmp_root)
        env["TMPDIR"] = str(tmp_root)
        convert_cmd = [
            str(soffice),
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nodefault",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "xlsx",
            "--outdir",
            str(out_dir),
            str(work_copy),
        ]
        try:
            proc = subprocess.Popen(
                convert_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(tmp_root),
                env=env,
                start_new_session=True,
            )
            try:
                _stdout, stderr = proc.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                _kill_process_tree(proc)
                shutil.rmtree(tmp_root, ignore_errors=True)
                raise RecalculationEngineUnavailable(
                    f"LibreOffice recalculation timed out after {timeout_seconds}s"
                ) from exc
        except OSError as exc:
            _kill_process_tree(proc)
            shutil.rmtree(tmp_root, ignore_errors=True)
            raise RecalculationEngineUnavailable(
                f"LibreOffice recalculation failed: {exc}"
            ) from exc

        if proc.returncode != 0:
            detail = (stderr or b"").decode("utf-8", errors="replace")[:500]
            shutil.rmtree(tmp_root, ignore_errors=True)
            raise RecalculationEngineUnavailable(
                f"LibreOffice recalculation exited with an error. {detail}".strip()
            )

        produced = out_dir / source_xlsx.name
        if not produced.is_file():
            candidates = list(out_dir.glob("*.xlsx"))
            if not candidates:
                shutil.rmtree(tmp_root, ignore_errors=True)
                raise RecalculationEngineUnavailable(
                    "LibreOffice did not produce a recalculated workbook."
                )
            produced = candidates[0]

        time.sleep(0.05)
        return produced
    except RecalculationEngineUnavailable:
        raise
    except Exception as exc:
        _kill_process_tree(proc)
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise RecalculationEngineUnavailable(f"LibreOffice recalculation failed: {exc}") from exc


def cleanup_recalc_dir(path: Path | None) -> None:
    if path is None:
        return
    root = path.parent.parent if path.parent.name == "out" else path.parent
    shutil.rmtree(root, ignore_errors=True)
