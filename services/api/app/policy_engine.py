from __future__ import annotations

import logging
from typing import Any

import httpx

from .models import Actor, PolicyDecision, RedactionResult, Role
from .policy import evaluate_chat_policy, evaluate_model_route, evaluate_tool_policy
from .settings import get_settings

logger = logging.getLogger("aegisdesk.policy")


class PolicyUnavailable(Exception):
    pass


class PolicyEngine:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def mode(self) -> str:
        if self.settings.policy_mode == "auto":
            return "opa" if self.settings.opa_url else "python"
        return self.settings.policy_mode

    def ready(self) -> dict[str, Any]:
        if self.mode != "opa":
            return {"mode": self.mode, "ready": True}

        if not self.settings.opa_url:
            return {"mode": "opa", "ready": False, "reason": "missing_opa_url"}

        try:
            response = httpx.get(f"{self.settings.opa_url.rstrip('/')}/health", timeout=self.settings.opa_timeout_seconds)
            return {"mode": "opa", "ready": response.status_code == 200}
        except httpx.HTTPError as exc:
            return {"mode": "opa", "ready": False, "reason": exc.__class__.__name__}

    def evaluate_chat(self, actor: Actor, intent: str) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_chat_policy(actor, intent)

        result = self._query(
            "/v1/data/aegisdesk/chat_policy/decision",
            {"role": actor.role.value, "team": actor.team, "intent": intent},
        )
        return self._policy_decision(result, "chat_policy")

    def evaluate_model_route(self, redaction: RedactionResult, intent: str) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_model_route(redaction, intent)

        result = self._query(
            "/v1/data/aegisdesk/model_routing/decision",
            {
                "pii_detected": redaction.pii_detected,
                "secrets_detected": redaction.secrets_detected,
                "intent": intent,
            },
        )
        return self._policy_decision(result, "model_routing")

    def evaluate_tool(self, role: Role, tool_name: str, action: str) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_tool_policy(role, tool_name, action)

        result = self._query(
            "/v1/data/aegisdesk/tool_authorization/decision",
            {"role": role.value, "tool": tool_name, "action": action},
        )
        return self._policy_decision(result, "tool_authorization")

    def _query(self, path: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.opa_url:
            raise PolicyUnavailable("opa_url_not_configured")

        url = f"{self.settings.opa_url.rstrip('/')}{path}"
        try:
            response = httpx.post(url, json={"input": input_payload}, timeout=self.settings.opa_timeout_seconds)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("opa_query_failed", extra={"path": path, "error": exc.__class__.__name__})
            raise PolicyUnavailable("policy_engine_unavailable") from exc

        result = response.json().get("result")
        if not isinstance(result, dict):
            raise PolicyUnavailable("invalid_policy_response")
        return result

    @staticmethod
    def _policy_decision(result: dict[str, Any], policy_name: str) -> PolicyDecision:
        metadata = {key: value for key, value in result.items() if key not in {"decision", "reason"}}
        return PolicyDecision(
            decision=result.get("decision", "deny"),
            reason=result.get("reason", "missing_policy_reason"),
            policy_name=policy_name,
            metadata=metadata,
        )
