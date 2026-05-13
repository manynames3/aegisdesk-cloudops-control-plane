from __future__ import annotations

from typing import Literal
from uuid import uuid4

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("aegisdesk-cloudops-tools")


@mcp.tool()
def create_ticket(title: str, team: str, severity: Literal["low", "medium", "high"] = "medium") -> dict:
    """Create a local support ticket payload for the governed CloudOps workflow."""
    return {
        "ticket_id": f"TCK-{uuid4().hex[:6].upper()}",
        "title": title,
        "team": team,
        "severity": severity,
        "status": "open",
    }


@mcp.tool()
def request_temporary_read_only_access(user_id: str, team: str, resource: str, reason: str) -> dict:
    """Create an approval request for temporary read-only production access."""
    return {
        "approval_id": f"APR-{uuid4().hex[:8].upper()}",
        "requester": user_id,
        "team": team,
        "resource": resource,
        "permission": "read_only",
        "status": "pending",
        "reason": reason,
        "expires_in": "2h",
    }


@mcp.tool()
def lookup_cost_summary(period: str = "last_7_days") -> dict:
    """Return a local cost summary payload for the governed CloudOps workflow."""
    return {
        "period": period,
        "total_usd": 184.72,
        "largest_driver": "cloud model experimentation",
        "recommendation": "route repeated low-value prompts locally or cache approved answers",
        "estimated_savings_usd": 37.4,
    }


@mcp.tool()
def search_runbook(query: str) -> dict:
    """Search a small local runbook corpus for incident triage."""
    return {
        "query": query,
        "matches": [
            {
                "title": "Checkout timeout triage",
                "summary": "Check recent deploys, upstream payment latency, database pool saturation, and error budgets.",
            }
        ],
    }


if __name__ == "__main__":
    mcp.run()
