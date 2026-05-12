from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthError, create_demo_token, decode_token, jwks_document, require_actor, require_admin, require_manager_or_admin
from .cognito_auth import CognitoSessionError, create_persona_session, ensure_persona_user, exchange_oauth_code
from .cost_explorer import CostExplorerUnavailable, get_cost_summary
from .incident_context import lookup_incident_context
from .llm import LLMUnavailable, maybe_generate_with_bedrock
from .model_router import select_model_route
from .models import (
    Actor,
    AnswerSource,
    ApprovalList,
    AuditEvent,
    ChatRequest,
    ChatResponse,
    EventList,
    HealthResponse,
    HostedAuthConfig,
    HostedLoginResponse,
    OAuthExchangeRequest,
    OAuthExchangeResponse,
    PersonaTokenRequest,
    PersonaTokenResponse,
    Role,
)
from .observability import configure_observability, current_trace_id, tracer
from .policy import classify_intent
from .policy_engine import PolicyEngine, PolicyUnavailable
from .redaction import inspect_and_redact
from .settings import get_settings
from .store import actor_from, create_store
from .tools import create_ticket, lookup_cost_summary, lookup_incident_context_tool, request_read_only_access

settings = get_settings()

app = FastAPI(
    title="AegisDesk CloudOps Control Plane API",
    version="0.1.0",
    description="CloudOps AI control plane for policy-aware AI workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
configure_observability(app, settings)

store = create_store()
policy_engine = PolicyEngine()


@app.post("/auth/persona-token", response_model=PersonaTokenResponse)
def persona_token(request: PersonaTokenRequest) -> PersonaTokenResponse:
    if not settings.persona_issuer_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="persona_token_issuer_disabled")

    actor = reviewer_actor_for_role(request.role, request.team)
    if settings.auth_mode == "cognito":
        try:
            access_token, actor = create_persona_session(request.role, request.team, settings)
        except CognitoSessionError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        return PersonaTokenResponse(access_token=access_token, actor=actor)

    return PersonaTokenResponse(access_token=create_demo_token(actor), actor=actor)


@app.get("/auth/hosted-ui-config", response_model=HostedAuthConfig)
def hosted_ui_config() -> HostedAuthConfig:
    return _hosted_auth_config()


@app.post("/auth/hosted-ui-login", response_model=HostedLoginResponse)
def hosted_ui_login(request: PersonaTokenRequest) -> HostedLoginResponse:
    if settings.auth_mode != "cognito":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="hosted_ui_requires_cognito")
    try:
        username, password, actor = ensure_persona_user(request.role, request.team, settings)
    except CognitoSessionError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return HostedLoginResponse(
        actor=actor,
        username=username,
        password=password,
        config=_hosted_auth_config(),
    )


@app.post("/auth/oauth/exchange", response_model=OAuthExchangeResponse)
def oauth_exchange(request: OAuthExchangeRequest) -> OAuthExchangeResponse:
    if settings.auth_mode != "cognito":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="oauth_exchange_requires_cognito")
    try:
        token_response = exchange_oauth_code(request.code, request.code_verifier, request.redirect_uri, settings)
        id_token = token_response["id_token"]
        actor = decode_token(id_token)
    except (AuthError, CognitoSessionError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return OAuthExchangeResponse(
        id_token=id_token,
        access_token=token_response.get("access_token"),
        refresh_token=token_response.get("refresh_token"),
        token_type=token_response.get("token_type", "Bearer"),
        expires_in=token_response.get("expires_in"),
        actor=actor,
    )


@app.post("/auth/demo-token", response_model=PersonaTokenResponse)
def demo_token(request: PersonaTokenRequest) -> PersonaTokenResponse:
    return persona_token(request)


@app.get("/auth/jwks.json")
def auth_jwks():
    return jwks_document()


@app.get("/.well-known/jwks.json")
def well_known_jwks():
    return jwks_document()


def _hosted_auth_config() -> HostedAuthConfig:
    if not settings.cognito_client_id or not settings.cognito_hosted_ui_domain:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="missing_cognito_hosted_ui_configuration")

    domain = settings.cognito_hosted_ui_domain.rstrip("/")
    return HostedAuthConfig(
        client_id=settings.cognito_client_id,
        authorization_endpoint=f"{domain}/oauth2/authorize",
        logout_endpoint=f"{domain}/logout",
        scopes=["openid", "profile", "email"],
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    if not settings.persona_issuer_enabled:
        mode = "production"
    elif settings.store_backend == "dynamodb":
        mode = "portfolio"
    else:
        mode = "local"
    return HealthResponse(status="ok", service="aegisdesk-api", mode=mode)


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
def events(_actor: Annotated[Actor, Depends(require_manager_or_admin)]) -> EventList:
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
            metadata={
                "approval_id": approval.approval_id,
                "permission": approval.permission,
                "decided_by": actor.user_id,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "status": approval.status.value,
            },
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
            metadata={
                "approval_id": approval.approval_id,
                "permission": approval.permission,
                "decided_by": actor.user_id,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
                "status": approval.status.value,
            },
            trace_id=current_trace_id(),
        )
    )
    return approval


@app.post("/admin/reset")
def reset_state(_actor: Annotated[Actor, Depends(require_admin)]):
    store.reset()
    return {"status": "reset"}


@app.post("/admin/seed")
def seed_state(_actor: Annotated[Actor, Depends(require_admin)]):
    store.reset()
    seed_requests = [
        (
            reviewer_actor_for_role(Role.employee, "payments"),
            ChatRequest(message="The checkout service is timing out. What should I check first?", context={"incident_id": "INC-1042"}),
        ),
        (
            reviewer_actor_for_role(Role.employee, "payments"),
            ChatRequest(
                message="Here is the error log with token=sample-secret-value and customer@example.test. Why is this failing?",
                context={"incident_id": "INC-1042"},
            ),
        ),
        (
            reviewer_actor_for_role(Role.employee, "cloudops"),
            ChatRequest(message="Create a ticket for the VPN outage and assign it to CloudOps."),
        ),
        (
            reviewer_actor_for_role(Role.employee, "payments"),
            ChatRequest(message="Give me admin access to the production database.", context={"incident_id": "INC-1042"}),
        ),
        (
            reviewer_actor_for_role(Role.manager, "payments"),
            ChatRequest(message="Why did our AI and cloud costs spike this week?"),
        ),
    ]

    for actor, seed_request in seed_requests:
        process_chat(seed_request, actor)

    return {"status": "seeded", "requests": len(seed_requests), "metrics": store.metrics()}


@app.post("/demo/reset")
def reset_demo(_actor: Annotated[Actor, Depends(require_admin)]):
    return reset_state(_actor)


@app.post("/demo/seed")
def seed_demo(_actor: Annotated[Actor, Depends(require_admin)]):
    return seed_state(_actor)


def process_chat(request: ChatRequest, actor: Actor) -> ChatResponse:
    with tracer.start_as_current_span("aegisdesk.chat") as span:
        request_id = f"req-{uuid4().hex[:10]}"
        trace_id = current_trace_id()
        if trace_id == "trace-unavailable":
            trace_id = f"trace-{uuid4().hex[:12]}"
        span.set_attribute("aegisdesk.request_id", request_id)
        span.set_attribute("aegisdesk.role", actor.role.value)
        span.set_attribute("aegisdesk.team", actor.team)

        try:
            quota_count = store.quota_count(actor)
            quota = policy_engine.evaluate_quota(actor, quota_count)
        except PolicyUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        if quota.decision == "deny":
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="quota.denied",
                    summary="Request denied by quota policy.",
                    metadata=quota.metadata,
                    trace_id=trace_id,
                )
            )
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=quota.reason)

        current_quota_count = store.increment_quota(actor)
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="quota.allowed",
                summary="Request allowed by quota policy.",
                metadata={**quota.metadata, "new_count": current_quota_count},
                trace_id=trace_id,
            )
        )

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
        incident_context = None
        answer = build_answer(intent, redaction.redacted_text, policy.decision)
        bedrock_answer_used = False

        if intent == "incident_triage":
            incident_context = lookup_incident_context(
                str(request.context.get("incident_id") or "INC-1042"),
                redaction.redacted_text,
            )
            tool_call = lookup_incident_context_tool(incident_context)
            tool_calls.append(tool_call)
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="incident.context.loaded",
                    summary="Read-only incident context loaded from seeded CloudWatch-style logs.",
                    metadata={
                        "tool": tool_call.name,
                        "source": incident_context.source,
                        "incident_id": incident_context.incident_id,
                        "log_group": incident_context.log_group,
                        "entries": len(incident_context.entries),
                    },
                    trace_id=trace_id,
                )
            )
            answer = enrich_incident_answer(answer, incident_context)

        if policy.decision == "allow":
            try:
                bedrock_answer, route = maybe_generate_with_bedrock(
                    route,
                    sanitized_input=redaction.redacted_text,
                    intent=intent,
                    settings=settings,
                )
                if bedrock_answer:
                    answer = bedrock_answer
                    bedrock_answer_used = True
            except LLMUnavailable:
                route = route.model_copy(
                    update={
                        "provider": "simulated-cloud",
                        "model": "bedrock-unavailable-deterministic-fallback",
                        "external_call": False,
                        "estimated_cost_usd": 0.0008,
                    }
                )
                store.add_event(
                    AuditEvent(
                        request_id=request_id,
                        actor=actor,
                        event_type="model.fallback",
                        summary="Bedrock was unavailable; deterministic fallback was used.",
                        metadata={"provider": "bedrock", "fallback_model": route.model},
                        trace_id=trace_id,
                    )
                )

        store.add_route(route)

        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="model.route.selected",
                summary=f"Request routed to {route.provider}.",
                metadata={
                    "model": route.model,
                    "provider": route.provider,
                    "reason": route.reason,
                    "policy_reason": model_policy.reason,
                    "external_call": route.external_call,
                    "input_tokens": route.input_tokens,
                    "output_tokens": route.output_tokens,
                },
                trace_id=trace_id,
            )
        )

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
                        metadata={
                            "approval_id": approval.approval_id,
                            "resource": approval.resource,
                            "permission": approval.permission,
                            "requester": approval.requester.user_id,
                            "status": approval.status.value,
                        },
                        trace_id=trace_id,
                    )
                )
                answer = (
                    "Production admin access was denied. A safer temporary read-only access request "
                    f"was opened for manager approval: {approval.approval_id}."
                )

            if intent == "cost_investigation":
                tool_policy = policy_engine.evaluate_tool(actor.role, "cost", "view_summary")
                cost_summary = None
                if tool_policy.decision == "allow":
                    try:
                        cost_summary = get_cost_summary(settings, store)
                    except CostExplorerUnavailable:
                        cost_summary = None
                tool_call = lookup_cost_summary(tool_policy, cost_summary)
                tool_calls.append(tool_call)
                event_type = "tool.called" if tool_call.status == "allowed" else "approval.requested"
                store.add_event(
                    AuditEvent(
                        request_id=request_id,
                        actor=actor,
                        event_type=event_type,
                        summary=f"{tool_call.name} {tool_call.status}.",
                        metadata={
                            "tool": tool_call.name,
                            "policy_reason": tool_call.policy.reason,
                            "source": tool_call.result.get("source"),
                            "cache_hit": tool_call.result.get("cache_hit"),
                        },
                        trace_id=trace_id,
                    )
                )
                if tool_call.status == "allowed":
                    source = tool_call.result.get("source", "cost_summary")
                    total = tool_call.result.get("total_usd", 0)
                    driver = tool_call.result.get("largest_driver", "unknown service")
                    recommendation = str(tool_call.result.get("recommendation", "review cost drivers")).rstrip(".")
                    answer = (
                        f"AWS cost summary from {source}: ${float(total):.2f} over the selected window. "
                        f"The largest driver is {driver}. Recommended control: {recommendation}."
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
            incident_context=incident_context,
            answer_sources=build_answer_sources(
                route=route,
                policy=policy,
                tool_calls=tool_calls,
                incident_context=incident_context,
                bedrock_answer_used=bedrock_answer_used,
            ),
            trace_id=trace_id,
        )


def reviewer_actor_for_role(role: Role, team: str | None = None) -> Actor:
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

    return f"Request processed through the governed CloudOps gateway. Sanitized input: {redacted_text[:180]}"


def enrich_incident_answer(answer: str, incident_context) -> str:
    return (
        f"{answer} Incident context points to {incident_context.suspected_cause} "
        f"I found {len(incident_context.entries)} relevant log entries in {incident_context.log_group}."
    )


def build_answer_sources(
    *,
    route,
    policy,
    tool_calls,
    incident_context,
    bedrock_answer_used: bool,
) -> list[AnswerSource]:
    sources: list[AnswerSource] = []

    if bedrock_answer_used:
        sources.append(
            AnswerSource(
                kind="model",
                name="Amazon Bedrock",
                detail=f"{route.model} generated the response from sanitized input.",
            )
        )
    else:
        sources.append(
            AnswerSource(
                kind="deterministic",
                name="AegisDesk deterministic responder",
                detail="Backend control-plane logic generated the response without a general LLM call.",
            )
        )

    sources.append(
        AnswerSource(
            kind="policy",
            name="OPA/Rego policy decision",
            detail=f"{policy.decision} from {policy.policy_name}: {policy.reason}.",
        )
    )

    if incident_context:
        sources.append(
            AnswerSource(
                kind="operational_context",
                name="Seeded CloudWatch-style incident logs",
                detail=(
                    f"{incident_context.incident_id}; {len(incident_context.entries)} entries "
                    f"from {incident_context.log_group}."
                ),
            )
        )

    for tool_call in tool_calls:
        if tool_call.name == "incident.context":
            continue
        if tool_call.name == "cost.summary" and tool_call.status == "allowed":
            source = str(tool_call.result.get("source") or "cost_summary")
            cache_hit = bool(tool_call.result.get("cache_hit"))
            sources.append(
                AnswerSource(
                    kind="cost",
                    name="AWS Cost Explorer cache" if cache_hit else source.replace("_", " ").title(),
                    detail=(
                        f"{tool_call.result.get('period', 'selected window')}; largest driver "
                        f"{tool_call.result.get('largest_driver', 'unknown')}."
                    ),
                )
            )
            continue
        sources.append(
            AnswerSource(
                kind="tool",
                name=f"MCP tool: {tool_call.name}",
                detail=f"Tool status {tool_call.status}; policy reason {tool_call.policy.reason}.",
            )
        )

    return sources
