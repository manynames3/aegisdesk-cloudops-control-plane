from __future__ import annotations

from .adapters import (
    CloudWatchIncidentAdapter,
    JiraTicketAdapter,
    LocalApprovalAdapter,
    LocalFixtureIncidentAdapter,
    IncidentContextAdapter,
    LocalTicketAdapter,
    ServiceNowTicketAdapter,
    TicketAdapter,
    UnavailableIncidentAdapter,
    UnavailableTicketAdapter,
)
from .models import ApprovalRequest, IncidentContext, PolicyDecision, Role, ToolCall
from .settings import get_settings


def _configured_ticket_adapter() -> TicketAdapter:
    settings = get_settings()
    if settings.ticket_adapter == "local":
        return LocalTicketAdapter()
    if settings.ticket_adapter == "jira":
        required = [
            settings.jira_base_url,
            settings.jira_email,
            settings.jira_api_token,
            settings.jira_project_key,
        ]
        if all(required):
            return JiraTicketAdapter(
                base_url=str(settings.jira_base_url),
                email=str(settings.jira_email),
                api_token=str(settings.jira_api_token),
                project_key=str(settings.jira_project_key),
                issue_type=settings.jira_issue_type,
                timeout_seconds=settings.jira_timeout_seconds,
            )
        return UnavailableTicketAdapter(reason="jira_adapter_missing_required_configuration", system="jira")
    if settings.ticket_adapter == "servicenow":
        required = [
            settings.servicenow_instance_url,
            settings.servicenow_username,
            settings.servicenow_password,
        ]
        if all(required):
            return ServiceNowTicketAdapter(
                instance_url=str(settings.servicenow_instance_url),
                username=str(settings.servicenow_username),
                password=str(settings.servicenow_password),
                assignment_group=settings.servicenow_assignment_group,
                table=settings.servicenow_table,
                timeout_seconds=settings.servicenow_timeout_seconds,
            )
        return UnavailableTicketAdapter(reason="servicenow_adapter_missing_required_configuration", system="servicenow")
    return UnavailableTicketAdapter(
        reason=f"unsupported_ticket_adapter:{settings.ticket_adapter}",
        system=settings.ticket_adapter,
    )


def _configured_incident_context_adapter() -> IncidentContextAdapter:
    settings = get_settings()
    if settings.incident_context_adapter == "local_fixture":
        return LocalFixtureIncidentAdapter()
    if settings.incident_context_adapter == "cloudwatch":
        if settings.cloudwatch_log_group:
            return CloudWatchIncidentAdapter(
                log_group=settings.cloudwatch_log_group,
                region=settings.cloudwatch_logs_region,
                lookback_minutes=settings.cloudwatch_query_lookback_minutes,
                query_limit=settings.cloudwatch_query_limit,
                poll_attempts=settings.cloudwatch_query_poll_attempts,
                poll_interval_seconds=settings.cloudwatch_query_poll_interval_seconds,
            )
        return UnavailableIncidentAdapter(
            reason="cloudwatch_adapter_missing_required_log_group",
            system="cloudwatch",
        )
    return UnavailableIncidentAdapter(
        reason=f"unsupported_incident_context_adapter:{settings.incident_context_adapter}",
        system=settings.incident_context_adapter,
    )


ticket_adapter = _configured_ticket_adapter()
incident_context_adapter = _configured_incident_context_adapter()
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


def lookup_incident_context(incident_id: str | None, query: str) -> IncidentContext:
    return incident_context_adapter.lookup_context(incident_id, query)


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
