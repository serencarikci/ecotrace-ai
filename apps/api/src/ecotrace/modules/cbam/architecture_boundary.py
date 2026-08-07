"""CBAM anti-corruption import boundary.

Scans CBAM Python sources for direct imports from forbidden bounded contexts
and calculation engines. Used by architecture tests; not a runtime gate.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

# Explicit forbidden import prefixes (modules and calculation engines).
FORBIDDEN_IMPORT_PREFIXES: Final[tuple[str, ...]] = (
    "ecotrace.modules.carbon_accounting",
    "ecotrace.modules.carbon_inventory",
    "ecotrace.modules.lifecycle_assessment",
    "ecotrace.modules.product_carbon_footprint",
)

CBAM_PACKAGE_ROOT: Final[Path] = Path(__file__).resolve().parent


def _module_matches_forbidden(module: str | None) -> str | None:
    if not module:
        return None
    for prefix in FORBIDDEN_IMPORT_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return prefix
    return None


def find_forbidden_imports_in_source(source: str, *, filename: str = "<string>") -> list[str]:
    """Return human-readable violations found via AST (ignores comments/docstrings)."""
    tree = ast.parse(source, filename=filename)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = _module_matches_forbidden(alias.name)
                if hit:
                    violations.append(
                        f"{filename}:{node.lineno}: import {alias.name} (forbidden: {hit})"
                    )
        elif isinstance(node, ast.ImportFrom):
            hit = _module_matches_forbidden(node.module)
            if hit:
                violations.append(
                    f"{filename}:{node.lineno}: from {node.module} import ... (forbidden: {hit})"
                )
    return violations


def iter_cbam_python_files(root: Path | None = None) -> list[Path]:
    base = root if root is not None else CBAM_PACKAGE_ROOT
    return sorted(path for path in base.rglob("*.py") if path.is_file())


def find_forbidden_imports_in_tree(root: Path | None = None) -> list[str]:
    violations: list[str] = []
    for path in iter_cbam_python_files(root):
        source = path.read_text(encoding="utf-8")
        violations.extend(find_forbidden_imports_in_source(source, filename=str(path)))
    return violations
