from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .incident_context import lookup_incident_context
from .models import ApprovalRequest, IncidentContext, PolicyDecision, Role, ToolCall
from .store import actor_from


class TicketAdapter(Protocol):
    """Creates governed work items in an external ticketing system."""

    name: str

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        ...


@dataclass(frozen=True)
class LocalTicketAdapter:
    name: str = "local_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        status = "allowed" if policy.decision == "allow" else "blocked"
        result = {}
        if status == "allowed":
            result = {
                "ticket_id": "TCK-4821",
                "title": title,
                "team": team,
                "severity": severity,
                "status": "open",
                "adapter": self.name,
            }
        return ToolCall(name="ticket.create", status=status, policy=policy, result=result)


@dataclass(frozen=True)
class JiraTicketAdapter:
    base_url: str
    project_key: str
    name: str = "jira_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        raise NotImplementedError("jira_ticket_adapter_requires_configured_api_client")


@dataclass(frozen=True)
class ServiceNowTicketAdapter:
    instance_url: str
    assignment_group: str
    name: str = "servicenow_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        raise NotImplementedError("servicenow_ticket_adapter_requires_configured_api_client")


class IncidentContextAdapter(Protocol):
    """Loads read-only incident evidence for AI-assisted triage."""

    name: str

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        ...

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        ...


@dataclass(frozen=True)
class LocalFixtureIncidentAdapter:
    name: str = "local_fixture_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        return lookup_incident_context(incident_id, query)

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        return ToolCall(
            name="incident.context",
            status="allowed",
            policy=PolicyDecision(
                decision="allow",
                reason="read_only_incident_context_allowed",
                policy_name="incident_context",
                metadata={"adapter": self.name},
            ),
            result=context.model_dump(),
        )


@dataclass(frozen=True)
class CloudWatchIncidentAdapter:
    log_group: str
    region: str
    name: str = "cloudwatch_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        raise NotImplementedError("cloudwatch_incident_adapter_requires_logs_client")

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        raise NotImplementedError("cloudwatch_incident_adapter_requires_logs_client")


@dataclass(frozen=True)
class DatadogIncidentAdapter:
    site: str
    index: str
    name: str = "datadog_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        raise NotImplementedError("datadog_incident_adapter_requires_logs_client")

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        raise NotImplementedError("datadog_incident_adapter_requires_logs_client")


class AccessRequestAdapter(Protocol):
    """Routes production access changes through an approval provider."""

    name: str

    def request_read_only_access(
        self,
        request_id: str,
        user_id: str,
        role: Role,
        team: str,
        reason: str,
        policy: PolicyDecision,
    ) -> tuple[ToolCall, ApprovalRequest]:
        ...


@dataclass(frozen=True)
class LocalApprovalAdapter:
    name: str = "local_approval_adapter"

    def request_read_only_access(
        self,
        request_id: str,
        user_id: str,
        role: Role,
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
                "adapter": self.name,
            },
        )
        return tool_call, approval


@dataclass(frozen=True)
class OktaGroupRequestAdapter:
    org_url: str
    group_id: str
    name: str = "okta_group_request_adapter"

    def request_read_only_access(
        self,
        request_id: str,
        user_id: str,
        role: Role,
        team: str,
        reason: str,
        policy: PolicyDecision,
    ) -> tuple[ToolCall, ApprovalRequest]:
        raise NotImplementedError("okta_group_request_adapter_requires_workflow_client")


@dataclass(frozen=True)
class IAMIdentityCenterAdapter:
    instance_arn: str
    permission_set_arn: str
    name: str = "iam_identity_center_adapter"

    def request_read_only_access(
        self,
        request_id: str,
        user_id: str,
        role: Role,
        team: str,
        reason: str,
        policy: PolicyDecision,
    ) -> tuple[ToolCall, ApprovalRequest]:
        raise NotImplementedError("iam_identity_center_adapter_requires_sso_admin_client")
