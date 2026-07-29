from __future__ import annotations
from typing import Any
from ecotrace.core.intelligence_constants import CONTROLLED_WRITE_TOOLS, READ_ONLY_TOOLS

def _tool(code: str, description: str, *, write: bool=False, input_schema: dict[str, Any] | None=None) -> dict[str, Any]:
    return {'name': code, 'description': description, 'inputSchema': input_schema or {'type': 'object', 'properties': {'organizationId': {'type': 'string', 'format': 'uuid'}, 'query': {'type': 'string'}}, 'required': ['organizationId']}, 'annotations': {'readOnlyHint': not write, 'destructiveHint': False, 'openWorldHint': False}, 'authorization': 'organization_scoped', 'approvalRequired': write}

def build_mcp_catalog() -> list[dict[str, Any]]:
    tools = []
    for code in sorted(READ_ONLY_TOOLS):
        tools.append(_tool(code, code.replace('_', ' '), write=False))
    for code in sorted(CONTROLLED_WRITE_TOOLS):
        tools.append(_tool(code, code.replace('_', ' '), write=True))
    return tools

def mcp_adapter_notes() -> dict[str, Any]:
    return {'defaultExposure': 'disabled', 'adapterGuidance': 'An external MCP adapter should authenticate as an EcoTrace service account, pass organization scope on every call, enforce the allowlist below, apply timeouts, and never expose SQL/shell/arbitrary HTTP tools.', 'tools': build_mcp_catalog()}
