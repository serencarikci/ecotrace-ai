# Agent Security

## Principles

1. Allowlisted tools only (`READ_ONLY_TOOLS` + `CONTROLLED_WRITE_TOOLS`).
2. Organization scoping and RBAC before every tool call.
3. Prompt injection marker checks; retrieved documents treated as untrusted.
4. Secret redaction in tool inputs/outputs and audit metadata.
5. Write actions require `agent_action_requests` approval + separate execute.
6. High-risk actions require organization_admin / system_admin.
7. No SQL, shell, arbitrary HTTP, or secret-access tools.
8. MCP-compatible catalog is internal and disabled for public exposure by default.

## Approval statuses

`pending` → `approved` / `rejected` / `expired` → `executed` / `failed`

Expired requests cannot execute. All decisions are audited.
