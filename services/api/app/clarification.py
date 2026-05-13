from __future__ import annotations

import re
from typing import Any

from .models import Actor, ChatRequest, ClarificationResult


SERVICE_PATTERNS = (
    "checkout",
    "payment",
    "payments",
    "vpn",
    "api",
    "database",
    "db",
    "lambda",
    "cloudwatch",
    "bedrock",
    "s3",
    "ec2",
    "eks",
    "auth",
    "login",
    "billing",
    "worker",
    "queue",
    "redis",
    "postgres",
    "endpoint",
)


def assess_clarification(intent: str, request: ChatRequest, actor: Actor) -> ClarificationResult:
    text = request.message.lower()

    if intent == "incident_triage":
        missing = []
        if not _has_service_or_system(text):
            missing.append("affected service or system")
        if not _has_incident_evidence(text, request.context):
            missing.append("incident ID, alert, log snippet, or metric")
        if not missing:
            return _complete("Incident request includes enough context for read-only triage.")
        return ClarificationResult(
            status="partial_guidance",
            risk_level="medium",
            missing_fields=missing,
            questions=[
                "Which service or system is affected?",
                "Do you have an incident ID, alert name, log snippet, metric, or timestamp?",
            ],
            can_answer_partially=True,
            blocks_tool_call=False,
            reason="incident_triage_can_provide_safe_first_steps_but_needs_context_for_log_lookup",
        )

    if intent == "create_ticket":
        requirements = {
            "affected service or system": _has_service_or_system(text),
            "severity or priority": _has_severity(text),
            "business or user impact": _has_impact(text),
        }
        missing = _missing(requirements)
        if not missing:
            return _complete("Ticket request includes service, severity, and impact.")
        return ClarificationResult(
            status="blocked_pending_details",
            risk_level="medium",
            missing_fields=missing,
            questions=[
                "Which service or system should the ticket be opened for?",
                "What severity or priority should be assigned?",
                "Who is affected and what is the business or user impact?",
            ],
            blocks_tool_call=True,
            reason="ticket_creation_requires_service_severity_and_impact",
        )

    if intent in {"production_admin_access", "temporary_read_only_access"}:
        requirements = {
            "resource": _has_resource(text),
            "environment": _has_environment(text),
            "business reason or incident reference": _has_reason(text) or _has_incident_reference(text, request.context),
            "duration": _has_duration(text),
            "permission scope": _has_permission_scope(text),
        }
        missing = _missing(requirements)
        if not missing:
            return _complete("Access request includes scope, target, reason, and duration.", risk_level="high")
        return ClarificationResult(
            status="blocked_pending_details",
            risk_level="high",
            missing_fields=missing,
            questions=[
                "Which exact resource and environment does this apply to?",
                "What minimum permission scope is needed, and can read-only access satisfy it?",
                "What business reason, incident ID, duration, and approver should be recorded?",
            ],
            blocks_tool_call=True,
            reason="access_workflows_require_scope_reason_duration_and_resource_before_approval",
        )

    if intent == "cost_investigation":
        requirements = {
            "team, service, or account scope": _has_cost_scope(text, actor),
            "time window": _has_time_window(text),
        }
        missing = _missing(requirements)
        if not missing:
            return _complete("Cost request includes account/team scope and a time window.")
        return ClarificationResult(
            status="blocked_pending_details",
            risk_level="medium",
            missing_fields=missing,
            questions=[
                "Which team, service, AWS account, or environment should be investigated?",
                "What time window should be compared?",
            ],
            blocks_tool_call=True,
            reason="cost_investigation_requires_scope_and_time_window",
        )

    return _complete("General support request can be answered without additional required fields.", risk_level="low")


def build_clarification_answer(intent: str, clarification: ClarificationResult, policy_decision: str) -> str:
    questions = " ".join(f"{index}. {question}" for index, question in enumerate(clarification.questions, start=1))
    missing = ", ".join(clarification.missing_fields)

    if clarification.status == "partial_guidance" and intent == "incident_triage":
        return (
            "I can give safe first-step triage, but I need more context before querying incident logs. "
            "Start by checking recent deploys, error-rate and latency dashboards, upstream dependency health, "
            "database connection pool saturation, and any active alerts. "
            f"Missing details: {missing}. {questions}"
        )

    if intent in {"production_admin_access", "temporary_read_only_access"}:
        return (
            "I cannot open or route an access request until the required control-plane details are recorded. "
            "For production access, use the smallest scoped permission, prefer temporary read-only access, "
            "include an incident or business reason, and set an expiration. "
            f"Missing details: {missing}. {questions}"
        )

    if intent == "create_ticket":
        return (
            "I need a few ticket fields before creating a record so the queue does not receive an ambiguous issue. "
            f"Missing details: {missing}. {questions}"
        )

    if intent == "cost_investigation":
        return (
            "I need cost scope before querying cost data. This prevents broad or expensive investigations from running "
            f"without ownership context. Missing details: {missing}. {questions}"
        )

    if policy_decision == "deny":
        return "This request was denied by policy. Provide a safer scoped request if you need an approved alternative."

    return f"I need more context before taking action. Missing details: {missing}. {questions}"


def _complete(reason: str, risk_level: str = "medium") -> ClarificationResult:
    return ClarificationResult(status="complete", risk_level=risk_level, reason=reason)


def _missing(requirements: dict[str, bool]) -> list[str]:
    return [field for field, is_present in requirements.items() if not is_present]


def _has_service_or_system(text: str) -> bool:
    return any(re.search(rf"\b{re.escape(pattern)}\b", text) for pattern in SERVICE_PATTERNS)


def _has_incident_evidence(text: str, context: dict[str, Any]) -> bool:
    return _has_incident_reference(text, context) or any(
        marker in text
        for marker in (
            "trace",
            "stack trace",
            "alert",
            "metric",
            "p95",
            "p99",
            "latency",
            "error log",
            "log",
            "timestamp",
            "5xx",
            "timeout",
            "timing out",
        )
    )


def _has_incident_reference(text: str, context: dict[str, Any]) -> bool:
    if context.get("incident_id"):
        return True
    return bool(re.search(r"\binc[-_ ]?\d{3,}\b", text, re.IGNORECASE))


def _has_severity(text: str) -> bool:
    return bool(re.search(r"\b(sev[- ]?[0-4]|p[0-4]|priority|severity|critical|high|medium|low)\b", text))


def _has_impact(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "affected",
            "impact",
            "customers",
            "users",
            "employees",
            "cannot",
            "unable",
            "outage",
            "down",
            "degraded",
            "revenue",
            "checkout",
            "payment",
        )
    )


def _has_resource(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "database",
            "db",
            "api",
            "iam",
            "role",
            "policy",
            "bucket",
            "lambda",
            "cluster",
            "prod-",
            "arn:",
        )
    )


def _has_environment(text: str) -> bool:
    return bool(re.search(r"\b(prod|production|staging|stage|dev|test|qa|uat|us-east-1|us-west-2)\b", text))


def _has_reason(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "because",
            "reason",
            "business reason",
            "to inspect",
            "investigate",
            "debug",
            "during active incident",
            "incident",
        )
    )


def _has_duration(text: str) -> bool:
    return bool(re.search(r"\b\d+\s*(minute|minutes|min|mins|hour|hours|hr|hrs|day|days)\b", text)) or any(
        marker in text for marker in ("until", "expires", "duration")
    )


def _has_permission_scope(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "read-only",
            "read only",
            "readonly",
            "admin",
            "write",
            "api access",
            "iam",
            "permission",
            "grant",
            "least privilege",
        )
    )


def _has_cost_scope(text: str, actor: Actor) -> bool:
    if actor.team:
        return True
    return any(
        marker in text
        for marker in (
            "team",
            "service",
            "account",
            "environment",
            "bedrock",
            "ai",
            "cloud",
            "aws",
            "lambda",
            "s3",
            "ec2",
            "eks",
        )
    )


def _has_time_window(text: str) -> bool:
    return bool(re.search(r"\b(last|past|this|previous)\s+\d*\s*(day|days|week|weeks|month|months)\b", text)) or any(
        marker in text for marker in ("today", "yesterday", "this week", "last week", "this month", "last month")
    )
