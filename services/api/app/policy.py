from __future__ import annotations

from .models import Actor, PolicyDecision, RedactionResult, Role


QUOTA_LIMITS_BY_ROLE = {
    Role.employee: 25,
    Role.manager: 50,
    Role.admin: 100,
}


def classify_intent(message: str) -> str:
    lower = message.lower()

    if ("admin access" in lower or "administrator access" in lower) and (
        "production" in lower or "prod" in lower or "database" in lower
    ):
        return "production_admin_access"
    if any(marker in lower for marker in ("read-only", "read only", "readonly", "api access", "iam", "permission", "grant access")):
        return "temporary_read_only_access"
    if "ticket" in lower and any(marker in lower for marker in ("create", "open", "file", "raise")):
        return "create_ticket"
    if "cost" in lower or "spend" in lower or "spike" in lower:
        return "cost_investigation"
    if any(
        marker in lower
        for marker in (
            "timeout",
            "timing out",
            "error",
            "incident",
            "log",
            "not working",
            "broken",
            "failing",
            "failed",
            "outage",
            "down",
            "degraded",
        )
    ):
        return "incident_triage"
    return "support_guidance"


def evaluate_chat_policy(actor: Actor, intent: str) -> PolicyDecision:
    if intent == "production_admin_access":
        return PolicyDecision(
            decision="deny",
            reason="employees_cannot_request_production_admin_access",
            policy_name="tool_authorization",
        )

    if intent == "cost_investigation" and actor.role == Role.employee:
        return PolicyDecision(
            decision="approval_required",
            reason="cost_investigation_requires_manager_or_admin",
            policy_name="tool_authorization",
        )

    return PolicyDecision(
        decision="allow",
        reason=f"{intent}_allowed_for_{actor.role.value}",
        policy_name="chat_request",
    )


def evaluate_tool_policy(role: Role, tool_name: str, action: str) -> PolicyDecision:
    if tool_name == "ticket" and action == "create_ticket":
        return PolicyDecision(
            decision="allow",
            reason="employees_can_create_support_tickets",
            policy_name="tool_authorization",
        )

    if tool_name == "access" and action == "grant_production_admin":
        return PolicyDecision(
            decision="deny",
            reason="production_admin_access_is_not_self_service",
            policy_name="tool_authorization",
        )

    if tool_name == "access" and action == "request_temporary_read_only":
        return PolicyDecision(
            decision="approval_required",
            reason="temporary_production_access_requires_manager_approval",
            policy_name="approval_rules",
        )

    if tool_name == "cost" and role in {Role.manager, Role.admin}:
        return PolicyDecision(
            decision="allow",
            reason="managers_and_admins_can_view_cost_summary",
            policy_name="tool_authorization",
        )

    if tool_name == "cost":
        return PolicyDecision(
            decision="approval_required",
            reason="cost_summary_requires_manager_or_admin",
            policy_name="tool_authorization",
        )

    return PolicyDecision(
        decision="deny",
        reason="tool_action_not_allowed",
        policy_name="tool_authorization",
    )


def evaluate_model_route(redaction: RedactionResult, intent: str) -> PolicyDecision:
    if redaction.secrets_detected:
        return PolicyDecision(
            decision="allow",
            reason="secrets_redacted_before_local_model_route",
            policy_name="model_routing",
        )

    if redaction.pii_detected:
        return PolicyDecision(
            decision="allow",
            reason="pii_redacted_before_local_model_route",
            policy_name="model_routing",
        )

    if intent in {"incident_triage", "production_admin_access", "temporary_read_only_access"}:
        return PolicyDecision(
            decision="allow",
            reason="internal_operational_context_uses_local_route",
            policy_name="model_routing",
        )

    return PolicyDecision(
        decision="allow",
        reason="low_sensitivity_request_can_use_bedrock_route",
        policy_name="model_routing",
        metadata={"provider": "bedrock"},
    )


def evaluate_quota_policy(actor: Actor, current_count: int) -> PolicyDecision:
    limit = QUOTA_LIMITS_BY_ROLE[actor.role]
    if current_count >= limit:
        return PolicyDecision(
            decision="deny",
            reason="daily_role_quota_exceeded",
            policy_name="quota",
            metadata={"limit": limit, "current_count": current_count, "window": "daily"},
        )

    return PolicyDecision(
        decision="allow",
        reason="daily_role_quota_available",
        policy_name="quota",
        metadata={"limit": limit, "current_count": current_count, "window": "daily"},
    )
