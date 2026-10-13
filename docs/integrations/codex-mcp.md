# Codex MCP Integration

AegisDesk includes a local Model Context Protocol server for Codex and other MCP-aware clients to inspect CloudOps-shaped fixture payloads over stdio. It is interoperability tooling, not an authenticated production interface to the hosted incident workflow.

## What This Enables

Agent clients can inspect these simulated workflows:

- return a locally generated ticket payload
- return an access approval request payload without granting access
- return a fixed example cost summary, not AWS billing data
- search a small runbook fixture

The hosted API uses separate in-process adapters for Lambda reliability. It does not invoke this MCP server, and MCP calls do not inherit the API's identity, policy, audit, or approval controls.

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
| `create_ticket` | Return a local ticket payload; no Jira/ServiceNow call |
| `request_temporary_read_only_access` | Return an approval-shaped payload; no durable approval or access grant |
| `lookup_cost_summary` | Return fixed fixture values; no Cost Explorer query |
| `search_runbook` | Search the local runbook fixture used for incident triage |

## Operating Boundary

This MCP server has a deliberately limited local boundary:

- It does not grant real production access.
- It does not mutate AWS infrastructure.
- It returns structured fixtures, not confirmed external outcomes.
- A production MCP transport would need verified identity, team scoping, OPA checks, exact-action approval, durable dispatch, and audit integration. Replacing fixtures with live adapters alone would not provide these controls.
