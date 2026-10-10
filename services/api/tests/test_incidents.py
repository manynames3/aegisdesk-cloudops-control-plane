from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event

import httpx
import pytest
from app import main, tools
from app.adapters import JiraTicketAdapter
from app.auth import create_persona_token
from app.main import app, store
from app.models import Actor, IncidentContext, IncidentLogEntry, PolicyDecision, Role
from app.policy_engine import PolicyUnavailable
from app.store import DemoStore
from fastapi.testclient import TestClient

client = TestClient(app)


def headers(role=Role.employee, team="payments", user="operator"):
    return {
        "Authorization": "Bearer "
        + create_persona_token(Actor(user_id=user, role=role, team=team))
    }


@pytest.fixture(autouse=True)
def reset():
    store.reset()


@pytest.fixture
def jira(monkeypatch):
    for name, value in {
        "TICKET_ADAPTER": "jira",
        "JIRA_BASE_URL": "https://example.atlassian.net",
        "JIRA_PROJECT_KEY": "OPS",
        "JIRA_EMAIL": "ops@example.test",
        "JIRA_API_TOKEN": "controlled-test-credential",
    }.items():
        monkeypatch.setenv("AEGISDESK_" + name, value)
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(201, json={"key": "OPS-123"})

    adapter = JiraTicketAdapter(
        base_url="https://example.atlassian.net",
        email="ops@example.test",
        api_token="controlled-test-credential",
        project_key="OPS",
        client=httpx.Client(transport=httpx.MockTransport(handle)),
    )
    monkeypatch.setattr(tools, "ticket_adapter", adapter)
    yield calls
    adapter.client.close()


def create():
    response = client.post(
        "/incidents",
        headers=headers(),
        json={
            "title": "Lambda errors",
            "description": "Investigate token=private-value customer@example.test",
            "service": "Lambda",
            "resource": "checkout-api",
            "environment": "production",
            "severity": "high",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def step(case, suffix, identity=None, extra=None):
    response = client.post(
        f"/incidents/{case['incident_id']}{suffix}",
        headers=identity or headers(),
        json={"version": case["version"], **(extra or {})},
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


def approved_case():
    case = step(create(), "/actions")
    action_id = case["actions"][0]["action_id"]
    case = step(case, f"/actions/{action_id}/request-approval")
    return step(
        case, f"/actions/{action_id}/approve", headers(Role.manager, user="manager")
    ), action_id


def test_incident_requires_auth_and_is_team_scoped():
    assert client.get("/incidents").status_code == 401
    case = create()
    assert "private-value" not in str(case)
    assert "customer@example.test" not in str(case)
    assert (
        client.get("/incidents", headers=headers(team="other")).json()["incidents"]
        == []
    )
    assert (
        client.get(
            f"/incidents/{case['incident_id']}",
            headers=headers(Role.admin, team="other"),
        ).status_code
        == 404
    )
    assert len(client.get("/incidents", headers=headers()).json()["incidents"]) == 1


def test_incident_transition_and_version_conflict():
    case = create()
    path = f"/incidents/{case['incident_id']}"
    assert (
        client.patch(
            path,
            headers=headers(),
            json={"version": case["version"], "status": "mitigating"},
        ).status_code
        == 409
    )
    updated = client.patch(
        path,
        headers=headers(),
        json={"version": case["version"], "status": "investigating"},
    ).json()
    assert updated["version"] == case["version"] + 1
    assert (
        client.patch(
            path,
            headers=headers(),
            json={"version": case["version"], "status": "investigating"},
        ).status_code
        == 409
    )
    updated = step(
        updated,
        "/notes",
        extra={"text": "Possible overload password=test-value", "kind": "hypothesis"},
    )
    assert updated["notes"][0]["verified_root_cause"] is False
    assert "test-value" not in str(updated)


def test_fixture_is_never_incident_evidence():
    case = step(create(), "/evidence")
    assert case["evidence_state"] == "unavailable"
    assert case["evidence"] is None


def test_cloudwatch_refresh_redacts_and_retains_stale_evidence(monkeypatch):
    monkeypatch.setenv("AEGISDESK_INCIDENT_CONTEXT_ADAPTER", "cloudwatch")
    monkeypatch.setenv("AEGISDESK_CLOUDWATCH_LOG_GROUP", "/aws/lambda/checkout")
    context = IncidentContext(
        incident_id="external-ref",
        source="cloudwatch_logs",
        log_group="/aws/lambda/checkout",
        query="bounded-query",
        suspected_cause="Unverified latency hypothesis",
        entries=[
            IncidentLogEntry(
                timestamp="2026-10-09T12:00:00Z",
                level="ERROR",
                service="checkout",
                message="token=private-value customer@example.test",
            )
        ],
    )
    monkeypatch.setattr(tools, "lookup_incident_context", lambda *args: context)
    case = step(create(), "/evidence")
    assert case["evidence_state"] == "success"
    assert "private-value" not in str(case)
    loaded_at = case["evidence"]["loaded_at"]
    monkeypatch.setattr(
        tools,
        "lookup_incident_context",
        lambda *args: context.model_copy(
            update={
                "source": "incident_context_unavailable",
                "entries": [],
                "suspected_cause": "CloudWatch denied",
            }
        ),
    )
    case = step(case, "/evidence")
    assert case["evidence_state"] == "stale"
    assert case["evidence"]["loaded_at"] == loaded_at
    assert len(case["evidence"]["context"]["entries"]) == 1


def test_empty_evidence_is_distinct_from_unavailable(monkeypatch):
    monkeypatch.setenv("AEGISDESK_INCIDENT_CONTEXT_ADAPTER", "cloudwatch")
    monkeypatch.setenv("AEGISDESK_CLOUDWATCH_LOG_GROUP", "logs")
    monkeypatch.setattr(
        tools,
        "lookup_incident_context",
        lambda *args: IncidentContext(
            incident_id="x",
            source="cloudwatch_logs",
            log_group="logs",
            query="query",
            suspected_cause="No events",
            entries=[],
        ),
    )
    case = step(create(), "/evidence")
    assert case["evidence_state"] == "empty"
    assert case["evidence"] is not None


def test_full_governed_ticket_lifecycle_and_no_duplicate_dispatch(jira):
    case, action_id = approved_case()
    case = step(case, f"/actions/{action_id}/execute")
    assert case["actions"][0]["state"] == "succeeded"
    assert case["external_ticket"]["ticket_id"] == "OPS-123"
    assert case["status"] == "mitigating"
    assert len(jira) == 1
    assert all(event["correlation_id"].startswith("req-") for event in case["timeline"])
    assert (
        client.post(
            f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
            headers=headers(),
            json={"version": case["version"]},
        ).status_code
        == 409
    )
    assert len(jira) == 1
    events = [item["event"] for item in case["timeline"]]
    assert events == [
        "incident.created",
        "action.proposed",
        "action.approval_requested",
        "action.approved",
        "action.executing",
        "action.succeeded",
    ]


def test_approval_is_independent_and_execution_requires_approval(jira):
    case = step(create(), "/actions")
    action_id = case["actions"][0]["action_id"]
    path = f"/incidents/{case['incident_id']}/actions/{action_id}"
    assert (
        client.post(
            path + "/execute", headers=headers(), json={"version": case["version"]}
        ).status_code
        == 409
    )
    case = step(case, f"/actions/{action_id}/request-approval")
    assert (
        client.post(
            path + "/approve", headers=headers(), json={"version": case["version"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            path + "/approve",
            headers=headers(Role.manager),
            json={"version": case["version"]},
        ).status_code
        == 403
    )
    assert len(jira) == 0


def test_approval_expiry_and_action_tampering_block_dispatch(jira):
    case, action_id = approved_case()
    original = case["version"]
    case["actions"][0]["arguments"]["severity"] = "critical"
    store.save_case(case, original)
    assert (
        client.post(
            f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
            headers=headers(),
            json={"version": original},
        ).status_code
        == 409
    )
    case["actions"][0]["expires_at"] = (
        datetime.now(UTC) - timedelta(hours=1)
    ).isoformat()
    store.save_case(case, original)
    response = client.post(
        f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
        headers=headers(),
        json={"version": original},
    )
    assert response.status_code == 409
    assert not jira


def test_policy_failure_at_execution_prevents_dispatch(monkeypatch, jira):
    case, action_id = approved_case()

    def fail(*args):
        raise PolicyUnavailable("policy failed")

    monkeypatch.setattr(main.policy_engine, "evaluate_tool", fail)
    assert (
        client.post(
            f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
            headers=headers(),
            json={"version": case["version"]},
        ).status_code
        == 503
    )
    assert not jira


def test_concurrent_execute_dispatches_once(monkeypatch, jira):
    case, action_id = approved_case()
    dispatched, release = Event(), Event()
    calls = []

    def handle(request):
        calls.append(request)
        dispatched.set()
        assert release.wait(5)
        return httpx.Response(201, json={"key": "OPS-123"})

    monkeypatch.setattr(
        tools,
        "ticket_adapter",
        JiraTicketAdapter(
            base_url="https://example.atlassian.net",
            email="ops@example.test",
            api_token="controlled-test-credential",
            project_key="OPS",
            client=httpx.Client(transport=httpx.MockTransport(handle)),
        ),
    )
    path = f"/incidents/{case['incident_id']}/actions/{action_id}/execute"
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(
            client.post, path, headers=headers(), json={"version": case["version"]}
        )
        try:
            assert dispatched.wait(5)
            assert (
                client.post(
                    path, headers=headers(), json={"version": case["version"]}
                ).status_code
                == 409
            )
        finally:
            release.set()
        assert first.result().status_code == 200
    assert len(calls) == 1


def test_approval_expiration_blocks_execution(jira):
    case, action_id = approved_case()
    case["actions"][0]["expires_at"] = (
        datetime.now(UTC) - timedelta(seconds=1)
    ).isoformat()
    case["actions"][0]["approval"]["expires_at"] = case["actions"][0]["expires_at"]
    store.save_case(case, case["version"])
    response = client.post(
        f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
        headers=headers(),
        json={"version": case["version"]},
    )
    assert response.status_code == 409
    assert "approval_expired" in response.json()["detail"]
    assert not jira


def test_timeout_remains_uncertain_and_reconciliation_requires_matching_ticket(
    monkeypatch, jira
):
    case, action_id = approved_case()

    def timeout(request):
        raise httpx.ReadTimeout("unknown outcome")

    monkeypatch.setattr(
        tools,
        "ticket_adapter",
        JiraTicketAdapter(
            base_url="https://example.atlassian.net",
            email="ops@example.test",
            api_token="controlled-test-credential",
            project_key="OPS",
            client=httpx.Client(transport=httpx.MockTransport(timeout)),
        ),
    )
    case = step(case, f"/actions/{action_id}/execute")
    assert case["actions"][0]["state"] == "outcome_uncertain"
    assert case["external_ticket"] is None
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.atlassian.net"),
            json={
                "key": "OPS-123",
                "fields": {"summary": "Wrong action", "project": {"key": "OPS"}},
            },
        ),
    )
    path = f"/incidents/{case['incident_id']}/actions/{action_id}/reconcile"
    assert (
        client.post(
            path,
            headers=headers(Role.manager, user="manager"),
            json={"version": case["version"], "ticket_key": "OPS-123"},
        ).status_code
        == 409
    )
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            request=httpx.Request("GET", "https://example.atlassian.net"),
            json={
                "key": "OPS-123",
                "fields": {
                    "summary": case["actions"][0]["arguments"]["title"],
                    "project": {"key": "OPS"},
                },
            },
        ),
    )
    case = step(
        case,
        f"/actions/{action_id}/reconcile",
        headers(Role.manager, user="manager"),
        {"ticket_key": "OPS-123"},
    )
    assert case["actions"][0]["state"] == "succeeded"


@pytest.mark.parametrize(
    "response_body", [{}, {"id": "123"}, {"key": "JIRA-UNKNOWN"}, []]
)
def test_malformed_jira_success_is_uncertain(response_body):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(201, json=response_body)
    )
    adapter = JiraTicketAdapter(
        base_url="https://example.atlassian.net",
        email="ops@example.test",
        api_token="controlled-test-credential",
        project_key="OPS",
        client=httpx.Client(transport=transport),
    )
    result = adapter.create_ticket(
        PolicyDecision(decision="allow", reason="test", policy_name="test"),
        "Incident",
        "payments",
        "high",
    )
    assert result.result["status"] == "outcome_uncertain"
    assert "ticket_id" not in result.result


def test_sqlite_case_survives_restart_and_conditional_write_is_atomic(tmp_path):
    database = str(tmp_path / "cases.db")
    local = DemoStore(database)
    local.save_case({"team": "payments", "incident_id": "INC-1", "version": 1}, 0)
    reopened = DemoStore(database)
    assert reopened.list_cases("payments")[0]["version"] == 1
    barrier = Barrier(2)

    def update():
        barrier.wait()
        try:
            local.save_case(
                {"team": "payments", "incident_id": "INC-1", "version": 2}, 1
            )
            return "saved"
        except ValueError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: update(), range(2)))
    assert sorted(results) == ["conflict", "saved"]


def test_cost_explorer_failure_does_not_substitute_fixture(monkeypatch):
    monkeypatch.setenv("AEGISDESK_ENABLE_COST_EXPLORER", "true")
    result = tools.lookup_cost_summary(
        PolicyDecision(decision="allow", reason="test", policy_name="test")
    )
    assert result.status == "blocked"
    assert "total_usd" not in result.result


def test_chat_cannot_bypass_jira_incident_approval(monkeypatch, jira):
    from dataclasses import replace

    monkeypatch.setattr(main, "settings", replace(main.settings, ticket_adapter="jira"))
    result = client.post(
        "/chat",
        headers=headers(),
        json={
            "message": "Create a ticket titled Lambda errors for payments with medium severity."
        },
    ).json()
    assert not jira
    assert result["tool_calls"][0]["status"] == "blocked"


def test_customer_mode_disables_seed_reset_and_hosted_personas(monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(
        main, "settings", replace(main.settings, persona_issuer_enabled=False)
    )
    for path in ("/admin/seed", "/admin/reset"):
        assert client.post(path, headers=headers(Role.admin)).status_code == 404
    assert (
        client.post(
            "/auth/hosted-ui-login", json={"role": "employee", "team": "payments"}
        ).status_code
        == 404
    )


def test_manager_audit_and_replay_are_scoped_and_redacted():
    response = client.post(
        "/chat",
        headers=headers(),
        json={
            "message": "Investigate token=private-value customer@example.test checkout incident"
        },
    )
    request_id = response.json()["request_id"]
    assert (
        client.get(
            f"/requests/{request_id}/replay",
            headers=headers(Role.manager, team="other"),
        ).status_code
        == 404
    )
    assert (
        client.get("/events", headers=headers(Role.manager, team="other")).json()[
            "events"
        ]
        == []
    )
    export = client.get("/audit/export", headers=headers(Role.manager)).text
    assert "private-value" not in export
    assert "customer@example.test" not in export


def test_dynamo_case_contract_paginates_and_uses_conditional_versions():
    from app.store import DynamoStore
    from botocore.exceptions import ClientError

    class Table:
        def __init__(self):
            self.queries = []
            self.writes = []

        def query(self, **args):
            self.queries.append(args)
            if len(self.queries) == 1:
                return {
                    "Items": [{"payload": '{"incident_id": "INC-1"}'}],
                    "LastEvaluatedKey": {"pk": "INCIDENT#payments", "sk": "INC-1"},
                }
            return {"Items": [{"payload": '{"incident_id": "INC-2"}'}]}

        def put_item(self, **args):
            self.writes.append(args)
            if args.get("ExpressionAttributeValues", {}).get(":v") == 99:
                raise ClientError(
                    {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem"
                )

    dynamo = DynamoStore.__new__(DynamoStore)
    dynamo._table = Table()
    assert len(dynamo.list_cases("payments")) == 2
    assert all(query["ConsistentRead"] for query in dynamo._table.queries)
    assert "ExclusiveStartKey" in dynamo._table.queries[1]
    case = {"team": "payments", "incident_id": "INC-1", "version": 1}
    dynamo.save_case(case, 0)
    dynamo.save_case({**case, "version": 2}, 1)
    assert dynamo._table.writes[0]["ConditionExpression"] == "attribute_not_exists(pk)"
    assert dynamo._table.writes[1]["ExpressionAttributeValues"] == {":v": 1}
    with pytest.raises(ValueError):
        dynamo.save_case(case, 99)


def test_invalid_policy_payload_fails_closed(monkeypatch):
    from app.policy_engine import PolicyEngine

    monkeypatch.setenv("AEGISDESK_POLICY_MODE", "opa")
    monkeypatch.setenv("OPA_URL", "http://policy.test")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *args, **kwargs: httpx.Response(
            200, request=httpx.Request("POST", "http://policy.test"), json=["invalid"]
        ),
    )
    engine = PolicyEngine()
    assert engine.mode == "opa_http"
    with pytest.raises(PolicyUnavailable, match="policy_engine_unavailable"):
        engine.evaluate_tool(Role.employee, "ticket", "create_ticket")
    with pytest.raises(PolicyUnavailable):
        PolicyEngine._policy_decision({"decision": "invalid"}, "test")


def test_strict_customer_mode_rejects_local_ticket_adapter(monkeypatch):
    monkeypatch.setenv("AEGISDESK_DATA_BOUNDARY_MODE", "customer_strict")
    monkeypatch.setenv("AEGISDESK_TICKET_ADAPTER", "local")
    adapter = tools._configured_ticket_adapter()
    result = adapter.create_ticket(
        PolicyDecision(decision="allow", reason="test", policy_name="test"),
        "Incident",
        "payments",
        "high",
    )
    assert result.status == "blocked"
    assert "ticket_id" not in result.result


def test_unrelated_team_employee_cannot_execute_approved_action(jira):
    case, action_id = approved_case()
    response = client.post(
        f"/incidents/{case['incident_id']}/actions/{action_id}/execute",
        headers=headers(user="coworker"),
        json={"version": case["version"]},
    )
    assert response.status_code == 403
    assert not jira


def test_malformed_servicenow_success_does_not_invent_ticket():
    from app.adapters import ServiceNowTicketAdapter

    adapter = ServiceNowTicketAdapter(
        instance_url="https://example.service-now.com",
        username="test",
        password="controlled-test-credential",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(201, json={"result": {}})
            )
        ),
    )
    result = adapter.create_ticket(
        PolicyDecision(decision="allow", reason="test", policy_name="test"),
        "Incident",
        "payments",
        "high",
    )
    assert result.status == "blocked"
    assert result.result["status"] == "outcome_uncertain"
    assert "ticket_id" not in result.result
