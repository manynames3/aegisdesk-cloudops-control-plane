from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import create_demo_token, decode_token, jwks_document
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


def test_demo_tokens_can_use_jwks_rs256_mode(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    monkeypatch.setenv("AEGISDESK_AUTH_MODE", "jwks")
    monkeypatch.setenv("AEGISDESK_JWKS_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("AEGISDESK_JWKS_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("AEGISDESK_JWKS_KEY_ID", "test-key")
    monkeypatch.setenv("AEGISDESK_JWT_ISSUER", "aegisdesk-test-issuer")

    actor = Actor(user_id="u-jwks", role=Role.manager, team="platform")
    token = create_demo_token(actor)
    decoded = decode_token(token)
    jwks = jwks_document()

    assert decoded == actor
    assert jwks["keys"][0]["kid"] == "test-key"


def test_chat_requires_bearer_token():
    response = client.post("/chat", json={"message": "Create a ticket."})

    assert response.status_code == 401


def test_quota_counter_tracks_role_team_window():
    actor = Actor(user_id="u-quota", role=Role.employee, team="payments")

    assert store.quota_count(actor) == 0
    assert store.increment_quota(actor) == 1
    assert store.quota_count(actor) == 1


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
    assert body["incident_context"]["source"] == "seeded_cloudwatch_logs"
    assert body["tool_calls"][0]["name"] == "incident.context"
    assert {source["kind"] for source in body["answer_sources"]} >= {
        "deterministic",
        "knowledge",
        "policy",
        "operational_context",
    }
    assert body["trusted_source_score"]["trusted_source_found"] is True
    assert body["trusted_source_score"]["sensitive_data_sent_externally"] is False
    assert body["knowledge_citations"][0]["doc_id"] == "KB-CLOUDOPS-001"
    assert "Initial Triage Sequence" == body["knowledge_citations"][0]["section"]


def test_low_sensitivity_prompt_uses_bedrock_route_with_local_fallback_when_disabled():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1004"),
        json={"message": "What is the safest way to ask for help with a CloudOps issue?"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["model_route"]["provider"] == "simulated-cloud"
    assert body["model_route"]["model"] == "bedrock-disabled-deterministic-fallback"
    assert body["answer_sources"][0]["name"] == "AegisDesk deterministic responder"
    assert body["knowledge_citations"][0]["doc_id"] == "GOV-FINOPS-007"


def test_production_access_denial_is_grounded_in_access_policy():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1005"),
        json={"message": "Give me admin access to the production database."},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "deny"
    assert body["knowledge_citations"][0]["doc_id"] == "POL-SEC-014"
    assert "production admin access is not self-service" in body["answer"].lower()


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
    employee_controls = client.get("/controls/abuse", headers=auth_headers(Role.employee))
    manager_approvals = client.get("/approvals", headers=auth_headers(Role.manager))
    manager_events = client.get("/events", headers=auth_headers(Role.manager))
    manager_controls = client.get("/controls/abuse", headers=auth_headers(Role.manager))

    assert employee_events.status_code == 403
    assert employee_metrics.status_code == 403
    assert employee_controls.status_code == 403
    assert manager_approvals.status_code == 200
    assert manager_events.status_code == 200
    assert manager_controls.status_code == 200
    assert manager_controls.json()["role_quotas"]["employee"] == 25


def test_oversized_prompt_is_rejected_before_model_routing():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-oversize"),
        json={"message": "x" * 2001},
    )

    assert response.status_code == 413
    assert store.metrics().requests_total == 0


def test_request_replay_contains_trace_packet():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-replay"),
        json={"message": "The checkout service is timing out. What should I check first?"},
    )
    request_id = response.json()["request_id"]

    replay = client.get(f"/requests/{request_id}/replay", headers=auth_headers(Role.manager))
    body = replay.json()

    assert replay.status_code == 200
    assert body["request_id"] == request_id
    assert body["sanitized_prompt"].startswith("The checkout service")
    assert body["policy_input"]["intent"] == "incident_triage"
    assert body["model_route"]["provider"] == "local"
    assert body["trusted_source_score"]["trusted_source_found"] is True
    assert "response.completed" in {event["event_type"] for event in body["audit_events"]}


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
