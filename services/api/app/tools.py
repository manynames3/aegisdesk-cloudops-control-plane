from __future__ import annotations

from .models import ApprovalRequest, IncidentContext, PolicyDecision, ToolCall
from .store import actor_from


def create_ticket(policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
    status = "allowed" if policy.decision == "allow" else "blocked"

    result = {}
    if status == "allowed":
        result = {
            "ticket_id": "TCK-4821",
            "title": title,
            "team": team,
            "severity": severity,
            "status": "open",
        }

    return ToolCall(name="ticket.create", status=status, policy=policy, result=result)


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
    return ToolCall(
        name="incident.context",
        status="allowed",
        policy=PolicyDecision(
            decision="allow",
            reason="read_only_incident_context_allowed",
            policy_name="incident_context",
        ),
        result=context.model_dump(),
    )


def request_read_only_access(
    request_id: str,
    user_id: str,
    role,
    team: str,
    reason: str,
    policy: PolicyDecision,
) -> tuple[ToolCall, ApprovalRequest]:
    approval = ApprovalRequest(
        request_id=request_id,
        requester=actor_from(user_id, role, team),
        resource="prod-payments-db",
        permission="read_only",
        reason=reason,
        risk_level="high",
        policy_reason=policy.reason,
    )
    tool_call = ToolCall(
        name="access.request_temporary_read_only",
        status="approval_required",
        policy=policy,
        result={
            "approval_id": approval.approval_id,
            "resource": approval.resource,
            "permission": approval.permission,
            "expires_in": "2h",
        },
    )
    return tool_call, approval
