from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.adapters import CloudWatchIncidentAdapter, JiraTicketAdapter, ServiceNowTicketAdapter, UnavailableTicketAdapter
from app.auth import create_persona_token, decode_token, jwks_document
from app.main import app, store
from app.models import Actor, AuditEvent, PolicyDecision, Role
from app.redaction import inspect_and_redact
from app.store import DemoStore


client = TestClient(app)


def auth_headers(role: Role = Role.employee, team: str = "payments", user_id: str = "u-test") -> dict[str, str]:
    token = create_persona_token(Actor(user_id=user_id, role=role, team=team))
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


def test_persona_tokens_can_use_jwks_rs256_mode(monkeypatch):
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
    token = create_persona_token(actor)
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


def test_broad_admin_access_request_is_denied_and_waits_for_required_details():
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
    assert body["tool_calls"] == []
    assert body["clarification"]["status"] == "blocked_pending_details"
    assert "duration" in body["clarification"]["missing_fields"]
    assert client.get("/metrics/summary", headers=auth_headers(Role.admin)).json()["approvals_pending"] == 0


def test_scoped_read_only_access_request_creates_approval():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1001"),
        json={
            "message": (
                "I need temporary read-only access to the production payments database for INC-1042. "
                "Duration: 2 hours. Business reason: inspect connection pool metrics during active incident. "
                "Approver: payments manager."
            ),
            "context": {"incident_id": "INC-1042"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "allow"
    assert body["clarification"]["status"] == "complete"
    assert body["tool_calls"][0]["status"] == "approval_required"
    assert client.get("/metrics/summary", headers=auth_headers(Role.admin)).json()["approvals_pending"] == 1


def test_employee_can_create_ticket():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="cloudops", user_id="u-1002"),
        json={
            "message": (
                "Create a SEV-2 ticket for the VPN outage affecting remote employees. "
                "Impact: users cannot connect to corporate VPN. Assign it to CloudOps."
            )
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["tool_calls"][0]["name"] == "ticket.create"
    assert body["tool_calls"][0]["status"] == "allowed"
    assert body["tool_calls"][0]["result"]["ticket_id"].startswith("TCK-")


def test_vague_ticket_request_waits_for_ticket_fields():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="cloudops", user_id="u-1002"),
        json={"message": "Create a ticket for the app issue."},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["decision"] == "allow"
    assert body["tool_calls"] == []
    assert body["clarification"]["status"] == "blocked_pending_details"
    assert "severity or priority" in body["clarification"]["missing_fields"]


def test_timing_out_prompt_routes_as_incident_triage():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1003"),
        json={
            "message": "The checkout service is timing out. What should I check first?",
            "context": {"incident_id": "INC-1042"},
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["reason"] == "incident_triage_allowed_for_employee"
    assert body["model_route"]["provider"] == "local"
    assert body["incident_context"]["source"] == "seeded_cloudwatch_logs"
    assert body["tool_calls"][0]["name"] == "incident.context"
    assert {source["kind"] for source in body["answer_sources"]} >= {
        "local_control",
        "knowledge",
        "policy",
        "operational_context",
    }
    assert body["trusted_source_score"]["trusted_source_found"] is True
    assert body["trusted_source_score"]["sensitive_data_sent_externally"] is False
    assert body["knowledge_citations"][0]["doc_id"] == "KB-CLOUDOPS-001"
    assert "Initial Triage Sequence" == body["knowledge_citations"][0]["section"]


def test_vague_incident_request_returns_partial_guidance_without_log_lookup():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1003"),
        json={"message": "app is not working"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["policy"]["reason"] == "incident_triage_allowed_for_employee"
    assert body["model_route"]["provider"] == "local"
    assert body["incident_context"] is None
    assert body["tool_calls"] == []
    assert body["clarification"]["status"] == "partial_guidance"
    assert "affected service or system" in body["clarification"]["missing_fields"]


def test_low_sensitivity_prompt_uses_bedrock_route_with_local_fallback_when_disabled():
    response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-1004"),
        json={"message": "What is the safest way to ask for help with a CloudOps issue?"},
    )

    body = response.json()

    assert response.status_code == 200
    assert body["model_route"]["provider"] == "local"
    assert body["model_route"]["model"] == "bedrock-disabled-local-control-fallback"
    assert body["answer_sources"][0]["name"] == "AegisDesk local control responder"
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
        json={
            "message": (
                "I need temporary read-only access to the production payments database for INC-1042. "
                "Duration: 2 hours. Business reason: inspect connection pool metrics during active incident."
            )
        },
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


def test_setup_status_is_public_and_redacts_secret_configuration():
    response = client.get("/setup/status")
    body = response.json()

    assert response.status_code == 200
    assert body["mode"] in {"evaluation", "production"}
    assert body["auth"]["mode"] in {"hmac", "jwks", "cognito"}
    assert "jira_api_token" not in response.text
    assert "servicenow_password" not in response.text
    assert "auth_secret" not in response.text
    assert body["data"]["audit_retention_days"] >= 1
    assert "cloudwatch_configured" in body["integrations"]


def test_audit_export_requires_manager_or_admin_and_returns_json_and_csv():
    chat_response = client.post(
        "/chat",
        headers=auth_headers(Role.employee, team="payments", user_id="u-export"),
        json={"message": "The checkout service is timing out. What should I check first?"},
    )
    request_id = chat_response.json()["request_id"]

    forbidden = client.get("/audit/export", headers=auth_headers(Role.employee))
    json_export = client.get("/audit/export", headers=auth_headers(Role.manager))
    csv_export = client.get("/audit/export?format=csv", headers=auth_headers(Role.admin))

    assert forbidden.status_code == 403
    assert json_export.status_code == 200
    assert json_export.json()["metadata"]["event_count"] >= 1
    assert any(event["request_id"] == request_id for event in json_export.json()["events"])
    assert csv_export.status_code == 200
    assert "text/csv" in csv_export.headers["content-type"]
    assert "request_id" in csv_export.text


def test_jira_ticket_adapter_creates_real_issue_payload():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"key": "OPS-123"}

    class FakeClient:
        def __init__(self):
            self.calls = []

        def post(self, url, json, auth):
            self.calls.append({"url": url, "json": json, "auth": auth})
            return FakeResponse()

    fake_client = FakeClient()
    adapter = JiraTicketAdapter(
        base_url="https://example.atlassian.net",
        email="ops@example.com",
        api_token="secret-token",
        project_key="OPS",
        issue_type="Task",
        client=fake_client,
    )
    policy = PolicyDecision(decision="allow", reason="ticket_creation_allowed", policy_name="tool_policy")

    tool_call = adapter.create_ticket(policy, "Checkout latency", "payments", "medium")

    assert tool_call.status == "allowed"
    assert tool_call.result["ticket_id"] == "OPS-123"
    assert tool_call.result["system"] == "jira"
    assert fake_client.calls[0]["url"] == "https://example.atlassian.net/rest/api/3/issue"
    assert fake_client.calls[0]["auth"] == ("ops@example.com", "secret-token")
    assert fake_client.calls[0]["json"]["fields"]["project"]["key"] == "OPS"


def test_servicenow_ticket_adapter_creates_real_incident_payload():
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"result": {"number": "INC0012345", "sys_id": "abc123", "state": "1"}}

    class FakeClient:
        def __init__(self):
            self.calls = []

        def post(self, url, json, auth):
            self.calls.append({"url": url, "json": json, "auth": auth})
            return FakeResponse()

    fake_client = FakeClient()
    adapter = ServiceNowTicketAdapter(
        instance_url="https://example.service-now.com",
        username="ops.integration",
        password="secret-password",
        assignment_group="cloudops",
        table="incident",
        client=fake_client,
    )
    policy = PolicyDecision(decision="allow", reason="ticket_creation_allowed", policy_name="tool_policy")

    tool_call = adapter.create_ticket(policy, "Checkout latency", "payments", "sev-2")

    assert tool_call.status == "allowed"
    assert tool_call.result["ticket_id"] == "INC0012345"
    assert tool_call.result["system"] == "servicenow"
    assert tool_call.result["sys_id"] == "abc123"
    assert fake_client.calls[0]["url"] == "https://example.service-now.com/api/now/table/incident"
    assert fake_client.calls[0]["auth"] == ("ops.integration", "secret-password")
    assert fake_client.calls[0]["json"]["assignment_group"] == "cloudops"
    assert fake_client.calls[0]["json"]["impact"] == "2"
    assert fake_client.calls[0]["json"]["urgency"] == "2"


def test_unavailable_ticket_adapter_fails_closed_without_fake_ticket():
    policy = PolicyDecision(decision="allow", reason="ticket_creation_allowed", policy_name="tool_policy")
    adapter = UnavailableTicketAdapter(reason="jira_adapter_missing_required_configuration", system="jira")

    tool_call = adapter.create_ticket(policy, "Checkout latency", "payments", "medium")

    assert tool_call.status == "blocked"
    assert "ticket_id" not in tool_call.result
    assert tool_call.result["error"] == "jira_adapter_missing_required_configuration"


def test_cloudwatch_incident_adapter_queries_bounded_logs():
    class FakeLogsClient:
        def __init__(self):
            self.start_query_call = None

        def start_query(self, **kwargs):
            self.start_query_call = kwargs
            return {"queryId": "query-123"}

        def get_query_results(self, queryId):
            return {
                "status": "Complete",
                "results": [
                    [
                        {"field": "@timestamp", "value": "2026-05-12T21:15:31Z"},
                        {"field": "level", "value": "ERROR"},
                        {"field": "service", "value": "checkout-api"},
                        {"field": "@message", "value": "INC-1042 database connection pool exhausted"},
                    ]
                ],
            }

    fake_client = FakeLogsClient()
    adapter = CloudWatchIncidentAdapter(
        log_group="/aws/lambda/checkout",
        region="us-east-1",
        lookback_minutes=15,
        query_limit=5,
        poll_interval_seconds=0,
        client=fake_client,
    )

    context = adapter.lookup_context("INC-1042", "checkout is timing out")
    tool_call = adapter.to_tool_call(context)

    assert context.source == "cloudwatch_logs"
    assert context.entries[0].service == "checkout-api"
    assert "INC-1042" in fake_client.start_query_call["queryString"]
    assert fake_client.start_query_call["limit"] == 5
    assert tool_call.status == "allowed"
    assert tool_call.policy.metadata["adapter"] == "cloudwatch_incident_adapter"


def test_cloudwatch_incident_adapter_fails_closed_without_fixture_fallback():
    class MisconfiguredLogsClient:
        def start_query(self, **kwargs):
            return {}

    adapter = CloudWatchIncidentAdapter(
        log_group="/aws/lambda/checkout",
        region="us-east-1",
        poll_interval_seconds=0,
        client=MisconfiguredLogsClient(),
    )

    context = adapter.lookup_context("INC-404", "checkout is timing out")
    tool_call = adapter.to_tool_call(context)

    assert context.source == "incident_context_unavailable"
    assert context.entries == []
    assert tool_call.status == "blocked"
    assert "fixture" not in tool_call.policy.reason


def test_sqlite_store_prunes_audit_events_by_retention(tmp_path):
    test_store = DemoStore(str(tmp_path / "aegisdesk.db"))
    actor = Actor(user_id="u-retention", role=Role.manager, team="platform")
    old_event = AuditEvent(
        request_id="req-old",
        actor=actor,
        event_type="request.received",
        summary="Old event",
        trace_id="trace-old",
        timestamp=datetime.now(UTC) - timedelta(days=10),
    )
    recent_event = AuditEvent(
        request_id="req-recent",
        actor=actor,
        event_type="request.received",
        summary="Recent event",
        trace_id="trace-recent",
        timestamp=datetime.now(UTC),
    )

    test_store.add_event(old_event)
    test_store.add_event(recent_event)

    assert test_store.prune_audit_events(retention_days=1) == 1
    assert [event.request_id for event in test_store.events] == ["req-recent"]


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
        json={
            "message": "The checkout service is timing out. What should I check first?",
            "context": {"incident_id": "INC-1042"},
        },
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
        json={
            "message": (
                "I need temporary read-only access to the production payments database for INC-1042. "
                "Duration: 2 hours. Business reason: inspect connection pool metrics during active incident."
            )
        },
    )
    approval_id = client.get("/approvals", headers=auth_headers(Role.manager)).json()["approvals"][0]["approval_id"]

    first = client.post(f"/approvals/{approval_id}/approve", headers=auth_headers(Role.manager))
    second = client.post(f"/approvals/{approval_id}/deny", headers=auth_headers(Role.manager))

    assert first.status_code == 200
    assert second.status_code == 409


def test_seed_state_requires_admin_and_populates_governance_state():
    forbidden = client.post("/admin/seed", headers=auth_headers(Role.employee))
    response = client.post("/admin/seed", headers=auth_headers(Role.admin, team="platform", user_id="u-9001"))
    metrics = response.json()["metrics"]

    assert forbidden.status_code == 403
    assert response.status_code == 200
    assert metrics["requests_total"] == 6
    assert metrics["redactions_total"] >= 2
    assert metrics["denied_actions"] == 1
    assert metrics["tool_calls_total"] >= 2
