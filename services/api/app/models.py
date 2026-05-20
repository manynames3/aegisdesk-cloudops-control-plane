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
    input_tokens: int = 0
    output_tokens: int = 0


class ToolCall(BaseModel):
    tool_call_id: str = Field(default_factory=lambda: f"tool-{uuid4().hex[:8]}")
    name: str
    status: Literal["allowed", "blocked", "approval_required"]
    policy: PolicyDecision
    result: dict[str, Any] = Field(default_factory=dict)


class IncidentLogEntry(BaseModel):
    timestamp: str
    level: Literal["INFO", "WARN", "ERROR"]
    service: str
    message: str


class IncidentContext(BaseModel):
    incident_id: str
    source: Literal["seeded_cloudwatch_logs", "cloudwatch_logs", "incident_context_unavailable"]
    log_group: str
    query: str
    entries: list[IncidentLogEntry] = Field(default_factory=list)
    suspected_cause: str


class KnowledgeCitation(BaseModel):
    doc_id: str
    title: str
    source_path: str
    section: str
    owner: str
    last_reviewed: str
    excerpt: str


class AnswerSource(BaseModel):
    kind: Literal[
        "local_control",
        "model",
        "knowledge",
        "operational_context",
        "tool",
        "policy",
        "cost",
        "clarification",
    ]
    name: str
    detail: str
    trusted: bool = True


class ClarificationResult(BaseModel):
    status: Literal["complete", "partial_guidance", "blocked_pending_details"]
    risk_level: Literal["low", "medium", "high"]
    missing_fields: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    can_answer_partially: bool = False
    blocks_tool_call: bool = False
    reason: str


class TrustedSourceScore(BaseModel):
    score: int = Field(ge=0, le=100)
    trusted_source_found: bool
    source_freshness: Literal["fresh", "stale", "unknown"]
    external_model_used: bool
    sensitive_data_sent_externally: bool
    policy_result: str
    rationale: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    answer: str
    model_route: ModelRoute
    redaction: RedactionResult
    policy: PolicyDecision
    tool_calls: list[ToolCall] = Field(default_factory=list)
    incident_context: IncidentContext | None = None
    knowledge_citations: list[KnowledgeCitation] = Field(default_factory=list)
    answer_sources: list[AnswerSource] = Field(default_factory=list)
    clarification: ClarificationResult | None = None
    trusted_source_score: TrustedSourceScore
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


class PersonaTokenRequest(BaseModel):
    role: Role
    team: str | None = None


class PersonaTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    actor: Actor


class HostedAuthConfig(BaseModel):
    client_id: str
    authorization_endpoint: str
    logout_endpoint: str
    scopes: list[str]


class HostedLoginResponse(BaseModel):
    actor: Actor
    username: str
    password: str
    config: HostedAuthConfig


class OAuthExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


class OAuthExchangeResponse(BaseModel):
    id_token: str
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str
    expires_in: int | None = None
    actor: Actor


class EventList(BaseModel):
    events: list[AuditEvent]


class RequestReplay(BaseModel):
    request_id: str
    trace_id: str
    actor: Actor | None = None
    prompt: str | None = None
    sanitized_prompt: str | None = None
    redaction: RedactionResult | None = None
    policy_input: dict[str, Any] = Field(default_factory=dict)
    policy: PolicyDecision | None = None
    model_route: ModelRoute | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    answer_sources: list[AnswerSource] = Field(default_factory=list)
    knowledge_citations: list[KnowledgeCitation] = Field(default_factory=list)
    clarification: ClarificationResult | None = None
    trusted_source_score: TrustedSourceScore | None = None
    answer_preview: str | None = None
    audit_events: list[AuditEvent] = Field(default_factory=list)


class AbuseControls(BaseModel):
    api_gateway_throttling_rate_limit: float
    api_gateway_throttling_burst_limit: int
    max_request_chars: int
    quota_window_seconds: int
    role_quotas: dict[str, int]
    cloud_model_kill_switch: bool
    bedrock_enabled: bool
    request_body_limit_note: str


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
