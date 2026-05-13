from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .auth import AuthError, create_demo_token, decode_token, jwks_document, require_actor, require_admin, require_manager_or_admin
from .clarification import assess_clarification, build_clarification_answer
from .cognito_auth import CognitoSessionError, create_persona_session, ensure_persona_user, exchange_oauth_code
from .cost_explorer import CostExplorerUnavailable, get_cost_summary
from .incident_context import lookup_incident_context
from .knowledge_base import format_knowledge_context, retrieve_knowledge, summarize_knowledge_guidance
from .llm import LLMUnavailable, maybe_generate_with_bedrock
from .model_router import select_model_route
from .models import (
    Actor,
    AnswerSource,
    ApprovalList,
    AbuseControls,
    AuditEvent,
    ChatRequest,
    ChatResponse,
    ClarificationResult,
    EventList,
    HealthResponse,
    HostedAuthConfig,
    HostedLoginResponse,
    OAuthExchangeRequest,
    OAuthExchangeResponse,
    PersonaTokenRequest,
    PersonaTokenResponse,
    RequestReplay,
    Role,
    TrustedSourceScore,
)
from .observability import configure_observability, current_trace_id, tracer
from .policy import QUOTA_LIMITS_BY_ROLE, classify_intent
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


@app.get("/requests/{request_id}/replay", response_model=RequestReplay)
def request_replay(request_id: str, _actor: Annotated[Actor, Depends(require_manager_or_admin)]) -> RequestReplay:
    request_events = [event for event in store.events if event.request_id == request_id]
    if not request_events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")
    return build_request_replay(request_id, request_events)


@app.get("/metrics/summary")
def metrics(_actor: Annotated[Actor, Depends(require_admin)]):
    return store.metrics()


@app.get("/controls/abuse", response_model=AbuseControls)
def abuse_controls(_actor: Annotated[Actor, Depends(require_manager_or_admin)]) -> AbuseControls:
    return AbuseControls(
        api_gateway_throttling_rate_limit=settings.api_throttling_rate_limit,
        api_gateway_throttling_burst_limit=settings.api_throttling_burst_limit,
        max_request_chars=settings.max_request_chars,
        quota_window_seconds=settings.quota_window_seconds,
        role_quotas={role.value: limit for role, limit in QUOTA_LIMITS_BY_ROLE.items()},
        cloud_model_kill_switch=settings.cloud_model_kill_switch,
        bedrock_enabled=settings.enable_bedrock,
        request_body_limit_note="Application rejects oversized prompts before policy/model routing; API Gateway enforces route throttles.",
    )


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
            ChatRequest(
                message=(
                    "Create a SEV-2 ticket for the VPN outage affecting remote employees. "
                    "Impact: users cannot connect to corporate VPN. Assign it to CloudOps."
                )
            ),
        ),
        (
            reviewer_actor_for_role(Role.employee, "payments"),
            ChatRequest(message="Give me admin access to the production database.", context={"incident_id": "INC-1042"}),
        ),
        (
            reviewer_actor_for_role(Role.employee, "payments"),
            ChatRequest(
                message=(
                    "I need temporary read-only access to the production payments database for INC-1042. "
                    "Duration: 2 hours. Business reason: inspect connection pool metrics during active incident. "
                    "Approver: payments manager."
                ),
                context={"incident_id": "INC-1042"},
            ),
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

        if len(request.message) > settings.max_request_chars:
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="request.rejected",
                    summary="Request rejected before routing because it exceeded the prompt size limit.",
                    metadata={
                        "limit_chars": settings.max_request_chars,
                        "actual_chars": len(request.message),
                        "control": "max_request_chars",
                    },
                    trace_id=trace_id,
                )
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"request_message_exceeds_{settings.max_request_chars}_chars",
            )

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

        with tracer.start_as_current_span("aegisdesk.redaction"):
            redaction = inspect_and_redact(request.message)
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="request.received",
                summary="CloudOps request received and stored with sanitized replay data.",
                metadata={
                    "team": actor.team,
                    "prompt_preview": _preview(redaction.redacted_text, 240),
                    "sanitized_prompt": redaction.redacted_text,
                },
                trace_id=trace_id,
            )
        )
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="redaction.completed",
                summary="Prompt redaction completed before policy and model routing.",
                metadata={
                    "pii_detected": redaction.pii_detected,
                    "secrets_detected": redaction.secrets_detected,
                    "findings": [finding.label for finding in redaction.findings],
                    "sanitized_prompt": redaction.redacted_text,
                },
                trace_id=trace_id,
            )
        )
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
        clarification = assess_clarification(intent, request, actor)
        knowledge_citations = retrieve_knowledge(intent, redaction.redacted_text)
        policy_input = {
            "actor": actor.model_dump(mode="json"),
            "intent": intent,
            "clarification": clarification.model_dump(mode="json"),
            "redaction": {
                "pii_detected": redaction.pii_detected,
                "secrets_detected": redaction.secrets_detected,
            },
            "team": actor.team,
        }
        if clarification.status != "complete":
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="clarification.requested",
                    summary="Request needs additional details before a sensitive tool action can run.",
                    metadata={
                        "intent": intent,
                        "status": clarification.status,
                        "risk_level": clarification.risk_level,
                        "missing_fields": clarification.missing_fields,
                        "questions": clarification.questions,
                        "blocks_tool_call": clarification.blocks_tool_call,
                        "reason": clarification.reason,
                    },
                    trace_id=trace_id,
                )
            )
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
        if route.provider == "bedrock" and settings.cloud_model_kill_switch:
            route = route.model_copy(
                update={
                    "provider": "local",
                    "model": "kill-switch-local-fallback",
                    "reason": "cloud_model_kill_switch_enabled",
                    "estimated_cost_usd": 0.0,
                    "external_call": False,
                }
            )
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="model.kill_switch_applied",
                    summary="Cloud model kill switch forced local routing before any external model call.",
                    metadata={"original_provider": "bedrock", "fallback_model": route.model},
                    trace_id=trace_id,
                )
            )

        if clarification.status != "complete":
            route = route.model_copy(
                update={
                    "provider": "local",
                    "model": "clarification-required-local-responder",
                    "reason": "clarification_required_before_action_or_external_model",
                    "estimated_cost_usd": 0.0,
                    "external_call": False,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            )
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="model.route.adjusted",
                    summary="Clarification requirement forced local response before any external model call.",
                    metadata={
                        "intent": intent,
                        "clarification_status": clarification.status,
                        "missing_fields": clarification.missing_fields,
                    },
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
                    metadata={
                        "intent": intent,
                        "reason": policy.reason,
                        "policy_engine": policy_engine.mode,
                        "policy_input": policy_input,
                        "policy_output": policy.model_dump(mode="json"),
                    },
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
                    metadata={
                        "intent": intent,
                        "reason": policy.reason,
                        "policy_engine": policy_engine.mode,
                        "policy_input": policy_input,
                        "policy_output": policy.model_dump(mode="json"),
                    },
                    trace_id=trace_id,
                )
            )

        tool_calls = []
        incident_context = None
        answer = build_answer(intent, redaction.redacted_text, policy.decision)
        if clarification.status != "complete":
            answer = build_clarification_answer(intent, clarification, policy.decision)
        bedrock_answer_used = False

        incident_id = _incident_id_from_request(request)
        if intent == "incident_triage" and incident_id:
            incident_context = lookup_incident_context(
                incident_id,
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

        if knowledge_citations:
            store.add_event(
                AuditEvent(
                    request_id=request_id,
                    actor=actor,
                    event_type="knowledge.retrieved",
                    summary="Trusted internal knowledge documents retrieved for answer grounding.",
                    metadata={
                        "documents": [citation.doc_id for citation in knowledge_citations],
                        "titles": [citation.title for citation in knowledge_citations],
                    },
                    trace_id=trace_id,
                )
            )
            answer = f"{answer}{summarize_knowledge_guidance(intent, knowledge_citations)}"

        if policy.decision == "allow" and clarification.status == "complete":
            try:
                bedrock_answer, route = maybe_generate_with_bedrock(
                    route,
                    sanitized_input=redaction.redacted_text,
                    intent=intent,
                    knowledge_context=format_knowledge_context(knowledge_citations),
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
                    "estimated_cost_usd": route.estimated_cost_usd,
                },
                trace_id=trace_id,
            )
        )

        try:
            if intent == "create_ticket" and not clarification.blocks_tool_call:
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
                    bedrock_answer_used = False
                    answer = (
                        f"Ticket {tool_call.result['ticket_id']} was created for {actor.team} with medium severity."
                        f"{summarize_knowledge_guidance(intent, knowledge_citations)}"
                    )

            if intent == "production_admin_access" and not clarification.blocks_tool_call:
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
                bedrock_answer_used = False
                answer = (
                    "Production admin access was denied. A safer temporary read-only access request "
                    f"was opened for manager approval: {approval.approval_id}."
                    f"{summarize_knowledge_guidance(intent, knowledge_citations)}"
                )

            if intent == "temporary_read_only_access" and not clarification.blocks_tool_call:
                tool_policy = policy_engine.evaluate_tool(actor.role, "access", "request_temporary_read_only")
                tool_call, approval = request_read_only_access(
                    request_id,
                    actor.user_id,
                    actor.role,
                    actor.team,
                    "Scoped temporary read-only production access request.",
                    tool_policy,
                )
                tool_calls.append(tool_call)
                store.add_approval(approval)
                store.add_event(
                    AuditEvent(
                        request_id=request_id,
                        actor=actor,
                        event_type="approval.requested",
                        summary="Scoped temporary read-only access was sent for manager approval.",
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
                bedrock_answer_used = False
                answer = (
                    "Temporary read-only access was routed to a manager for approval. "
                    f"Approval request: {approval.approval_id}."
                    f"{summarize_knowledge_guidance(intent, knowledge_citations)}"
                )

            if intent == "cost_investigation" and not clarification.blocks_tool_call:
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
                    bedrock_answer_used = False
                    source = tool_call.result.get("source", "cost_summary")
                    total = tool_call.result.get("total_usd", 0)
                    driver = tool_call.result.get("largest_driver", "unknown service")
                    recommendation = str(tool_call.result.get("recommendation", "review cost drivers")).rstrip(".")
                    answer = (
                        f"AWS cost summary from {source}: ${float(total):.2f} over the selected window. "
                        f"The largest driver is {driver}. Recommended control: {recommendation}."
                    )
                    answer = f"{answer}{summarize_knowledge_guidance(intent, knowledge_citations)}"
                else:
                    bedrock_answer_used = False
                    answer = f"Cost investigation requires manager or admin access.{summarize_knowledge_guidance(intent, knowledge_citations)}"
        except PolicyUnavailable as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        answer_sources = build_answer_sources(
            route=route,
            policy=policy,
            tool_calls=tool_calls,
            incident_context=incident_context,
            knowledge_citations=knowledge_citations,
            clarification=clarification,
            bedrock_answer_used=bedrock_answer_used,
        )
        trusted_source_score = build_trusted_source_score(
            redaction=redaction,
            policy=policy,
            route=route,
            answer_sources=answer_sources,
            knowledge_citations=knowledge_citations,
        )
        response = ChatResponse(
            request_id=request_id,
            answer=answer,
            model_route=route,
            redaction=redaction,
            policy=policy,
            tool_calls=tool_calls,
            incident_context=incident_context,
            knowledge_citations=knowledge_citations,
            answer_sources=answer_sources,
            clarification=clarification,
            trusted_source_score=trusted_source_score,
            trace_id=trace_id,
        )
        store.add_event(
            AuditEvent(
                request_id=request_id,
                actor=actor,
                event_type="response.completed",
                summary="Response snapshot persisted for trace replay.",
                metadata={
                    "snapshot": build_replay_snapshot(
                        actor=actor,
                        request_id=request_id,
                        trace_id=trace_id,
                        sanitized_prompt=redaction.redacted_text,
                        policy_input=policy_input,
                        response=response,
                    ),
                    "trusted_source_score": trusted_source_score.model_dump(mode="json"),
                },
                trace_id=trace_id,
            )
        )
        return response


def build_request_replay(request_id: str, request_events: list[AuditEvent]) -> RequestReplay:
    ordered_events = sorted(request_events, key=lambda event: (event.timestamp, event.event_id))
    response_event = next((event for event in reversed(ordered_events) if event.event_type == "response.completed"), None)
    snapshot = response_event.metadata.get("snapshot") if response_event and isinstance(response_event.metadata, dict) else None
    if isinstance(snapshot, dict):
        return RequestReplay(
            request_id=request_id,
            trace_id=str(snapshot.get("trace_id") or ordered_events[0].trace_id),
            actor=snapshot.get("actor") or ordered_events[0].actor,
            prompt=snapshot.get("prompt"),
            sanitized_prompt=snapshot.get("sanitized_prompt"),
            redaction=snapshot.get("redaction"),
            policy_input=snapshot.get("policy_input") if isinstance(snapshot.get("policy_input"), dict) else {},
            policy=snapshot.get("policy"),
            model_route=snapshot.get("model_route"),
            tool_calls=snapshot.get("tool_calls") if isinstance(snapshot.get("tool_calls"), list) else [],
            answer_sources=snapshot.get("answer_sources") if isinstance(snapshot.get("answer_sources"), list) else [],
            knowledge_citations=snapshot.get("knowledge_citations") if isinstance(snapshot.get("knowledge_citations"), list) else [],
            clarification=snapshot.get("clarification"),
            trusted_source_score=snapshot.get("trusted_source_score"),
            answer_preview=snapshot.get("answer_preview"),
            audit_events=ordered_events,
        )

    request_event = next((event for event in ordered_events if event.event_type == "request.received"), ordered_events[0])
    redaction_event = next((event for event in ordered_events if event.event_type == "redaction.completed"), None)
    policy_event = next(
        (event for event in ordered_events if event.event_type in {"policy.allowed", "policy.denied", "approval.requested"}),
        None,
    )
    route_event = next((event for event in ordered_events if event.event_type == "model.route.selected"), None)

    route = None
    if route_event:
        route = {
            "provider": route_event.metadata.get("provider", "unknown"),
            "model": route_event.metadata.get("model", "unknown"),
            "reason": route_event.metadata.get("reason", "unknown"),
            "estimated_cost_usd": route_event.metadata.get("estimated_cost_usd", 0),
            "external_call": route_event.metadata.get("external_call", False),
            "input_tokens": route_event.metadata.get("input_tokens", 0),
            "output_tokens": route_event.metadata.get("output_tokens", 0),
        }

    return RequestReplay(
        request_id=request_id,
        trace_id=ordered_events[0].trace_id,
        actor=ordered_events[0].actor,
        prompt=request_event.metadata.get("prompt_preview") if isinstance(request_event.metadata, dict) else None,
        sanitized_prompt=redaction_event.metadata.get("sanitized_prompt") if redaction_event else None,
        policy_input=policy_event.metadata.get("policy_input") if policy_event and isinstance(policy_event.metadata.get("policy_input"), dict) else {},
        policy=policy_event.metadata.get("policy_output") if policy_event else None,
        model_route=route,
        audit_events=ordered_events,
    )


def build_replay_snapshot(
    *,
    actor: Actor,
    request_id: str,
    trace_id: str,
    sanitized_prompt: str,
    policy_input: dict,
    response: ChatResponse,
) -> dict:
    return {
        "request_id": request_id,
        "trace_id": trace_id,
        "actor": actor.model_dump(mode="json"),
        "prompt": _preview(sanitized_prompt, 500),
        "sanitized_prompt": sanitized_prompt,
        "redaction": response.redaction.model_dump(mode="json"),
        "policy_input": policy_input,
        "policy": response.policy.model_dump(mode="json"),
        "model_route": response.model_route.model_dump(mode="json"),
        "tool_calls": [tool.model_dump(mode="json") for tool in response.tool_calls],
        "answer_sources": [source.model_dump(mode="json") for source in response.answer_sources],
        "knowledge_citations": [citation.model_dump(mode="json") for citation in response.knowledge_citations],
        "clarification": response.clarification.model_dump(mode="json") if response.clarification else None,
        "trusted_source_score": response.trusted_source_score.model_dump(mode="json"),
        "answer_preview": _preview(response.answer, 1000),
    }


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
    knowledge_citations,
    clarification: ClarificationResult,
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

    if clarification.status != "complete":
        sources.append(
            AnswerSource(
                kind="clarification",
                name="Risk-based clarification policy",
                detail=(
                    f"{clarification.status}; missing "
                    f"{', '.join(clarification.missing_fields) or 'required context'}."
                ),
            )
        )

    for citation in knowledge_citations:
        sources.append(
            AnswerSource(
                kind="knowledge",
                name=f"{citation.title} ({citation.doc_id})",
                detail=f"{citation.section}; owner {citation.owner}; reviewed {citation.last_reviewed}.",
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


def build_trusted_source_score(
    *,
    redaction,
    policy,
    route,
    answer_sources: list[AnswerSource],
    knowledge_citations,
) -> TrustedSourceScore:
    trusted_source_found = any(
        source.trusted and source.kind in {"knowledge", "operational_context", "cost"} for source in answer_sources
    )
    source_freshness = _source_freshness(knowledge_citations)
    external_model_used = bool(route.external_call and route.provider == "bedrock")
    sensitive_data_sent_externally = bool(external_model_used and (redaction.pii_detected or redaction.secrets_detected))
    rationale: list[str] = []
    score = 35

    if trusted_source_found:
        score += 25
        rationale.append("Answer is grounded in internal runbook, policy, operational, or cost data.")
    else:
        rationale.append("No trusted internal source was attached to this answer.")

    if source_freshness == "fresh":
        score += 15
        rationale.append("Attached knowledge sources were reviewed within the freshness window.")
    elif source_freshness == "stale":
        score += 5
        rationale.append("At least one attached knowledge source is outside the freshness window.")
    else:
        rationale.append("No reviewed knowledge source date was available.")

    if policy.decision == "allow":
        score += 15
        rationale.append("OPA policy allowed the request.")
    elif policy.decision == "approval_required":
        score += 8
        rationale.append("OPA required human approval before the sensitive action can proceed.")
    else:
        rationale.append("OPA denied the requested action.")

    if sensitive_data_sent_externally:
        rationale.append("Sensitive data was detected on a request that attempted an external model route.")
    else:
        score += 10
        rationale.append("No detected sensitive values were sent to an external model.")

    if external_model_used:
        rationale.append("Amazon Bedrock was used only after policy and redaction controls completed.")
    else:
        rationale.append("The answer did not require an external model call.")

    return TrustedSourceScore(
        score=min(score, 100),
        trusted_source_found=trusted_source_found,
        source_freshness=source_freshness,
        external_model_used=external_model_used,
        sensitive_data_sent_externally=sensitive_data_sent_externally,
        policy_result=policy.decision,
        rationale=rationale,
    )


def _source_freshness(knowledge_citations) -> str:
    if not knowledge_citations:
        return "unknown"

    reviewed_dates = []
    for citation in knowledge_citations:
        try:
            reviewed_at = datetime.fromisoformat(citation.last_reviewed)
        except ValueError:
            return "unknown"
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=UTC)
        reviewed_dates.append(reviewed_at)

    oldest_days = max((datetime.now(UTC) - reviewed_at).days for reviewed_at in reviewed_dates)
    return "fresh" if oldest_days <= 365 else "stale"


def _incident_id_from_request(request: ChatRequest) -> str | None:
    context_incident_id = request.context.get("incident_id")
    if context_incident_id:
        return str(context_incident_id)

    match = re.search(r"\binc[-_ ]?(\d{3,})\b", request.message, re.IGNORECASE)
    if match:
        return f"INC-{match.group(1)}"

    return None


def _preview(value: str, limit: int = 240) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3].rstrip()}..."
