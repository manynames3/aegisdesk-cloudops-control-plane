from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import create_demo_token, require_actor, require_admin, require_manager_or_admin
from .model_router import select_model_route
from .models import (
    Actor,
    ApprovalList,
    AuditEvent,
    ChatRequest,
    ChatResponse,
    DemoTokenRequest,
    DemoTokenResponse,
    EventList,
    HealthResponse,
    Role,
)
from .observability import configure_observability, current_trace_id, tracer
from .policy import classify_intent
from .policy_engine import PolicyEngine, PolicyUnavailable
from .redaction import inspect_and_redact
from .settings import get_settings
from .store import DemoStore, actor_from
from .tools import create_ticket, lookup_cost_summary, request_read_only_access

settings = get_settings()

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
configure_observability(app, settings)

store = DemoStore()
policy_engine = PolicyEngine()


@app.post("/auth/demo-token", response_model=DemoTokenResponse)
def demo_token(request: DemoTokenRequest) -> DemoTokenResponse:
    if not settings.demo_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="demo_token_issuer_disabled")

    actor = demo_actor_for_role(request.role, request.team)
    return DemoTokenResponse(access_token=create_demo_token(actor), actor=actor)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="aegisdesk-api", mode="local-demo" if settings.demo_mode else "production")


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "aegisdesk-api"}


@app.get("/health/ready")
def ready():
    store_ready = store.ready()
    policy_ready = policy_engine.ready()
    details = {"store": {"ready": store_ready}, "policy": policy_ready}

    if not store_ready or not policy_ready["ready"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=details)

    return {"status": "ok", "details": details}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, actor: Annotated[Actor, Depends(require_actor)]) -> ChatResponse:
    return process_chat(request, actor)


@app.get("/events", response_model=EventList)
def events(_actor: Annotated[Actor, Depends(require_admin)]) -> EventList:
    return EventList(events=list(reversed(store.events))[:100])


@app.get("/metrics/summary")
def metrics(_actor: Annotated[Actor, Depends(require_admin)]):
    return store.metrics()


@app.get("/approvals", response_model=ApprovalList)
def approvals(_actor: Annotated[Actor, Depends(require_manager_or_admin)]) -> ApprovalList:
    return ApprovalList(approvals=list(reversed(store.approvals)))


@app.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, actor: Annotated[Actor, Depends(require_manager_or_admin)]):
    try:
        approval = store.decide_approval(approval_id, actor.user_id, actor.role, approved=True)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval_not_found") from exc

    store.add_event(
        AuditEvent(
            request_id=approval.request_id,
            actor=actor,
            event_type="approval.granted",
            summary="Manager approved scoped temporary access.",
            metadata={"approval_id": approval.approval_id, "permission": approval.permission},
            trace_id=current_trace_id(),
        )
    )
    return approval


@app.post("/approvals/{approval_id}/deny")
def deny(approval_id: str, actor: Annotated[Actor, Depends(require_manager_or_admin)]):
    try:
        approval = store.decide_approval(approval_id, actor.user_id, actor.role, approved=False)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval_not_found") from exc

    store.add_event(
        AuditEvent(
            request_id=approval.request_id,
            actor=actor,
            event_type="approval.denied",
            summary="Manager denied scoped temporary access.",
            metadata={"approval_id": approval.approval_id, "permission": approval.permission},
            trace_id=current_trace_id(),
        )
    )
    return approval


@app.post("/demo/reset")
def reset_demo(_actor: Annotated[Actor, Depends(require_admin)]):
    store.reset()
    return {"status": "reset"}


@app.post("/demo/seed")
def seed_demo(_actor: Annotated[Actor, Depends(require_admin)]):
    store.reset()
    demo_requests = [
        (
            demo_actor_for_role(Role.employee, "payments"),
            ChatRequest(message="The checkout service is timing out. What should I check first?", context={"incident_id": "INC-1042"}),
        ),
        (
            demo_actor_for_role(Role.employee, "payments"),
            ChatRequest(
                message="Here is the error log with token=demo-secret-value and customer@example.test. Why is this failing?",
                context={"incident_id": "INC-1042"},
            ),
        ),
        (
            demo_actor_for_role(Role.employee, "cloudops"),
            ChatRequest(message="Create a ticket for the VPN outage and assign it to CloudOps."),
        ),
        (
            demo_actor_for_role(Role.employee, "payments"),
            ChatRequest(message="Give me admin access to the production database.", context={"incident_id": "INC-1042"}),
        ),
        (
            demo_actor_for_role(Role.manager, "payments"),
            ChatRequest(message="Why did our AI and cloud costs spike this week?"),
        ),
    ]

    for actor, demo_request in demo_requests:
        process_chat(demo_request, actor)

    return {"status": "seeded", "requests": len(demo_requests), "metrics": store.metrics()}


def process_chat(request: ChatRequest, actor: Actor) -> ChatResponse:
    with tracer.start_as_current_span("aegisdesk.chat") as span:
        request_id = f"req-{uuid4().hex[:10]}"
        trace_id = current_trace_id()
        if trace_id == "trace-unavailable":
            trace_id = f"trace-{uuid4().hex[:12]}"
        span.set_attribute("aegisdesk.request_id", request_id)
        span.set_attribute("aegisdesk.role", actor.role.value)
        span.set_attribute("aegisdesk.team", actor.team)

        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="request.received",
                summary="CloudOps request received.",
                metadata={"team": actor.team},
                trace_id=trace_id,
            )
        )

        with tracer.start_as_current_span("aegisdesk.redaction"):
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
        try:
            with tracer.start_as_current_span("aegisdesk.policy.chat"):
                policy = policy_engine.evaluate_chat(actor, intent)
            with tracer.start_as_current_span("aegisdesk.policy.model_route"):
                model_policy = policy_engine.evaluate_model_route(redaction, intent)
        except PolicyUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        route = select_model_route(
            redaction,
            intent,
            provider_override=model_policy.metadata.get("provider"),
            reason_override=model_policy.reason,
        )
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
                    metadata={"intent": intent, "reason": policy.reason, "policy_engine": policy_engine.mode},
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
                    metadata={"intent": intent, "reason": policy.reason, "policy_engine": policy_engine.mode},
                    trace_id=trace_id,
                )
            )

        tool_calls = []
        answer = build_answer(intent, redaction.redacted_text, policy.decision)

        try:
            if intent == "create_ticket":
                tool_policy = policy_engine.evaluate_tool(actor.role, "ticket", "create_ticket")
                tool_call = create_ticket(tool_policy, "CloudOps support request", actor.team, "medium")
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
                    answer = f"Ticket {tool_call.result['ticket_id']} was created for {actor.team} with medium severity."

            if intent == "production_admin_access":
                tool_policy = policy_engine.evaluate_tool(actor.role, "access", "request_temporary_read_only")
                tool_call, approval = request_read_only_access(
                    request_id,
                    actor.user_id,
                    actor.role,
                    actor.team,
                    "Safer alternative to denied production admin access request.",
                    tool_policy,
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
                tool_policy = policy_engine.evaluate_tool(actor.role, "cost", "view_summary")
                tool_call = lookup_cost_summary(tool_policy)
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
        except PolicyUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        return ChatResponse(
            request_id=request_id,
            answer=answer,
            model_route=route,
            redaction=redaction,
            policy=policy,
            tool_calls=tool_calls,
            trace_id=trace_id,
        )


def demo_actor_for_role(role: Role, team: str | None = None) -> Actor:
    if role == Role.admin:
        return actor_from("u-9001", role, team or "platform")
    if role == Role.manager:
        return actor_from("u-2001", role, team or "payments")
    return actor_from("u-1001", role, team or "payments")


def build_answer(intent: str, redacted_text: str, decision: str) -> str:
    if decision == "deny":
        return "This request was denied by policy."

    if intent == "incident_triage":
        return (
            "Start with recent deploys, upstream dependency latency, database connection pool saturation, "
            "and any matching alerts. Sensitive values were removed before model routing when detected."
        )

    if intent == "support_guidance":
        return "I can help with approved CloudOps support steps, create a ticket, or explain policy-safe next actions."

    return f"Request processed through the local demo gateway. Sanitized input: {redacted_text[:180]}"
