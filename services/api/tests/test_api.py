from fastapi.testclient import TestClient

from app.auth import create_demo_token
from app.main import app, store
from app.models import Actor, Role
from app.redaction import inspect_and_redact


client = TestClient(app)


def auth_headers(role: Role = Role.employee, team: str = "payments", user_id: str = "u-test") -> dict[str, str]:
    token = create_demo_token(Actor(user_id=user_id, role=role, team=team))
    return {"Authorization": f"Bearer {token}"}


def setup_function():
    store.reset()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_store_and_policy_status():
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["details"]["store"]["ready"] is True
    assert response.json()["details"]["policy"]["ready"] is True


def test_redaction_detects_pii_and_secret():
    result = inspect_and_redact("email jane@example.com token=abc123456")

    assert result.pii_detected is True
    assert result.secrets_detected is True
    assert "[REDACTED_EMAIL]" in result.redacted_text
    assert "[REDACTED_CREDENTIAL]" in result.redacted_text


def test_chat_requires_bearer_token():
    response = client.post("/chat", json={"message": "Create a ticket."})

    assert response.status_code == 401


def test_role_spoofing_in_body_is_ignored():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, user_id="u-employee"),
        json={
            "user_id": "u-spoofed-admin",
            "role": "admin",
            "team": "platform",
            "message": "Why did our AI and cloud costs spike this week?",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "approval_required"
    assert body["tool_calls"][0]["status"] == "approval_required"


def test_admin_access_request_is_denied_and_creates_approval():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1001"),
        json={
            "message": "Give me admin access to the production database.",
            "context": {"incident_id": "INC-1042"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "deny"
    assert body["tool_calls"][0]["status"] == "approval_required"
    assert client.get("/metrics/summary", headers=auth_headers(Role.admin)).json()["approvals_pending"] == 1


def test_employee_can_create_ticket():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="cloudops", user_id="u-1002"),
        json={"message": "Create a ticket for the VPN outage and assign it to CloudOps."},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["tool_calls"][0]["name"] == "ticket.create"
    assert body["tool_calls"][0]["status"] == "allowed"
    assert body["tool_calls"][0]["result"]["ticket_id"].startswith("TCK-")


def test_timing_out_prompt_routes_as_incident_triage():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1003"),
        json={"message": "The checkout service is timing out. What should I check first?"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["reason"] == "incident_triage_allowed_for_employee"
    assert body["model_route"]["provider"] == "local"


def test_employee_cannot_approve_pending_access_request():
    client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1001"),
        json={"message": "Give me admin access to the production database."},
    )
    approval_id = client.get("/approvals", headers=auth_headers(Role.manager)).json()["approvals"][0]["approval_id"]

    response = client.post(f"/approvals/{approval_id}/approve", headers=auth_headers(Role.employee))

    assert response.status_code == 403


def test_governance_endpoints_require_admin_role():
    employee_events = client.get("/events", headers=auth_headers(Role.employee))
    employee_metrics = client.get("/metrics/summary", headers=auth_headers(Role.employee))
    manager_approvals = client.get("/approvals", headers=auth_headers(Role.manager))

    assert employee_events.status_code == 403
    assert employee_metrics.status_code == 403
    assert manager_approvals.status_code == 200


def test_approval_decisions_are_pending_only():
    client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1001"),
        json={"message": "Give me admin access to the production database."},
    )
    approval_id = client.get("/approvals", headers=auth_headers(Role.manager)).json()["approvals"][0]["approval_id"]

    first = client.post(f"/approvals/{approval_id}/approve", headers=auth_headers(Role.manager))
    second = client.post(f"/approvals/{approval_id}/deny", headers=auth_headers(Role.manager))

    assert first.status_code == 200
    assert second.status_code == 409


def test_seed_demo_requires_admin_and_populates_governance_state():
    forbidden = client.post("/demo/seed", headers=auth_headers(Role.employee))
    response = client.post("/demo/seed", headers=auth_headers(Role.admin, team="platform", user_id="u-9001"))
    metrics = response.json()["metrics"]

    assert forbidden.status_code == 403
    assert response.status_code == 200
    assert metrics["requests_total"] == 5
    assert metrics["redactions_total"] >= 2
    assert metrics["denied_actions"] == 1
    assert metrics["tool_calls_total"] >= 2
