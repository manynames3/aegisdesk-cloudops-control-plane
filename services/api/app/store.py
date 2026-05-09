from __future__ import annotations

from datetime import UTC, datetime

from .models import (
    Actor,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    MetricsSummary,
    ModelRoute,
    Role,
)


class DemoStore:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self.approvals: list[ApprovalRequest] = []
        self.model_routes: list[ModelRoute] = []

    def add_event(self, event: AuditEvent) -> None:
        self.events.append(event)

    def add_route(self, route: ModelRoute) -> None:
        self.model_routes.append(route)

    def add_approval(self, approval: ApprovalRequest) -> None:
        self.approvals.append(approval)

    def decide_approval(self, approval_id: str, actor_id: str, role: Role, approved: bool) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if role not in {Role.manager, Role.admin}:
            raise PermissionError("approval_decision_requires_manager_or_admin")

        approval.status = ApprovalStatus.approved if approved else ApprovalStatus.denied
        approval.decided_by = actor_id
        approval.decided_at = datetime.now(UTC)
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        for approval in self.approvals:
            if approval.approval_id == approval_id:
                return approval
        raise KeyError(approval_id)

    def metrics(self) -> MetricsSummary:
        local_model_requests = sum(1 for route in self.model_routes if route.provider == "local")
        cloud_model_requests = sum(1 for route in self.model_routes if route.provider == "simulated-cloud")
        redactions_total = sum(1 for event in self.events if event.event_type in {"pii.detected", "secret.detected"})
        denied_actions = sum(1 for event in self.events if event.event_type in {"policy.denied", "tool.blocked"})
        tool_calls_total = sum(1 for event in self.events if event.event_type == "tool.called")
        approvals_pending = sum(1 for approval in self.approvals if approval.status == ApprovalStatus.pending)

        return MetricsSummary(
            requests_total=sum(1 for event in self.events if event.event_type == "request.received"),
            estimated_spend_usd=round(sum(route.estimated_cost_usd for route in self.model_routes), 4),
            local_model_requests=local_model_requests,
            cloud_model_requests=cloud_model_requests,
            redactions_total=redactions_total,
            denied_actions=denied_actions,
            approvals_pending=approvals_pending,
            tool_calls_total=tool_calls_total,
        )

    def reset(self) -> None:
        self.events.clear()
        self.approvals.clear()
        self.model_routes.clear()


def actor_from(user_id: str, role: Role, team: str) -> Actor:
    return Actor(user_id=user_id, role=role, team=team)

