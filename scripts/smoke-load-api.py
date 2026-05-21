#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import statistics
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_persona_token  # noqa: E402
from app.main import app, store  # noqa: E402
from app.models import Actor, Role  # noqa: E402


logging.getLogger("aegisdesk.api").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


PROMPTS = [
    {"message": "The checkout service is timing out. What should I check first?", "context": {"incident_id": "INC-1042"}},
    {"message": "Create a SEV-2 ticket for VPN outage. Impact: remote users cannot connect. Assign to CloudOps."},
    {"message": "I need temporary read-only access to production payments database for INC-1042. Duration: 2 hours. Business reason: inspect connection pool metrics."},
    {"message": "What is the safest way to ask for help with a CloudOps issue?"},
]


def auth_headers(role: Role = Role.employee, team: str = "payments", user_id: str = "u-load") -> dict[str, str]:
    token = create_persona_token(Actor(user_id=user_id, role=role, team=team))
    return {"Authorization": f"Bearer {token}"}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def main() -> int:
    store.reset()
    client = TestClient(app)
    durations_ms: list[float] = []
    failures: list[dict[str, object]] = []
    total_requests = 20

    for index in range(total_requests):
        payload = PROMPTS[index % len(PROMPTS)]
        role = Role.manager if "cloud costs" in payload["message"].lower() else Role.employee
        started = time.perf_counter()
        response = client.post(
            "/chat",
            headers=auth_headers(role=role, user_id=f"u-load-{index}"),
            json=payload,
        )
        durations_ms.append((time.perf_counter() - started) * 1000)
        if response.status_code >= 500:
            failures.append({"index": index, "status": response.status_code, "body": response.text[:300]})

    result = {
        "requests": total_requests,
        "failures": len(failures),
        "p50_ms": round(statistics.median(durations_ms), 2),
        "p95_ms": round(percentile(durations_ms, 95), 2),
        "max_ms": round(max(durations_ms), 2),
        "store_metrics": store.metrics().model_dump(mode="json"),
    }
    print(json.dumps(result, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
