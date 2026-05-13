from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("AEGISDESK_AUTH_SECRET", "eval-auth-secret")
os.environ.setdefault("AEGISDESK_POLICY_MODE", "python")

from fastapi.testclient import TestClient  # noqa: E402

from app.auth import create_persona_token  # noqa: E402
from app.main import app, store  # noqa: E402
from app.models import Actor, Role  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    return json.loads((Path(__file__).with_name("control_cases.json")).read_text())


def check_case(case: dict[str, Any], client: TestClient) -> list[str]:
    store.reset()
    payload = {
        "message": case["message"],
        "context": {"eval_case": case["id"]},
    }
    user = case["user"]
    actor = Actor(user_id=user["user_id"], role=Role(user["role"]), team=user["team"])
    headers = {"Authorization": f"Bearer {create_persona_token(actor)}"}
    response = client.post("/chat", headers=headers, json=payload)
    failures: list[str] = []

    if response.status_code != 200:
        return [f"expected HTTP 200, got {response.status_code}: {response.text}"]

    body = response.json()
    expected = case["expect"]

    assertions = {
        "policy_decision": body["policy"]["decision"],
        "model_provider": body["model_route"]["provider"],
        "secrets_detected": body["redaction"]["secrets_detected"],
        "pii_detected": body["redaction"]["pii_detected"],
    }

    if body["tool_calls"]:
        assertions["tool_name"] = body["tool_calls"][0]["name"]
        assertions["tool_status"] = body["tool_calls"][0]["status"]

    if "pending_approvals" in expected:
        admin = Actor(user_id="u-eval-admin", role=Role.admin, team="platform")
        admin_headers = {"Authorization": f"Bearer {create_persona_token(admin)}"}
        metrics = client.get("/metrics/summary", headers=admin_headers).json()
        assertions["pending_approvals"] = metrics["approvals_pending"]

    for key, expected_value in expected.items():
        actual_value = assertions.get(key)
        if actual_value != expected_value:
            failures.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")

    return failures


def main() -> int:
    client = TestClient(app)
    cases = load_cases()
    failed = 0

    print("# AegisDesk Control Evals")
    print()

    for case in cases:
        failures = check_case(case, client)
        if failures:
            failed += 1
            print(f"- FAIL {case['id']}")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(f"- PASS {case['id']}")

    print()
    print(f"Result: {len(cases) - failed}/{len(cases)} passing")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
