from __future__ import annotations

from .adapters import LocalApprovalAdapter, LocalFixtureIncidentAdapter, LocalTicketAdapter
from .models import ApprovalRequest, IncidentContext, PolicyDecision, Role, ToolCall


ticket_adapter = LocalTicketAdapter()
incident_context_adapter = LocalFixtureIncidentAdapter()
access_request_adapter = LocalApprovalAdapter()


def create_ticket(policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
    return ticket_adapter.create_ticket(policy, title, team, severity)


def lookup_cost_summary(policy: PolicyDecision, summary: dict | None = None) -> ToolCall:
    status = "allowed" if policy.decision == "allow" else "approval_required"

    result = {}
    if status == "allowed":
        result = summary or {
            "period": "last_7_days",
            "total_usd": 184.72,
            "largest_driver": "cloud model experimentation",
            "recommendation": "route low-value repeated prompts to local model or cache approved answers",
            "estimated_savings_usd": 37.4,
        }

    return ToolCall(name="cost.summary", status=status, policy=policy, result=result)


def lookup_incident_context_tool(context: IncidentContext) -> ToolCall:
    return incident_context_adapter.to_tool_call(context)


def request_read_only_access(
    request_id: str,
    user_id: str,
    role: Role,
    team: str,
    reason: str,
    policy: PolicyDecision,
) -> tuple[ToolCall, ApprovalRequest]:
    return access_request_adapter.request_read_only_access(request_id, user_id, role, team, reason, policy)
