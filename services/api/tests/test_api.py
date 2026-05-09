from fastapi.testclient import TestClient

from app.main import app, store
from app.redaction import inspect_and_redact


client = TestClient(app)


def setup_function():
    store.reset()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_redaction_detects_pii_and_secret():
    result = inspect_and_redact("email jane@example.com token=abc123456")

    assert result.pii_detected is True
    assert result.secrets_detected is True
    assert "[REDACTED_EMAIL]" in result.redacted_text
    assert "[REDACTED_CREDENTIAL]" in result.redacted_text


def test_admin_access_request_is_denied_and_creates_approval():
    response = client.post(
        "/chat",
        json={
            "user_id": "u-1001",
            "role": "employee",
            "team": "payments",
            "message": "Give me admin access to the production database.",
            "context": {"incident_id": "INC-1042"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "deny"
    assert body["tool_calls"][0]["status"] == "approval_required"
    assert client.get("/metrics/summary").json()["approvals_pending"] == 1


def test_employee_can_create_ticket():
    response = client.post(
        "/chat",
        json={
            "user_id": "u-1002",
            "role": "employee",
            "team": "cloudops",
            "message": "Create a ticket for the VPN outage and assign it to CloudOps.",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["tool_calls"][0]["name"] == "ticket.create"
    assert body["tool_calls"][0]["status"] == "allowed"
    assert body["tool_calls"][0]["result"]["ticket_id"].startswith("TCK-")


def test_timing_out_prompt_routes_as_incident_triage():
    response = client.post(
        "/chat",
        json={
            "user_id": "u-1003",
            "role": "employee",
            "team": "payments",
            "message": "The checkout service is timing out. What should I check first?",
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["reason"] == "incident_triage_allowed_for_employee"
    assert body["model_route"]["provider"] == "local"


def test_seed_demo_populates_governance_state():
    response = client.post("/demo/seed")
    metrics = response.json()["metrics"]

    assert response.status_code == 200
    assert metrics["requests_total"] == 5
    assert metrics["redactions_total"] >= 2
    assert metrics["denied_actions"] == 1
    assert metrics["tool_calls_total"] >= 2
