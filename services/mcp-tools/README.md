# MCP Tool Server

This service exposes the AegisDesk governed tools through a real Model Context Protocol server using the Python MCP SDK.

Implemented tools:

- `create_ticket`
- `request_temporary_read_only_access`
- `lookup_cost_summary`
- `search_runbook`

The hosted Lambda API uses an in-process adapter for these controlled actions so it does not need to spawn a subprocess. This MCP server proves protocol interoperability for local reviewers and future agent clients.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

The default transport is stdio, which is the expected mode for local MCP clients.

## Use With Codex

From the repository root:

```bash
codex mcp add aegisdesk-cloudops -- "$(pwd)/scripts/run-mcp-tools.sh"
```

Then restart Codex or open a new session. See [Codex MCP Integration](../../docs/integrations/codex-mcp.md) for the smoke test and operating boundary.
