from __future__ import annotations

from pathlib import Path

import pytest

from ecotrace.modules.cbam.architecture_boundary import (
    APPLICATION_FORBIDDEN_INFRASTRUCTURE_PREFIXES,
    CBAM_API_ROUTER_PATH,
    CBAM_PACKAGE_ROOT,
    CBAM_SCAN_ROOTS,
    FORBIDDEN_IMPORT_PREFIXES,
    FORBIDDEN_MODULE_LEAF_NAMES,
    find_forbidden_imports_in_source,
    find_forbidden_imports_in_tree,
    format_findings,
    iter_cbam_scan_paths,
)


def test_forbidden_list_covers_contexts_and_engines() -> None:
    assert set(FORBIDDEN_MODULE_LEAF_NAMES) == {
        "carbon_accounting",
        "carbon_inventory",
        "lifecycle_assessment",
        "product_carbon_footprint",
    }
    joined = " ".join(FORBIDDEN_IMPORT_PREFIXES)
    assert "carbon_accounting" in joined
    assert "lifecycle_assessment" in joined
    engine_findings = find_forbidden_imports_in_source(
        "from ecotrace.modules.lifecycle_assessment.application.calculation_engine "
        "import run_lca_calculation\n",
        filename="engine.py",
    )
    assert len(engine_findings) == 1
    assert "lifecycle_assessment" in engine_findings[0].matched_forbidden


def test_scan_roots_include_module_package_and_api_router() -> None:
    assert CBAM_PACKAGE_ROOT in CBAM_SCAN_ROOTS
    assert CBAM_API_ROUTER_PATH in CBAM_SCAN_ROOTS
    paths = iter_cbam_scan_paths()
    assert any(path == CBAM_API_ROUTER_PATH.resolve() for path in paths)
    assert any(
        CBAM_PACKAGE_ROOT.resolve() in path.parents or path == CBAM_PACKAGE_ROOT.resolve()
        for path in paths
    )
    assert CBAM_API_ROUTER_PATH.is_file()


def test_cbam_scan_roots_have_no_forbidden_imports() -> None:
    findings = find_forbidden_imports_in_tree()
    assert findings == [], "CBAM sources must not import forbidden contexts:\n" + "\n".join(
        format_findings(findings)
    )


def test_api_router_is_included_in_positive_scan() -> None:
    findings = find_forbidden_imports_in_tree(roots=(CBAM_API_ROUTER_PATH,))
    assert findings == []
    assert "module-status" in CBAM_API_ROUTER_PATH.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("source", "expected_fragment"),
    [
        ("import ecotrace.modules.carbon_inventory\n", "carbon_inventory"),
        ("from ecotrace.modules.carbon_inventory import SomeModel\n", "carbon_inventory"),
        ("from ecotrace.modules import carbon_inventory\n", "carbon_inventory"),
        ("from ecotrace.modules import lifecycle_assessment\n", "lifecycle_assessment"),
        ("from ecotrace.modules import carbon_inventory as inventory\n", "carbon_inventory"),
        (
            "from ecotrace.modules.lifecycle_assessment.application.calculation_engine "
            "import run_lca_calculation\n",
            "lifecycle_assessment",
        ),
        (
            "from ecotrace.modules.carbon_accounting.application import calculation_math\n",
            "carbon_accounting",
        ),
        (
            "from ecotrace.modules.product_carbon_footprint.application import pcf_service\n",
            "product_carbon_footprint",
        ),
    ],
)
def test_detects_absolute_and_parent_package_forms(source: str, expected_fragment: str) -> None:
    findings = find_forbidden_imports_in_source(source, filename="sample.py")
    assert len(findings) >= 1
    text = findings[0].format()
    assert expected_fragment in text
    assert "sample.py:" in text
    assert findings[0].lineno >= 1
    assert findings[0].detected_import
    assert findings[0].matched_forbidden


@pytest.mark.parametrize(
    "source",
    [
        "from .. import carbon_inventory\n",
        "from ..carbon_inventory import SomeModel\n",
        "from ...modules import product_carbon_footprint\n",
        "from ...modules import carbon_inventory as inventory\n",
    ],
)
def test_detects_relative_escape_forms(tmp_path: Path, source: str) -> None:
    src_root = tmp_path / "src"
    probe = src_root / "ecotrace" / "modules" / "cbam" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text(source, encoding="utf-8")
    findings = find_forbidden_imports_in_tree(roots=(probe,), src_root=src_root)
    assert len(findings) >= 1
    text = findings[0].format()
    assert str(probe) in text
    assert findings[0].lineno >= 1
    assert any(leaf in findings[0].matched_forbidden for leaf in FORBIDDEN_MODULE_LEAF_NAMES)


def test_controlled_negative_forbidden_import_in_router_scan_root(tmp_path: Path) -> None:
    src_root = tmp_path / "src"
    fake_router = src_root / "ecotrace" / "api" / "v1" / "cbam.py"
    fake_router.parent.mkdir(parents=True)
    fake_router.write_text(
        "from ecotrace.modules.lifecycle_assessment.infrastructure import models\n",
        encoding="utf-8",
    )
    findings = find_forbidden_imports_in_tree(roots=(fake_router,), src_root=src_root)
    assert len(findings) == 1
    assert findings[0].matched_forbidden.endswith("lifecycle_assessment")
    assert "lifecycle_assessment" in findings[0].detected_import
    assert find_forbidden_imports_in_tree(roots=(CBAM_API_ROUTER_PATH,)) == []


def test_architecture_ignores_comments_strings_and_docstrings() -> None:
    source = '''
"""Example mentioning ecotrace.modules.lifecycle_assessment in a docstring."""
# from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonInventory
x = "ecotrace.modules.product_carbon_footprint"
y = 'from ecotrace.modules import carbon_accounting'
'''
    assert find_forbidden_imports_in_source(source, filename="safe.py") == []


def test_architecture_allows_stdlib_shared_and_identity_imports() -> None:
    source = """
import uuid
from pathlib import Path
from typing import Final
from ecotrace.shared.application.org_access import require_org_roles
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
"""
    assert find_forbidden_imports_in_source(source, filename="ok.py") == []


def test_architecture_allows_internal_cbam_relative_imports(tmp_path: Path) -> None:
    src_root = tmp_path / "src"
    probe = src_root / "ecotrace" / "modules" / "cbam" / "application" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text(
        "from .. import MODULE_CODE\n"
        "from . import permissions\n"
        "from ..architecture_boundary import CBAM_SCAN_ROOTS\n",
        encoding="utf-8",
    )
    findings = find_forbidden_imports_in_tree(roots=(probe,), src_root=src_root)
    assert findings == []


def test_similarly_named_safe_modules_are_not_flagged() -> None:
    source = """
import ecotrace.modules.carbon_preferences
from ecotrace.modules import reporting_periods
from ecotrace.modules.cbam.application import permissions
"""
    assert find_forbidden_imports_in_source(source, filename="safe_names.py") == []


def test_application_layer_forbids_cross_module_orm_imports(tmp_path: Path) -> None:
    src_root = tmp_path / "src"
    probe = src_root / "ecotrace" / "modules" / "cbam" / "application" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text(
        "from ecotrace.modules.facilities.infrastructure.models import Facility\n",
        encoding="utf-8",
    )
    findings = find_forbidden_imports_in_tree(roots=(probe,), src_root=src_root)
    assert len(findings) == 1
    assert "facilities.infrastructure" in findings[0].matched_forbidden


def test_application_layer_allows_reference_application_services(tmp_path: Path) -> None:
    src_root = tmp_path / "src"
    probe = src_root / "ecotrace" / "modules" / "cbam" / "application" / "probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text(
        "from ecotrace.modules.facilities.application.facility_service import get_facility\n"
        "from ecotrace.modules.reporting_periods.application.period_service import get_period\n"
        "from ecotrace.modules.products.application.product_service import get_product\n",
        encoding="utf-8",
    )
    assert find_forbidden_imports_in_tree(roots=(probe,), src_root=src_root) == []


def test_infrastructure_adapters_may_call_foreign_application_services() -> None:
    assert APPLICATION_FORBIDDEN_INFRASTRUCTURE_PREFIXES
    findings = find_forbidden_imports_in_tree(
        roots=(CBAM_PACKAGE_ROOT / "infrastructure",)
    )
    assert findings == [], "\n".join(format_findings(findings))
