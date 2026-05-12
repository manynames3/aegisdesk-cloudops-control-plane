from __future__ import annotations

import json
import logging
import subprocess
from typing import Any
from pathlib import Path

import httpx

from .models import Actor, PolicyDecision, RedactionResult, Role
from .policy import evaluate_chat_policy, evaluate_model_route, evaluate_quota_policy, evaluate_tool_policy
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
            if self.settings.opa_url:
                return "opa_http"
            if Path(self.settings.opa_executable_path).exists() and Path(self.settings.opa_policy_path).exists():
                return "opa_subprocess"
            return "python"
        if self.settings.policy_mode == "opa":
            return "opa_http" if self.settings.opa_url else "opa_subprocess"
        return self.settings.policy_mode

    def ready(self) -> dict[str, Any]:
        if self.mode == "python":
            return {"mode": self.mode, "ready": True}

        if self.mode == "opa_subprocess":
            executable = Path(self.settings.opa_executable_path)
            policies = Path(self.settings.opa_policy_path)
            return {
                "mode": self.mode,
                "ready": executable.exists() and policies.exists(),
                "executable": str(executable),
                "policy_path": str(policies),
            }

        if not self.settings.opa_url:
            return {"mode": self.mode, "ready": False, "reason": "missing_opa_url"}

        try:
            response = httpx.get(f"{self.settings.opa_url.rstrip('/')}/health", timeout=self.settings.opa_timeout_seconds)
            return {"mode": self.mode, "ready": response.status_code == 200}
        except httpx.HTTPError as exc:
            return {"mode": "opa", "ready": False, "reason": exc.__class__.__name__}

    def evaluate_chat(self, actor: Actor, intent: str) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_chat_policy(actor, intent)

        result = self._query_policy(
            "/v1/data/aegisdesk/chat_policy/decision",
            {"role": actor.role.value, "team": actor.team, "intent": intent},
        )
        return self._policy_decision(result, "chat_policy")

    def evaluate_model_route(self, redaction: RedactionResult, intent: str) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_model_route(redaction, intent)

        result = self._query_policy(
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

        result = self._query_policy(
            "/v1/data/aegisdesk/tool_authorization/decision",
            {"role": role.value, "tool": tool_name, "action": action},
        )
        return self._policy_decision(result, "tool_authorization")

    def evaluate_quota(self, actor: Actor, current_count: int) -> PolicyDecision:
        if self.mode == "python":
            return evaluate_quota_policy(actor, current_count)

        result = self._query_policy(
            "/v1/data/aegisdesk/quota/decision",
            {"role": actor.role.value, "team": actor.team, "current_count": current_count},
        )
        return self._policy_decision(result, "quota")

    def _query_policy(self, path: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        if self.mode == "opa_subprocess":
            return self._query_subprocess(path, input_payload)
        return self._query_http(path, input_payload)

    def _query_http(self, path: str, input_payload: dict[str, Any]) -> dict[str, Any]:
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

    def _query_subprocess(self, path: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        executable = Path(self.settings.opa_executable_path)
        policies = Path(self.settings.opa_policy_path)
        if not executable.exists() or not policies.exists():
            raise PolicyUnavailable("opa_subprocess_not_configured")

        query = path.removeprefix("/v1/data/").replace("/", ".")
        try:
            completed = subprocess.run(
                [
                    str(executable),
                    "eval",
                    "--format",
                    "json",
                    "--data",
                    str(policies),
                    "--stdin-input",
                    f"data.{query}",
                ],
                input=json.dumps(input_payload),
                text=True,
                capture_output=True,
                timeout=self.settings.opa_timeout_seconds,
                check=True,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            logger.warning("opa_subprocess_failed", extra={"path": path, "error": exc.__class__.__name__})
            raise PolicyUnavailable("policy_engine_unavailable") from exc

        try:
            result = json.loads(completed.stdout)["result"][0]["expressions"][0]["value"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise PolicyUnavailable("invalid_policy_response") from exc

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
