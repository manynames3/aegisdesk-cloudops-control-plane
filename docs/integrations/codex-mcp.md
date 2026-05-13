# Codex MCP Integration

AegisDesk exposes its governed CloudOps tools through a local Model Context Protocol server so Codex and other MCP-aware agent clients can call the same operational actions through a standard interface.

## What This Enables

Codex can call AegisDesk tools directly for agent workflows such as:

- create a CloudOps ticket
- request temporary read-only access
- look up a cost summary
- search the runbook corpus

The hosted API still uses in-process tool adapters for Lambda reliability. The MCP server is the external agent interface.

## Register With Codex

From the repository root:

```bash
codex mcp add aegisdesk-cloudops -- "$(pwd)/scripts/run-mcp-tools.sh"
```

Then restart Codex or open a new Codex session so the new MCP server is loaded.

Verify the registration:

```bash
codex mcp list
codex mcp get aegisdesk-cloudops
```

## Smoke Test The MCP Server

The smoke test launches the MCP server over stdio, lists tools, and calls `create_ticket`.

```bash
npm run smoke:mcp
```

Or run the wrapper directly:

```bash
scripts/smoke-mcp-tools.sh
```

The launcher creates `services/mcp-tools/.venv` on first run and writes setup logs to stderr so stdout remains reserved for MCP protocol messages.

## Available Tools

| Tool | Purpose |
| --- | --- |
| `create_ticket` | Create a controlled support ticket payload for governed CloudOps workflows |
| `request_temporary_read_only_access` | Create a temporary read-only access approval request payload |
| `lookup_cost_summary` | Return a cost summary payload for cost-governance workflows |
| `search_runbook` | Search the local runbook fixture used for incident triage |

## Operating Boundary

This MCP server is safe by default:

- It does not grant real production access.
- It does not mutate AWS infrastructure.
- It returns structured payloads that match the AegisDesk governed tool model.
- Real enterprise deployments should replace these local adapters with ServiceNow/Jira, IAM Identity Center, CloudWatch Logs, and Cost Explorer adapters behind the same policy boundary.
