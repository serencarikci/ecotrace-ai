"""Authoritative FastAPI route inventory checks (stability, not frozen path counts).

FastAPI 0.140+ keeps included routers as ``_IncludedRouter`` wrappers, so
``len(app.routes)`` is NOT the application surface area. Prefer OpenAPI path
counts or a recursive APIRoute walk.

Do not lock CI to a historical total path count unless that number is an
intentionally reviewed API contract.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.routing import APIRoute, APIRouter

from ecotrace.main import create_app

# Required CBAM surface (prefix presence — not a frozen endpoint census).
REQUIRED_CBAM_PREFIXES: tuple[str, ...] = (
    "/api/v1/cbam/organizations",
    "/api/v1/cbam/organizations/{organization_id}/installations",
    "/api/v1/cbam/organizations/{organization_id}/reporting-period-bindings",
    "/api/v1/cbam/organizations/{organization_id}/product-profile-versions",
)


@dataclass(frozen=True)
class RouteInventory:
    top_level_route_objects: int
    apiroute_objects: int
    unique_paths: int
    path_method_pairs: int
    cbam_unique_paths: int
    official_see_unique_paths: int
    openapi_unique_paths: int
    openapi_cbam_paths: int
    openapi_official_see_paths: int
    openapi_path_method_pairs: int
    duplicate_path_method_ops: int


def _walk_apiroutes(router: APIRouter, prefix: str = "") -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    for route in router.routes:
        if isinstance(route, APIRoute):
            methods = tuple(sorted(m for m in (route.methods or set()) if m not in {"HEAD"}))
            found.append((prefix + route.path, methods))
        elif type(route).__name__ == "_IncludedRouter":
            include_context = route.include_context
            nested_prefix = prefix + (getattr(include_context, "prefix", None) or "")
            found.extend(_walk_apiroutes(route.original_router, nested_prefix))
        elif isinstance(route, APIRouter):
            found.extend(_walk_apiroutes(route, prefix))
    return found


def collect_apiroutes(app: FastAPI) -> list[tuple[str, tuple[str, ...]]]:
    found: list[tuple[str, tuple[str, ...]]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = tuple(sorted(m for m in (route.methods or set()) if m not in {"HEAD"}))
            found.append((route.path, methods))
        elif type(route).__name__ == "_IncludedRouter":
            include_context = route.include_context
            prefix = getattr(include_context, "prefix", None) or ""
            found.extend(_walk_apiroutes(route.original_router, prefix))
    return found


def inventory_routes(app: FastAPI) -> RouteInventory:
    walked = collect_apiroutes(app)
    paths = {path for path, _ in walked}
    pairs = sum(len(methods) for _, methods in walked)
    op_keys: list[tuple[str, str]] = []
    for path, methods in walked:
        for method in methods:
            op_keys.append((path, method))
    duplicates = sum(1 for _, count in Counter(op_keys).items() if count > 1)

    openapi_paths = app.openapi().get("paths") or {}
    openapi_pairs = 0
    openapi_ops: list[tuple[str, str]] = []
    for path, ops in openapi_paths.items():
        for method in ops:
            if method in {"get", "post", "put", "patch", "delete", "options"}:
                openapi_pairs += 1
                openapi_ops.append((path, method.upper()))
    openapi_duplicates = sum(1 for _, count in Counter(openapi_ops).items() if count > 1)

    return RouteInventory(
        top_level_route_objects=len(app.routes),
        apiroute_objects=len(walked),
        unique_paths=len(paths),
        path_method_pairs=pairs,
        cbam_unique_paths=sum(1 for path in paths if "/cbam" in path),
        official_see_unique_paths=sum(1 for path in paths if "official-see-export" in path),
        openapi_unique_paths=len(openapi_paths),
        openapi_cbam_paths=sum(1 for path in openapi_paths if "/cbam" in path),
        openapi_official_see_paths=sum(
            1 for path in openapi_paths if "official-see-export" in path
        ),
        openapi_path_method_pairs=openapi_pairs,
        duplicate_path_method_ops=duplicates + openapi_duplicates,
    )


def test_create_app_route_inventory_is_stable_and_complete() -> None:
    """Fresh and repeated create_app() must expose the same route set."""
    first = inventory_routes(create_app())
    second = inventory_routes(create_app())

    # Soft floors — catch catastrophic router loss without freezing a census.
    assert first.openapi_unique_paths >= 100
    assert first.openapi_cbam_paths >= 50
    assert first.openapi_official_see_paths >= 4
    assert first.unique_paths == first.openapi_unique_paths
    assert first.path_method_pairs == first.openapi_path_method_pairs
    assert first.cbam_unique_paths == first.openapi_cbam_paths
    assert first.official_see_unique_paths == first.openapi_official_see_paths
    assert first.duplicate_path_method_ops == 0

    # FastAPI 0.140+ keeps routers as wrappers; top-level len(app.routes) is small.
    assert first.top_level_route_objects < 20
    assert first.apiroute_objects == first.path_method_pairs

    assert second.openapi_unique_paths == first.openapi_unique_paths
    assert second.openapi_cbam_paths == first.openapi_cbam_paths
    assert second.openapi_official_see_paths == first.openapi_official_see_paths
    assert second.path_method_pairs == first.path_method_pairs


def test_required_cbam_and_official_see_routes_exist() -> None:
    app = create_app()
    paths = set(app.openapi().get("paths") or {})
    for prefix in REQUIRED_CBAM_PREFIXES:
        assert any(
            path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "{")
            for path in paths
        ), prefix
    official = [path for path in paths if "official-see-export" in path]
    assert official, "Official SEE export routes missing from OpenAPI"
    assert any("readiness" in path for path in official)
    assert any("/runs" in path for path in official)


def test_openapi_generation_succeeds() -> None:
    schema = create_app().openapi()
    assert schema.get("openapi")
    assert schema.get("paths")
    assert schema.get("info", {}).get("title")


def test_module_level_app_matches_create_app_inventory() -> None:
    from ecotrace.main import app as module_app

    created = inventory_routes(create_app())
    module = inventory_routes(module_app)
    assert module.openapi_unique_paths == created.openapi_unique_paths
    assert module.openapi_cbam_paths == created.openapi_cbam_paths
    assert module.openapi_official_see_paths == created.openapi_official_see_paths
