from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(StrEnum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class Actor(BaseModel):
    user_id: str
    role: Role
    team: str


class RedactionFinding(BaseModel):
    kind: Literal["email", "ssn", "api_key", "credential"]
    label: str
    replacement: str


class RedactionResult(BaseModel):
    pii_detected: bool
    secrets_detected: bool
    redacted_text: str
    findings: list[RedactionFinding] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    decision: Literal["allow", "deny", "approval_required"]
    reason: str
    policy_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelRoute(BaseModel):
    provider: str
    model: str
    reason: str
    estimated_cost_usd: float
    external_call: bool = False


class ToolCall(BaseModel):
    tool_call_id: str = Field(default_factory=lambda: f"tool-{uuid4().hex[:8]}")
    name: str
    status: Literal["allowed", "blocked", "approval_required"]
    policy: PolicyDecision
    result: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    model_route: ModelRoute
    redaction: RedactionResult
    policy: PolicyDecision
    tool_calls: list[ToolCall] = Field(default_factory=list)
    trace_id: str


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt-{uuid4().hex[:10]}")
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: Actor
    event_type: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: str


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class ApprovalRequest(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"apr-{uuid4().hex[:8]}")
    request_id: str
    requester: Actor
    resource: str
    permission: str
    reason: str
    risk_level: Literal["low", "medium", "high"]
    status: ApprovalStatus = ApprovalStatus.pending
    policy_reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_by: str | None = None
    decided_at: datetime | None = None


class DemoTokenRequest(BaseModel):
    role: Role
    team: str | None = None


class DemoTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    actor: Actor


class EventList(BaseModel):
    events: list[AuditEvent]


class ApprovalList(BaseModel):
    approvals: list[ApprovalRequest]


class MetricsSummary(BaseModel):
    requests_total: int
    estimated_spend_usd: float
    local_model_requests: int
    cloud_model_requests: int
    redactions_total: int
    denied_actions: int
    approvals_pending: int
    tool_calls_total: int


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    mode: str
