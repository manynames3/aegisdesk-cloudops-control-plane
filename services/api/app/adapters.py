from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import httpx

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
class UnavailableTicketAdapter:
    reason: str
    system: str
    name: str = "unavailable_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        return ToolCall(
            name="ticket.create",
            status="blocked",
            policy=policy,
            result={
                "adapter": self.name,
                "system": self.system,
                "status": "failed",
                "error": self.reason,
                "title": title,
                "team": team,
                "severity": severity,
            },
        )


@dataclass(frozen=True)
class JiraTicketAdapter:
    base_url: str
    email: str
    api_token: str
    project_key: str
    issue_type: str = "Task"
    timeout_seconds: float = 8
    client: httpx.Client | None = None
    name: str = "jira_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        if policy.decision != "allow":
            return ToolCall(name="ticket.create", status="blocked", policy=policy, result={})

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Created by AegisDesk governed CloudOps workflow. "
                                        f"Team: {team}. Severity: {severity}."
                                    ),
                                }
                            ],
                        }
                    ],
                },
                "issuetype": {"name": self.issue_type},
                "labels": ["aegisdesk", f"team-{team}", f"severity-{severity}".lower()],
            }
        }
        url = f"{self.base_url.rstrip('/')}/rest/api/3/issue"
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        should_close = self.client is None

        try:
            response = client.post(url, json=payload, auth=(self.email, self.api_token))
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            return ToolCall(
                name="ticket.create",
                status="blocked",
                policy=policy,
                result={
                    "adapter": self.name,
                    "system": "jira",
                    "status": "failed",
                    "error": exc.__class__.__name__,
                },
            )
        finally:
            if should_close:
                client.close()

        ticket_id = str(body.get("key") or body.get("id") or "JIRA-UNKNOWN")
        return ToolCall(
            name="ticket.create",
            status="allowed",
            policy=policy,
            result={
                "ticket_id": ticket_id,
                "external_url": f"{self.base_url.rstrip('/')}/browse/{ticket_id}",
                "title": title,
                "team": team,
                "severity": severity,
                "status": "open",
                "adapter": self.name,
                "system": "jira",
            },
        )


@dataclass(frozen=True)
class ServiceNowTicketAdapter:
    instance_url: str
    username: str
    password: str
    assignment_group: str | None = None
    table: str = "incident"
    timeout_seconds: float = 8
    client: httpx.Client | None = None
    name: str = "servicenow_ticket_adapter"

    def create_ticket(self, policy: PolicyDecision, title: str, team: str, severity: str) -> ToolCall:
        if policy.decision != "allow":
            return ToolCall(name="ticket.create", status="blocked", policy=policy, result={})

        impact, urgency = _servicenow_priority_fields(severity)
        payload = {
            "short_description": title,
            "description": (
                "Created by AegisDesk governed CloudOps workflow.\n"
                f"Team: {team}\n"
                f"Severity: {severity}\n"
                f"Policy: {policy.policy_name} / {policy.reason}"
            ),
            "category": "inquiry",
            "contact_type": "self-service",
            "impact": impact,
            "urgency": urgency,
        }
        if self.assignment_group:
            payload["assignment_group"] = self.assignment_group

        url = f"{self.instance_url.rstrip('/')}/api/now/table/{self.table}"
        client = self.client or httpx.Client(timeout=self.timeout_seconds)
        should_close = self.client is None

        try:
            response = client.post(url, json=payload, auth=(self.username, self.password))
            response.raise_for_status()
            body = response.json().get("result", {})
        except httpx.HTTPError as exc:
            return ToolCall(
                name="ticket.create",
                status="blocked",
                policy=policy,
                result={
                    "adapter": self.name,
                    "system": "servicenow",
                    "status": "failed",
                    "error": exc.__class__.__name__,
                },
            )
        finally:
            if should_close:
                client.close()

        ticket_id = str(body.get("number") or body.get("sys_id") or "SN-UNKNOWN")
        sys_id = str(body.get("sys_id") or "")
        return ToolCall(
            name="ticket.create",
            status="allowed",
            policy=policy,
            result={
                "ticket_id": ticket_id,
                "external_url": f"{self.instance_url.rstrip('/')}/nav_to.do?uri={self.table}.do?sys_id={sys_id}" if sys_id else None,
                "title": title,
                "team": team,
                "severity": severity,
                "status": str(body.get("state") or "open"),
                "adapter": self.name,
                "system": "servicenow",
                "sys_id": sys_id or None,
            },
        )


def _servicenow_priority_fields(severity: str) -> tuple[str, str]:
    normalized = severity.lower()
    if normalized in {"sev-1", "severity-1", "critical", "high"}:
        return "1", "1"
    if normalized in {"sev-2", "severity-2", "medium"}:
        return "2", "2"
    return "3", "3"


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
    lookback_minutes: int = 60
    query_limit: int = 20
    poll_attempts: int = 6
    poll_interval_seconds: float = 0.5
    client: object | None = None
    name: str = "cloudwatch_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        query_string = self._query_string(incident_id)
        logs_client = self.client or boto3.client("logs", region_name=self.region)
        end_time = int(datetime.now(UTC).timestamp())
        start_time = int((datetime.now(UTC) - timedelta(minutes=self.lookback_minutes)).timestamp())

        try:
            response = logs_client.start_query(
                logGroupName=self.log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=query_string,
                limit=self.query_limit,
            )
            query_id = response["queryId"]
            results = self._poll_results(logs_client, query_id)
        except (BotoCoreError, ClientError, KeyError, TimeoutError) as exc:
            return _unavailable_incident_context(
                incident_id=incident_id,
                log_group=self.log_group,
                query=query_string,
                reason=f"CloudWatch query unavailable: {exc.__class__.__name__}",
            )

        entries = [_entry_from_cloudwatch_result(row) for row in results]
        entries = [entry for entry in entries if entry is not None][: self.query_limit]
        suspected_cause = _suspected_cause_from_entries(entries, query)
        if not entries:
            suspected_cause = "CloudWatch returned no matching log events for the configured time window."

        return IncidentContext(
            incident_id=incident_id or "cloudwatch-latest",
            source="cloudwatch_logs",
            log_group=self.log_group,
            query=query_string,
            entries=entries,
            suspected_cause=suspected_cause,
        )

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        status = "blocked" if context.source == "incident_context_unavailable" else "allowed"
        return ToolCall(
            name="incident.context",
            status=status,
            policy=PolicyDecision(
                decision="allow" if status == "allowed" else "deny",
                reason=(
                    "read_only_cloudwatch_context_loaded"
                    if status == "allowed"
                    else "cloudwatch_context_unavailable_without_fallback"
                ),
                policy_name="incident_context",
                metadata={
                    "adapter": self.name,
                    "source": context.source,
                    "log_group": context.log_group,
                    "entries": len(context.entries),
                },
            ),
            result=context.model_dump(),
        )

    def _query_string(self, incident_id: str | None) -> str:
        limit = max(1, min(self.query_limit, 100))
        if incident_id:
            safe_incident_id = _safe_logs_pattern(incident_id)
            filter_expression = f"| filter @message like /{safe_incident_id}/ "
        else:
            filter_expression = (
                "| filter @message like /ERROR/ "
                "or @message like /WARN/ "
                "or @message like /timeout/ "
                "or @message like /latency/ "
                "or @message like /checkout/ "
            )
        return (
            "fields @timestamp, @message, service, level "
            f"{filter_expression}"
            "| sort @timestamp desc "
            f"| limit {limit}"
        )

    def _poll_results(self, logs_client, query_id: str) -> list[list[dict[str, str]]]:
        for _ in range(max(1, self.poll_attempts)):
            response = logs_client.get_query_results(queryId=query_id)
            status = response.get("status")
            if status == "Complete":
                return response.get("results", [])
            if status in {"Failed", "Cancelled", "Timeout"}:
                raise TimeoutError(f"cloudwatch_query_{status.lower()}")
            if self.poll_interval_seconds > 0:
                time.sleep(self.poll_interval_seconds)
        raise TimeoutError("cloudwatch_query_poll_limit_exceeded")


@dataclass(frozen=True)
class DatadogIncidentAdapter:
    site: str
    index: str
    name: str = "datadog_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        raise NotImplementedError("datadog_incident_adapter_requires_logs_client")

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        raise NotImplementedError("datadog_incident_adapter_requires_logs_client")


@dataclass(frozen=True)
class UnavailableIncidentAdapter:
    reason: str
    system: str
    name: str = "unavailable_incident_adapter"

    def lookup_context(self, incident_id: str | None, query: str) -> IncidentContext:
        return _unavailable_incident_context(
            incident_id=incident_id,
            log_group=self.system,
            query=query,
            reason=self.reason,
        )

    def to_tool_call(self, context: IncidentContext) -> ToolCall:
        return ToolCall(
            name="incident.context",
            status="blocked",
            policy=PolicyDecision(
                decision="deny",
                reason="incident_context_adapter_unavailable_without_fallback",
                policy_name="incident_context",
                metadata={"adapter": self.name, "system": self.system, "source": context.source},
            ),
            result=context.model_dump(),
        )


def _unavailable_incident_context(incident_id: str | None, log_group: str, query: str, reason: str) -> IncidentContext:
    return IncidentContext(
        incident_id=incident_id or "incident-context-unavailable",
        source="incident_context_unavailable",
        log_group=log_group,
        query=query,
        entries=[],
        suspected_cause=reason,
    )


def _safe_logs_pattern(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.:#-]", "", value)
    return sanitized[:80] or "incident"


def _entry_from_cloudwatch_result(row: list[dict[str, str]]):
    fields = {item.get("field", ""): item.get("value", "") for item in row}
    message = fields.get("@message") or fields.get("message") or ""
    if not message:
        return None
    return {
        "timestamp": fields.get("@timestamp") or fields.get("timestamp") or datetime.now(UTC).isoformat(),
        "level": _normalize_log_level(fields.get("level") or message),
        "service": fields.get("service") or _service_from_message(message),
        "message": message,
    }


def _normalize_log_level(value: str) -> str:
    value = value.upper()
    if "ERROR" in value:
        return "ERROR"
    if "WARN" in value:
        return "WARN"
    return "INFO"


def _service_from_message(message: str) -> str:
    match = re.search(r"\bservice[=:]\s*([A-Za-z0-9_.-]+)", message)
    if match:
        return match.group(1)
    if "checkout" in message.lower():
        return "checkout-api"
    return "unknown-service"


def _suspected_cause_from_entries(entries, query: str) -> str:
    text = " ".join([query, *[entry["message"] for entry in entries]]).lower()
    if "connection pool" in text or "database" in text:
        return "Database connection pool saturation is the strongest signal."
    if "payment" in text or "upstream" in text:
        return "Upstream payment latency is likely contributing to checkout timeouts."
    if "deploy" in text or "release" in text:
        return "Recent deployment timing should be checked before deeper debugging."
    if "timeout" in text or "latency" in text:
        return "Recent timeout and latency log events should be compared with dependency health."
    return "Recent log patterns should be compared with deployment and dependency health."


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
