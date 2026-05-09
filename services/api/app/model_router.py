from __future__ import annotations

from .models import ModelRoute, RedactionResult


def select_model_route(
    redaction: RedactionResult,
    intent: str,
    provider_override: str | None = None,
    reason_override: str | None = None,
) -> ModelRoute:
    if provider_override:
        return _route_for_provider(provider_override, reason_override or "policy_selected_route")

    if redaction.secrets_detected:
        return _route_for_provider("local", "secrets_detected_and_redacted")

    if redaction.pii_detected:
        return _route_for_provider("local", "pii_detected_and_redacted")

    if intent in {"incident_triage", "production_admin_access", "temporary_read_only_access"}:
        return _route_for_provider("local", "internal_cloudops_context")

    return _route_for_provider("simulated-cloud", "low_sensitivity_demo_route")


def _route_for_provider(provider: str, reason: str) -> ModelRoute:
    if provider == "local":
        return ModelRoute(
            provider="local",
            model="ollama/llama3.1",
            reason=reason,
            estimated_cost_usd=0.0,
            external_call=False,
        )

    return ModelRoute(
        provider="simulated-cloud",
        model="cost-optimized-small-model",
        reason=reason,
        estimated_cost_usd=0.0008,
        external_call=False,
    )
