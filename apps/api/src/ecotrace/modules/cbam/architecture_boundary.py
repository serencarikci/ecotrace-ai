from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.util import resolve_name
from pathlib import Path
from typing import Final

FORBIDDEN_MODULE_LEAF_NAMES: Final[tuple[str, ...]] = (
    "carbon_accounting",
    "carbon_inventory",
    "lifecycle_assessment",
    "product_carbon_footprint",
)

FORBIDDEN_IMPORT_PREFIXES: Final[tuple[str, ...]] = tuple(
    f"ecotrace.modules.{name}" for name in FORBIDDEN_MODULE_LEAF_NAMES
)

APPLICATION_FORBIDDEN_INFRASTRUCTURE_PREFIXES: Final[tuple[str, ...]] = (
    "ecotrace.modules.facilities.infrastructure",
    "ecotrace.modules.reporting_periods.infrastructure",
    "ecotrace.modules.products.infrastructure",
)

_SRC_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
CBAM_PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent
CBAM_APPLICATION_ROOT: Final[Path] = CBAM_PACKAGE_ROOT / "application"
CBAM_DOMAIN_ROOT: Final[Path] = CBAM_PACKAGE_ROOT / "domain"
CBAM_API_ROUTER_PATH: Final[Path] = _SRC_ROOT / "ecotrace" / "api" / "v1" / "cbam.py"

CBAM_SCAN_ROOTS: Final[tuple[Path, ...]] = (
    CBAM_PACKAGE_ROOT,
    CBAM_API_ROUTER_PATH,
)


@dataclass(frozen=True, slots=True)
class ForbiddenImportFinding:
    file: str
    lineno: int
    detected_import: str
    matched_forbidden: str

    def format(self) -> str:
        return (
            f"{self.file}:{self.lineno}: {self.detected_import} "
            f"(forbidden: {self.matched_forbidden})"
        )


def _module_matches_forbidden(module: str | None) -> str | None:
    if not module:
        return None
    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return prefix
    return None


def _module_matches_application_infrastructure_ban(module: str | None) -> str | None:
    if not module:
        return None
    for prefix in APPLICATION_FORBIDDEN_INFRASTRUCTURE_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return prefix
    return None


def _is_under_application_or_domain(path: Path) -> bool:
    parts = path.resolve().parts
    for index, part in enumerate(parts):
        if part != "cbam" or index + 1 >= len(parts):
            continue
        if parts[index + 1] in ("application", "domain"):
            return True
    return False


def _file_to_module(path: Path, *, src_root: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(src_root.resolve())
    except ValueError:
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _package_for_module(module_name: str, *, is_package_init: bool) -> str:
    if is_package_init:
        return module_name
    if "." not in module_name:
        return ""
    return module_name.rsplit(".", 1)[0]


def _candidate_modules_from_import_from(
    node: ast.ImportFrom,
    *,
    file_path: Path,
    src_root: Path,
) -> list[str]:
    module_name = _file_to_module(file_path, src_root=src_root)
    is_init = file_path.name == "__init__.py"
    package = _package_for_module(module_name, is_package_init=is_init) if module_name else ""

    if node.level == 0:
        base = node.module or ""
        candidates: list[str] = []
        if base:
            candidates.append(base)
        for alias in node.names:
            if alias.name == "*":
                continue
            candidates.append(f"{base}.{alias.name}" if base else alias.name)
        return candidates

    if not package:
        return []

    dots = "." * node.level
    relative = f"{dots}{node.module}" if node.module else dots
    try:
        absolute_base = resolve_name(relative, package)
    except (ImportError, ValueError):
        return []

    candidates = [absolute_base]
    if node.module is None:
        for alias in node.names:
            if alias.name == "*":
                continue
            candidates.append(f"{absolute_base}.{alias.name}" if absolute_base else alias.name)
    else:
        for alias in node.names:
            if alias.name == "*":
                continue
            candidates.append(f"{absolute_base}.{alias.name}")
    return candidates


def find_forbidden_imports_in_source(
    source: str,
    *,
    filename: str = "<string>",
    file_path: Path | None = None,
    src_root: Path | None = None,
    enforce_application_infrastructure_ban: bool | None = None,
) -> list[ForbiddenImportFinding]:
    tree = ast.parse(source, filename=filename)
    root = src_root if src_root is not None else _SRC_ROOT
    path = file_path if file_path is not None else Path(filename)
    check_app_infra = (
        enforce_application_infrastructure_ban
        if enforce_application_infrastructure_ban is not None
        else _is_under_application_or_domain(path)
    )
    findings: list[ForbiddenImportFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = _module_matches_forbidden(alias.name)
                if not hit and check_app_infra:
                    hit = _module_matches_application_infrastructure_ban(alias.name)
                if hit:
                    findings.append(
                        ForbiddenImportFinding(
                            file=filename,
                            lineno=node.lineno,
                            detected_import=f"import {alias.name}",
                            matched_forbidden=hit,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            for candidate in _candidate_modules_from_import_from(
                node, file_path=path, src_root=root
            ):
                hit = _module_matches_forbidden(candidate)
                if not hit and check_app_infra:
                    hit = _module_matches_application_infrastructure_ban(candidate)
                if hit:
                    findings.append(
                        ForbiddenImportFinding(
                            file=filename,
                            lineno=node.lineno,
                            detected_import=f"from-import -> {candidate}",
                            matched_forbidden=hit,
                        )
                    )
                    break
    return findings


def iter_python_files_in_root(root: Path) -> list[Path]:
    if root.is_file() and root.suffix == ".py":
        return [root.resolve()]
    if not root.is_dir():
        return []
    return sorted(path.resolve() for path in root.rglob("*.py") if path.is_file())


def iter_cbam_scan_paths(
    roots: Iterable[Path] | None = None,
) -> list[Path]:
    selected = tuple(roots) if roots is not None else CBAM_SCAN_ROOTS
    paths: list[Path] = []
    seen: set[Path] = set()
    for root in selected:
        for path in iter_python_files_in_root(root):
            if path not in seen:
                seen.add(path)
                paths.append(path)
    return paths


def find_forbidden_imports_in_tree(
    roots: Iterable[Path] | None = None,
    *,
    src_root: Path | None = None,
) -> list[ForbiddenImportFinding]:
    findings: list[ForbiddenImportFinding] = []
    root = src_root if src_root is not None else _SRC_ROOT
    for path in iter_cbam_scan_paths(roots):
        source = path.read_text(encoding="utf-8")
        findings.extend(
            find_forbidden_imports_in_source(
                source,
                filename=str(path),
                file_path=path,
                src_root=root,
            )
        )
    return findings


def format_findings(findings: Iterable[ForbiddenImportFinding]) -> list[str]:
    return [finding.format() for finding in findings]
