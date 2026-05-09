from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .model_router import select_model_route
from .models import (
    ApprovalDecisionRequest,
    ApprovalList,
    AuditEvent,
    ChatRequest,
    ChatResponse,
    EventList,
    HealthResponse,
)
from .policy import classify_intent, evaluate_chat_policy, evaluate_model_route
from .redaction import inspect_and_redact
from .store import DemoStore, actor_from
from .tools import create_ticket, lookup_cost_summary, request_read_only_access

app = FastAPI(
    title="AegisDesk CloudOps Control Plane API",
    version="0.1.0",
    description="Local-first demo gateway for policy-aware CloudOps AI workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DemoStore()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="aegisdesk-api", mode="local-demo")


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    request_id = f"req-{uuid4().hex[:10]}"
    trace_id = f"trace-{uuid4().hex[:12]}"
    actor = actor_from(request.user_id, request.role, request.team)

    store.add_event(
        AuditEvent(
            request_id=request_id,
            actor=actor,
            event_type="request.received",
            summary="CloudOps request received.",
            metadata={"team": request.team},
            trace_id=trace_id,
        )
    )

    redaction = inspect_and_redact(request.message)
    if redaction.pii_detected:
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="pii.detected",
                summary="PII detected and redacted before model routing.",
                metadata={"findings": [f.label for f in redaction.findings if f.kind in {"email", "ssn"}]},
                trace_id=trace_id,
            )
        )
    if redaction.secrets_detected:
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="secret.detected",
                summary="Secret-like value detected and redacted before model routing.",
                metadata={"findings": [f.label for f in redaction.findings if f.kind in {"api_key", "credential"}]},
                trace_id=trace_id,
            )
        )

    intent = classify_intent(request.message)
    policy = evaluate_chat_policy(request, intent)
    model_policy = evaluate_model_route(redaction, intent)
    route = select_model_route(redaction, intent)
    store.add_route(route)

    store.add_event(
        AuditEvent(
            request_id=request_id,
            actor=actor,
            event_type="model.route.selected",
            summary=f"Request routed to {route.provider}.",
            metadata={"model": route.model, "reason": route.reason, "policy_reason": model_policy.reason},
            trace_id=trace_id,
        )
    )

    if policy.decision == "deny":
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="policy.denied",
                summary="Request denied by policy.",
                metadata={"intent": intent, "reason": policy.reason},
                trace_id=trace_id,
            )
        )
    else:
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="policy.allowed" if policy.decision == "allow" else "approval.requested",
                summary=f"Policy decision: {policy.decision}.",
                metadata={"intent": intent, "reason": policy.reason},
                trace_id=trace_id,
            )
        )

    tool_calls = []
    answer = build_answer(intent, redaction.redacted_text, policy.decision)

    if intent == "create_ticket":
        tool_call = create_ticket(request.role, "CloudOps support request", request.team, "medium")
        tool_calls.append(tool_call)
        event_type = "tool.called" if tool_call.status == "allowed" else "tool.blocked"
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type=event_type,
                summary=f"{tool_call.name} {tool_call.status}.",
                metadata={"tool": tool_call.name, "policy_reason": tool_call.policy.reason},
                trace_id=trace_id,
            )
        )
        if tool_call.status == "allowed":
            answer = f"Ticket {tool_call.result['ticket_id']} was created for {request.team} with medium severity."

    if intent == "production_admin_access":
        tool_call, approval = request_read_only_access(
            request_id,
            request.user_id,
            request.role,
            request.team,
            "Safer alternative to denied production admin access request.",
        )
        tool_calls.append(tool_call)
        store.add_approval(approval)
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="approval.requested",
                summary="Temporary read-only access was sent for manager approval.",
                metadata={"approval_id": approval.approval_id, "resource": approval.resource},
                trace_id=trace_id,
            )
        )
        answer = (
            "Production admin access was denied. A safer temporary read-only access request "
            f"was opened for manager approval: {approval.approval_id}."
        )

    if intent == "cost_investigation":
        tool_call = lookup_cost_summary(request.role)
        tool_calls.append(tool_call)
        event_type = "tool.called" if tool_call.status == "allowed" else "approval.requested"
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type=event_type,
                summary=f"{tool_call.name} {tool_call.status}.",
                metadata={"tool": tool_call.name, "policy_reason": tool_call.policy.reason},
                trace_id=trace_id,
            )
        )
        if tool_call.status == "allowed":
            answer = (
                "The simulated weekly cost spike is driven by cloud model experimentation. "
                "The recommended control is to route repeated low-value prompts locally or cache approved answers."
            )
        else:
            answer = "Cost investigation requires manager or admin access."

    return ChatResponse(
        request_id=request_id,
        answer=answer,
        model_route=route,
        redaction=redaction,
        policy=policy,
        tool_calls=tool_calls,
        trace_id=trace_id,
    )


@app.get("/events", response_model=EventList)
def events() -> EventList:
    return EventList(events=list(reversed(store.events))[:100])


@app.get("/metrics/summary")
def metrics():
    return store.metrics()


@app.get("/approvals", response_model=ApprovalList)
def approvals() -> ApprovalList:
    return ApprovalList(approvals=list(reversed(store.approvals)))


@app.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, decision: ApprovalDecisionRequest):
    try:
        approval = store.decide_approval(approval_id, decision.actor_id, decision.role, approved=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval_not_found") from exc

    store.add_event(
        AuditEvent(
            request_id=approval.request_id,
            actor=actor_from(decision.actor_id, decision.role, "management"),
            event_type="approval.granted",
            summary="Manager approved scoped temporary access.",
            metadata={"approval_id": approval.approval_id, "permission": approval.permission},
            trace_id=f"trace-{uuid4().hex[:12]}",
        )
    )
    return approval


@app.post("/approvals/{approval_id}/deny")
def deny(approval_id: str, decision: ApprovalDecisionRequest):
    try:
        approval = store.decide_approval(approval_id, decision.actor_id, decision.role, approved=False)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval_not_found") from exc

    store.add_event(
        AuditEvent(
            request_id=approval.request_id,
            actor=actor_from(decision.actor_id, decision.role, "management"),
            event_type="approval.denied",
            summary="Manager denied scoped temporary access.",
            metadata={"approval_id": approval.approval_id, "permission": approval.permission},
            trace_id=f"trace-{uuid4().hex[:12]}",
        )
    )
    return approval


@app.post("/demo/reset")
def reset_demo():
    store.reset()
    return {"status": "reset"}


def build_answer(intent: str, redacted_text: str, decision: str) -> str:
    if decision == "deny":
        return "This request was denied by policy."

    if intent == "incident_triage":
        return (
            "Start with recent deploys, upstream dependency latency, database connection pool saturation, "
            "and any matching alerts. Sensitive values were removed before model routing when detected."
        )

    if intent == "support_guidance":
        return (
            "I can help with approved CloudOps support steps, create a ticket, or explain policy-safe next actions."
        )

    return f"Request processed through the local demo gateway. Sanitized input: {redacted_text[:180]}"

