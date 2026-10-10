from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import tools
from .auth import require_actor
from .knowledge_base import retrieve_knowledge
from .models import Actor, Role
from .observability import current_correlation_id, current_trace_id
from .policy_engine import PolicyUnavailable
from .redaction import inspect_and_redact
from .settings import get_settings

ActorDependency = Annotated[Actor, Depends(require_actor)]
CaseStatus = Literal[
    "open", "investigating", "awaiting_approval", "mitigating", "resolved"
]


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    service: str = Field(min_length=1, max_length=100)
    resource: str = Field(min_length=1, max_length=300)
    environment: str = Field(min_length=1, max_length=80)
    evidence_filter: str = Field(default="", max_length=80)


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


class CaseUpdate(VersionInput):
    status: CaseStatus


class NoteInput(VersionInput):
    text: str = Field(min_length=1, max_length=4000)
    kind: Literal["note", "hypothesis", "next_step"] = "note"


class ReconcileInput(VersionInput):
    ticket_key: str = Field(pattern=r"^[A-Z][A-Z0-9_]*-[0-9]+$", max_length=100)


def incident_router(store, policy_engine) -> APIRouter:
    router = APIRouter(prefix="/incidents", tags=["Incident cases"])

    def now() -> str:
        return datetime.now(UTC).isoformat()

    def clean(text: str) -> str:
        return inspect_and_redact(text).redacted_text

    def authorize(actor: Actor, ticket: bool = False):
        try:
            decision = (
                policy_engine.evaluate_tool(actor.role, "ticket", "create_ticket")
                if ticket
                else policy_engine.evaluate_chat(actor, "incident_triage")
            )
        except PolicyUnavailable as exc:
            raise HTTPException(503, "policy_unavailable_action_blocked") from exc
        if decision.decision != "allow":
            raise HTTPException(403, "policy_did_not_allow_action")
        return decision

    def load(incident_id: str, actor: Actor, version: int | None = None) -> dict:
        case = next(
            (
                case
                for case in store.list_cases(actor.team)
                if case["incident_id"] == incident_id
            ),
            None,
        )
        if case is None:
            raise HTTPException(404, "incident_not_found_in_team")
        if version is not None and case["version"] != version:
            raise HTTPException(409, "incident_changed_refresh_before_retry")
        return case

    def persist(
        case: dict, actor: Actor, event: str, detail: dict | None = None
    ) -> dict:
        version = case["version"]
        case["updated_at"] = now()
        case["version"] += 1
        case["timeline"].append(
            {
                "event_id": f"evt-{uuid4().hex}",
                "timestamp": case["updated_at"],
                "actor": actor.model_dump(mode="json"),
                "event": event,
                "detail": detail or {},
                "trace_id": current_trace_id(),
                "correlation_id": current_correlation_id(),
            }
        )
        # Leave headroom below DynamoDB's item limit; reject before any external call.
        if len(json.dumps(case).encode()) > 280_000:
            raise HTTPException(413, "incident_evidence_capacity_reached")
        try:
            store.save_case(case, version)
        except ValueError as exc:
            raise HTTPException(409, "incident_changed_refresh_before_retry") from exc
        return case

    def action_for(case: dict, action_id: str) -> dict:
        action = next(
            (item for item in case["actions"] if item["action_id"] == action_id), None
        )
        if action is None:
            raise HTTPException(404, "action_not_found")
        return action

    def unexpired(action: dict):
        if datetime.fromisoformat(action["expires_at"]) <= datetime.now(UTC):
            raise HTTPException(409, "approval_expired_propose_new_action")

    @router.get("")
    def list_incidents(actor: ActorDependency):
        cases = store.list_cases(actor.team)
        return {
            "incidents": sorted(
                cases, key=lambda case: case["updated_at"], reverse=True
            )
        }

    @router.post("", status_code=201)
    def create_case(body: CaseInput, actor: ActorDependency):
        authorize(actor)
        fields = body.model_dump()
        fields = {
            key: clean(value) if isinstance(value, str) else value
            for key, value in fields.items()
        }
        case = {
            **fields,
            "incident_id": f"INC-{uuid4().hex[:12].upper()}",
            "team": actor.team,
            "owner": actor.user_id,
            "status": "open",
            "created_at": now(),
            "updated_at": now(),
            "version": 0,
            "evidence": None,
            "evidence_state": "empty",
            "evidence_error": None,
            "evidence_checked_at": None,
            "notes": [],
            "runbooks": [
                citation.model_dump()
                for citation in retrieve_knowledge(
                    "incident_triage", fields["description"]
                )
            ],
            "actions": [],
            "external_ticket": None,
            "timeline": [],
        }
        return persist(case, actor, "incident.created")

    @router.get("/{incident_id}")
    def get_case(incident_id: str, actor: ActorDependency):
        return load(incident_id, actor)

    @router.patch("/{incident_id}")
    def update_case(incident_id: str, body: CaseUpdate, actor: ActorDependency):
        authorize(actor)
        case = load(incident_id, actor, body.version)
        transitions = {
            "open": {"investigating"},
            "investigating": {"resolved"},
            "awaiting_approval": set(),
            "mitigating": {"investigating", "resolved"},
            "resolved": {"investigating"},
        }
        if body.status not in transitions[case["status"]]:
            raise HTTPException(409, "invalid_incident_transition")
        if body.status == "resolved" and any(
            action["state"]
            in {
                "proposed",
                "pending_approval",
                "approved",
                "executing",
                "outcome_uncertain",
            }
            for action in case["actions"]
        ):
            raise HTTPException(409, "unresolved_action_outcome")
        case["status"] = body.status
        return persist(case, actor, "incident.status_changed", {"status": body.status})

    @router.post("/{incident_id}/notes")
    def add_note(incident_id: str, body: NoteInput, actor: ActorDependency):
        authorize(actor)
        case = load(incident_id, actor, body.version)
        note = {
            "text": clean(body.text),
            "kind": body.kind,
            "author": actor.user_id,
            "timestamp": now(),
            "source": "operator",
            "verified_root_cause": False,
        }
        case["notes"].append(note)
        return persist(case, actor, "investigation.note_added", {"kind": body.kind})

    @router.post("/{incident_id}/evidence")
    def refresh_evidence(incident_id: str, body: VersionInput, actor: ActorDependency):
        authorize(actor)
        case = load(incident_id, actor, body.version)
        settings = get_settings()
        context = None
        error = "Configure the CloudWatch adapter and a permitted log group. Fixture evidence is not used in incident cases."
        if (
            settings.incident_context_adapter == "cloudwatch"
            and settings.cloudwatch_log_group
        ):
            context = tools.lookup_incident_context(
                case["evidence_filter"] or None, case["description"]
            )
            error = context.suspected_cause
        case["evidence_checked_at"] = now()
        if context is None or context.source != "cloudwatch_logs":
            case["evidence_state"] = "stale" if case["evidence"] else "unavailable"
            case["evidence_error"] = clean(error)
        else:
            evidence = context.model_dump()
            evidence["entries"] = [
                {
                    **entry,
                    "message": clean(entry["message"]),
                    "service": clean(entry["service"]),
                }
                for entry in evidence["entries"]
            ]
            evidence["suspected_cause"] = clean(evidence["suspected_cause"])
            case["evidence"] = {
                "context": evidence,
                "loaded_at": now(),
                "lookback_minutes": settings.cloudwatch_query_lookback_minutes,
                "region": settings.cloudwatch_logs_region,
            }
            case["evidence_state"] = "success" if evidence["entries"] else "empty"
            case["evidence_error"] = None
        return persist(
            case,
            actor,
            "evidence.refresh",
            {"state": case["evidence_state"], "source": "cloudwatch"},
        )

    @router.post("/{incident_id}/actions", status_code=201)
    def propose_action(incident_id: str, body: VersionInput, actor: ActorDependency):
        policy = authorize(actor, ticket=True)
        case = load(incident_id, actor, body.version)
        settings = get_settings()
        if settings.ticket_adapter != "jira" or not all(
            [
                settings.jira_base_url,
                settings.jira_project_key,
                settings.jira_email,
                settings.jira_api_token,
            ]
        ):
            raise HTTPException(503, "jira_not_configured_no_fixture_ticket_created")
        if case["status"] not in {"open", "investigating"}:
            raise HTTPException(409, "investigate_before_proposing_action")
        target = f"{settings.jira_base_url.rstrip('/')}/{settings.jira_project_key}"
        if any(
            action["state"] != "failed"
            and (
                action["state"] != "pending_approval"
                or datetime.fromisoformat(action["expires_at"]) > datetime.now(UTC)
            )
            for action in case["actions"]
        ):
            raise HTTPException(409, "existing_ticket_action_requires_resolution")
        action_id = f"act-{uuid4().hex[:16]}"
        arguments = {
            "title": f"[{case['incident_id']}/{action_id}] {case['title']}"[:250],
            "team": case["team"],
            "severity": case["severity"],
        }
        provenance = {
            "operation": "ticket.create",
            "target": target,
            "arguments": arguments,
            "requester": actor.model_dump(mode="json"),
            "action_version": 1,
            "policy": policy.model_dump(),
        }
        action = {
            **provenance,
            "action_id": action_id,
            "fingerprint": hashlib.sha256(
                json.dumps(provenance, sort_keys=True).encode()
            ).hexdigest(),
            "state": "proposed",
            "created_at": now(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "approval": None,
            "outcome": None,
        }
        case["actions"].append(action)
        case["status"] = "investigating"
        return persist(
            case,
            actor,
            "action.proposed",
            {"action_id": action_id, "fingerprint": action["fingerprint"]},
        )

    @router.post("/{incident_id}/actions/{action_id}/request-approval")
    def request_approval(
        incident_id: str, action_id: str, body: VersionInput, actor: ActorDependency
    ):
        authorize(actor, ticket=True)
        case = load(incident_id, actor, body.version)
        action = action_for(case, action_id)
        if action["state"] != "proposed":
            raise HTTPException(409, "action_not_proposed")
        if actor.user_id != action["requester"]["user_id"] and actor.role not in {
            Role.manager,
            Role.admin,
        }:
            raise HTTPException(403, "requester_or_manager_required")
        unexpired(action)
        action["state"] = "pending_approval"
        case["status"] = "awaiting_approval"
        return persist(
            case, actor, "action.approval_requested", {"action_id": action_id}
        )

    @router.post("/{incident_id}/actions/{action_id}/approve")
    def approve_action(
        incident_id: str, action_id: str, body: VersionInput, actor: ActorDependency
    ):
        policy = authorize(actor, ticket=True)
        case = load(incident_id, actor, body.version)
        action = action_for(case, action_id)
        if (
            actor.role not in {Role.manager, Role.admin}
            or actor.user_id == action["requester"]["user_id"]
        ):
            raise HTTPException(403, "independent_team_manager_required")
        if action["state"] != "pending_approval":
            raise HTTPException(409, "action_not_pending_approval")
        unexpired(action)
        action["approval"] = {
            "approver": actor.model_dump(mode="json"),
            "approved_at": now(),
            "fingerprint": action["fingerprint"],
            "action_version": action["action_version"],
            "policy": policy.model_dump(),
            "expires_at": action["expires_at"],
        }
        action["state"] = "approved"
        return persist(
            case,
            actor,
            "action.approved",
            {"action_id": action_id, "fingerprint": action["fingerprint"]},
        )

    @router.post("/{incident_id}/actions/{action_id}/cancel")
    def cancel_action(
        incident_id: str, action_id: str, body: VersionInput, actor: ActorDependency
    ):
        authorize(actor)
        case = load(incident_id, actor, body.version)
        action = action_for(case, action_id)
        if action["state"] not in {"proposed", "pending_approval", "approved"}:
            raise HTTPException(409, "cannot_cancel_dispatched_action")
        if actor.user_id != action["requester"]["user_id"] and actor.role not in {
            Role.manager,
            Role.admin,
        }:
            raise HTTPException(403, "requester_or_manager_required")
        action["state"] = "failed"
        action["outcome"] = {"error": "cancelled_before_execution"}
        case["status"] = "investigating"
        return persist(case, actor, "action.cancelled", {"action_id": action_id})

    @router.post("/{incident_id}/actions/{action_id}/execute")
    def execute_action(
        incident_id: str, action_id: str, body: VersionInput, actor: ActorDependency
    ):
        policy = authorize(actor, ticket=True)
        case = load(incident_id, actor, body.version)
        action = action_for(case, action_id)
        if actor.user_id != action["requester"]["user_id"] and actor.role not in {
            Role.manager,
            Role.admin,
        }:
            raise HTTPException(403, "requester_or_manager_required")
        if (
            action["state"] != "approved"
            or not action["approval"]
            or action["approval"]["fingerprint"] != action["fingerprint"]
        ):
            raise HTTPException(409, "exact_action_approval_required")
        provenance = {
            key: action[key]
            for key in (
                "operation",
                "target",
                "arguments",
                "requester",
                "action_version",
                "policy",
            )
        }
        fingerprint = hashlib.sha256(
            json.dumps(provenance, sort_keys=True).encode()
        ).hexdigest()
        if (
            action["fingerprint"] != fingerprint
            or action["approval"]["action_version"] != action["action_version"]
            or action["approval"]["expires_at"] != action["expires_at"]
        ):
            raise HTTPException(409, "action_provenance_changed")
        unexpired(action)
        settings = get_settings()
        if (
            settings.ticket_adapter != "jira"
            or action["target"]
            != f"{(settings.jira_base_url or '').rstrip('/')}/{settings.jira_project_key}"
        ):
            raise HTTPException(409, "ticket_target_changed_new_approval_required")
        # Persist the dispatch claim before I/O. A crash leaves a reconcilable state,
        # and the conditional version write prevents concurrent duplicate dispatch.
        action["state"] = "executing"
        case["status"] = "mitigating"
        case = persist(
            case,
            actor,
            "action.executing",
            {"action_id": action_id, "policy": policy.model_dump()},
        )
        try:
            result = tools.create_ticket(policy, **action["arguments"])
            action["outcome"] = result.result
            if (
                result.status == "allowed"
                and result.result.get("ticket_id")
                and result.result.get("system") == "jira"
            ):
                action["state"] = "succeeded"
                case["external_ticket"] = result.result
                case["status"] = "mitigating"
            else:
                action["state"] = (
                    "outcome_uncertain"
                    if result.result.get("status") == "outcome_uncertain"
                    else "failed"
                )
                if action["state"] == "failed":
                    case["status"] = "investigating"
        except Exception as exc:  # noqa: BLE001 - dispatch may have occurred; every adapter failure requires reconciliation.
            action["state"] = "outcome_uncertain"
            action["outcome"] = {
                "error": "dispatch_interrupted_reconcile_before_retry",
                "failure_type": type(exc).__name__,
            }
        return persist(
            case,
            actor,
            f"action.{action['state']}",
            {"action_id": action_id, "outcome": action["outcome"]},
        )

    @router.post("/{incident_id}/actions/{action_id}/reconcile")
    def reconcile_action(
        incident_id: str, action_id: str, body: ReconcileInput, actor: ActorDependency
    ):
        authorize(actor, ticket=True)
        if actor.role not in {Role.manager, Role.admin}:
            raise HTTPException(403, "manager_required")
        case = load(incident_id, actor, body.version)
        action = action_for(case, action_id)
        if action["state"] not in {"executing", "outcome_uncertain"}:
            raise HTTPException(409, "action_not_reconcilable")
        settings = get_settings()
        if (
            settings.ticket_adapter != "jira"
            or action["target"]
            != f"{(settings.jira_base_url or '').rstrip('/')}/{settings.jira_project_key}"
        ):
            raise HTTPException(409, "ticket_target_changed")
        try:
            response = httpx.get(
                f"{settings.jira_base_url.rstrip('/')}/rest/api/3/issue/{body.ticket_key}",
                params={"fields": "summary,project"},
                auth=(settings.jira_email, settings.jira_api_token),
                timeout=settings.jira_timeout_seconds,
            )
            response.raise_for_status()
            ticket = response.json()
            if (
                ticket.get("key") != body.ticket_key
                or ticket.get("fields", {}).get("summary")
                != action["arguments"]["title"]
                or ticket.get("fields", {}).get("project", {}).get("key")
                != settings.jira_project_key
            ):
                raise ValueError("ticket_does_not_match_exact_action")
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise HTTPException(
                409, "jira_outcome_not_verified_action_remains_unresolved"
            ) from exc
        action["state"] = "succeeded"
        action["outcome"] = {
            "system": "jira",
            "ticket_id": body.ticket_key,
            "external_url": f"{settings.jira_base_url.rstrip('/')}/browse/{body.ticket_key}",
            "verified_by": actor.user_id,
        }
        case["external_ticket"] = action["outcome"]
        case["status"] = "mitigating"
        return persist(
            case,
            actor,
            "action.reconciled",
            {"action_id": action_id, "ticket_id": body.ticket_key},
        )

    return router
