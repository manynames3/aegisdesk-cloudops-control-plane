from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .settings import Settings


class CostExplorerUnavailable(Exception):
    pass


def get_cost_summary(settings: Settings, store: Any, period_days: int = 7) -> dict[str, Any]:
    cache_key = (
        f"cost-summary:v1:{settings.cost_explorer_scope}:"
        f"{settings.cost_explorer_tag_key}:{settings.cost_explorer_tag_value}:{period_days}"
    )
    cached = store.get_cache(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["cache_hit"] = True
        return payload

    if not settings.enable_cost_explorer:
        payload = _fallback_summary("cost_explorer_disabled", period_days)
        store.set_cache(cache_key, json.dumps(payload), settings.cost_cache_ttl_seconds)
        return payload

    payload = _query_cost_explorer(settings, period_days)
    store.set_cache(cache_key, json.dumps(payload), settings.cost_cache_ttl_seconds)
    return payload


def _query_cost_explorer(settings: Settings, period_days: int) -> dict[str, Any]:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=period_days)
    request: dict[str, Any] = {
        "TimePeriod": {"Start": start.isoformat(), "End": end.isoformat()},
        "Granularity": "DAILY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
    }
    if settings.cost_explorer_scope == "tagged":
        request["Filter"] = {
            "Tags": {
                "Key": settings.cost_explorer_tag_key,
                "Values": [settings.cost_explorer_tag_value],
                "MatchOptions": ["EQUALS"],
            }
        }

    client = boto3.client("ce", region_name="us-east-1")
    try:
        response = client.get_cost_and_usage(**request)
    except (BotoCoreError, ClientError) as exc:
        raise CostExplorerUnavailable("cost_explorer_unavailable") from exc

    by_service: dict[str, Decimal] = {}
    for result in response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service = group.get("Keys", ["Unknown"])[0]
            amount = Decimal(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount", "0"))
            by_service[service] = by_service.get(service, Decimal("0")) + amount

    total = sum(by_service.values(), Decimal("0"))
    largest_service = max(by_service, key=by_service.get, default="No tagged spend returned")
    largest_amount = by_service.get(largest_service, Decimal("0"))

    return {
        "period": f"last_{period_days}_days",
        "source": "aws_cost_explorer",
        "scope": settings.cost_explorer_scope,
        "cache_hit": False,
        "cache_ttl_seconds": settings.cost_cache_ttl_seconds,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_usd": round(float(total), 4),
        "largest_driver": largest_service,
        "largest_driver_usd": round(float(largest_amount), 4),
        "recommendation": _recommendation(largest_service, total),
        "estimated_savings_usd": round(float(total) * 0.2, 4),
    }


def _fallback_summary(reason: str, period_days: int) -> dict[str, Any]:
    return {
        "period": f"last_{period_days}_days",
        "source": "local_fallback",
        "reason": reason,
        "cache_hit": False,
        "cache_ttl_seconds": 0,
        "total_usd": 184.72,
        "largest_driver": "cloud model experimentation",
        "largest_driver_usd": 91.18,
        "recommendation": "route repeated low-value prompts locally or cache approved answers",
        "estimated_savings_usd": 37.4,
    }


def _recommendation(largest_service: str, total: Decimal) -> str:
    if total == 0:
        return "No tagged AWS spend returned for this window; verify cost allocation tags or widen the scope."
    if "Bedrock" in largest_service:
        return "review model routing, cache repeat prompts, and require approval for high-cost model classes"
    if "CloudFront" in largest_service or "Data Transfer" in largest_service:
        return "review cache hit ratio and static asset expiration policy"
    if "Lambda" in largest_service:
        return "review cold starts, timeout settings, and expensive downstream retries"
    return "review tagged service drivers and compare against the policy and routing audit trail"
