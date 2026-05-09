from __future__ import annotations

from .models import ModelRoute, RedactionResult


def select_model_route(redaction: RedactionResult, intent: str) -> ModelRoute:
    if redaction.secrets_detected:
        return ModelRoute(
            provider="local",
            model="ollama/llama3.1",
            reason="secrets_detected_and_redacted",
            estimated_cost_usd=0.0,
            external_call=False,
        )

    if redaction.pii_detected:
        return ModelRoute(
            provider="local",
            model="ollama/llama3.1",
            reason="pii_detected_and_redacted",
            estimated_cost_usd=0.0,
            external_call=False,
        )

    if intent in {"incident_triage", "production_admin_access", "temporary_read_only_access"}:
        return ModelRoute(
            provider="local",
            model="ollama/llama3.1",
            reason="internal_cloudops_context",
            estimated_cost_usd=0.0,
            external_call=False,
        )

    return ModelRoute(
        provider="simulated-cloud",
        model="cost-optimized-small-model",
        reason="low_sensitivity_demo_route",
        estimated_cost_usd=0.0008,
        external_call=False,
    )

