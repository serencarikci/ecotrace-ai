from __future__ import annotations

from pathlib import Path

import pytest

from ecotrace.modules.cbam.architecture_boundary import (
    FORBIDDEN_IMPORT_PREFIXES,
    find_forbidden_imports_in_source,
    find_forbidden_imports_in_tree,
)


def test_forbidden_import_list_covers_carbon_lca_pcf_engines() -> None:
    joined = " ".join(FORBIDDEN_IMPORT_PREFIXES)
    assert "carbon_accounting" in joined
    assert "carbon_inventory" in joined
    assert "lifecycle_assessment" in joined
    assert "product_carbon_footprint" in joined


def test_cbam_module_has_no_forbidden_imports() -> None:
    violations = find_forbidden_imports_in_tree()
    assert violations == [], "CBAM module must not import forbidden contexts:\n" + "\n".join(
        violations
    )


def test_architecture_detects_forbidden_import_in_controlled_sample(tmp_path: Path) -> None:
    sample = tmp_path / "controlled_forbidden_import.py"
    sample.write_text(
        "from ecotrace.modules.lifecycle_assessment.application.calculation_engine "
        "import run_lca_calculation\n"
        "from ecotrace.modules.carbon_accounting.application import calculation_math\n"
        "import ecotrace.modules.carbon_inventory.infrastructure.models as inv\n"
        "from ecotrace.modules.product_carbon_footprint.application "
        "import pcf_service\n",
        encoding="utf-8",
    )
    violations = find_forbidden_imports_in_tree(tmp_path)
    assert len(violations) >= 4
    assert any("lifecycle_assessment" in v for v in violations)
    assert any("carbon_accounting" in v for v in violations)
    assert any("carbon_inventory" in v for v in violations)
    assert any("product_carbon_footprint" in v for v in violations)


def test_architecture_ignores_forbidden_names_in_comments_and_docstrings() -> None:
    source = '''
"""Example mentioning ecotrace.modules.lifecycle_assessment in a docstring."""
# from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonInventory
x = "ecotrace.modules.product_carbon_footprint"
'''
    assert find_forbidden_imports_in_source(source, filename="safe.py") == []


def test_architecture_allows_identity_and_org_imports() -> None:
    source = """
from ecotrace.shared.application.org_access import require_org_roles
from ecotrace.modules.identity.infrastructure.models import User
"""
    assert find_forbidden_imports_in_source(source, filename="ok.py") == []


@pytest.mark.parametrize(
    "module",
    [
        "ecotrace.modules.lifecycle_assessment",
        "ecotrace.modules.lifecycle_assessment.application.calculation_engine",
        "ecotrace.modules.carbon_accounting.application.calculation_math",
    ],
)
def test_forbidden_prefix_matching(module: str) -> None:
    source = f"import {module}\n"
    violations = find_forbidden_imports_in_source(source, filename="sample.py")
    assert len(violations) == 1
