from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = {
    "create_ticket",
    "request_temporary_read_only_access",
    "lookup_cost_summary",
    "search_runbook",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the AegisDesk MCP tool server.")
    parser.add_argument(
        "--command",
        default=str(ROOT / "scripts" / "run-mcp-tools.sh"),
        help="Command used to launch the MCP server.",
    )
    parser.add_argument(
        "--server-python",
        default=None,
        help="Run services/mcp-tools/server.py with this Python executable instead of the launcher.",
    )
    return parser.parse_args()


async def smoke() -> None:
    args = parse_args()
    if args.server_python:
        params = StdioServerParameters(
            command=args.server_python,
            args=[str(ROOT / "services" / "mcp-tools" / "server.py")],
            cwd=str(ROOT),
        )
    else:
        params = StdioServerParameters(command=args.command, cwd=str(ROOT))

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = {tool.name for tool in tools.tools}
            missing = EXPECTED_TOOLS - tool_names
            if missing:
                raise AssertionError(f"missing MCP tools: {sorted(missing)}")

            ticket = await session.call_tool(
                "create_ticket",
                {"title": "VPN outage", "team": "CloudOps", "severity": "high"},
            )
            if ticket.isError:
                raise AssertionError("create_ticket returned an MCP error")

            payload = json.loads(ticket.content[0].text)
            if payload.get("status") != "open" or not str(payload.get("ticket_id", "")).startswith("TCK-"):
                raise AssertionError(f"unexpected ticket payload: {payload}")

            print("MCP smoke passed:", ", ".join(sorted(tool_names)))


if __name__ == "__main__":
    try:
        asyncio.run(smoke())
    except Exception as exc:
        print(f"MCP smoke failed: {exc}", file=sys.stderr)
        raise
