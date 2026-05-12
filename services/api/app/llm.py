from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from .models import ModelRoute
from .settings import Settings

logger = logging.getLogger("aegisdesk.llm")


class LLMUnavailable(Exception):
    pass


def maybe_generate_with_bedrock(
    route: ModelRoute,
    *,
    sanitized_input: str,
    intent: str,
    knowledge_context: str | None,
    settings: Settings,
) -> tuple[str | None, ModelRoute]:
    if route.provider != "bedrock":
        return None, route

    if not settings.enable_bedrock:
        fallback_route = route.model_copy(
            update={
                "provider": "simulated-cloud",
                "model": "bedrock-disabled-deterministic-fallback",
                "external_call": False,
                "estimated_cost_usd": 0.0008,
            }
        )
        return None, fallback_route

    prompt = _build_cloudops_prompt(sanitized_input, intent, knowledge_context)
    client = boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        config=Config(
            connect_timeout=settings.bedrock_timeout_seconds,
            read_timeout=settings.bedrock_timeout_seconds,
            retries={"max_attempts": 1},
        ),
    )

    try:
        response = client.converse(
            modelId=settings.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": settings.bedrock_max_tokens, "temperature": 0.1},
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning("bedrock_converse_failed", extra={"error": exc.__class__.__name__})
        raise LLMUnavailable("bedrock_unavailable") from exc

    answer = _extract_text(response)
    usage = response.get("usage", {})
    input_tokens = int(usage.get("inputTokens", 0) or 0)
    output_tokens = int(usage.get("outputTokens", 0) or 0)
    estimated_cost = _estimate_bedrock_cost(input_tokens, output_tokens, settings)

    return answer, route.model_copy(
        update={
            "model": settings.bedrock_model_id,
            "estimated_cost_usd": estimated_cost,
            "external_call": True,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    )


def _build_cloudops_prompt(sanitized_input: str, intent: str, knowledge_context: str | None) -> str:
    trusted_context = knowledge_context or "No trusted internal knowledge excerpt was retrieved for this request."
    return (
        "You are AegisDesk, a concise CloudOps assistant inside a governed enterprise AI gateway. "
        "Answer in 2-4 sentences. Do not invent tool results, secrets, ticket IDs, or approvals. "
        "Use the trusted internal knowledge excerpts when they are relevant. "
        "Mention that sensitive values are redacted when relevant.\n\n"
        f"Intent: {intent}\n"
        f"Sanitized user request: {sanitized_input}\n\n"
        f"Trusted internal knowledge excerpts:\n{trusted_context}"
    )


def _extract_text(response: dict[str, Any]) -> str:
    content = response.get("output", {}).get("message", {}).get("content", [])
    text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
    text = " ".join(part.strip() for part in text_parts if part.strip())
    return text or "Bedrock returned an empty response."


def _estimate_bedrock_cost(input_tokens: int, output_tokens: int, settings: Settings) -> float:
    input_cost = (input_tokens / 1_000_000) * settings.bedrock_input_price_per_1m_tokens
    output_cost = (output_tokens / 1_000_000) * settings.bedrock_output_price_per_1m_tokens
    return round(input_cost + output_cost, 6)
