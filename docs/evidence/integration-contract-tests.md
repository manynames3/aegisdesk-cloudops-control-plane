# Integration Contract Test Evidence

AegisDesk includes adapter contract tests for the external workflows that should be connected in customer environments.

## Covered Adapters

| Adapter | Evidence | What is verified |
| --- | --- | --- |
| Jira ticket adapter | `services/api/tests/test_api.py::test_jira_ticket_adapter_creates_real_issue_payload` | Jira REST API v3 endpoint, auth tuple, project key, issue type, labels, returned ticket URL |
| ServiceNow ticket adapter | `services/api/tests/test_api.py::test_servicenow_ticket_adapter_creates_real_incident_payload` | Table API endpoint, basic auth, assignment group, severity mapping, returned number/sys_id |
| Ticket failure path | `services/api/tests/test_api.py::test_ticket_adapter_api_failure_is_blocked_without_fake_success` | External API failure returns blocked tool call, not fake success |
| CloudWatch Logs adapter | `services/api/tests/test_api.py::test_cloudwatch_incident_adapter_queries_bounded_logs` | Logs Insights query, log group, query limit, parsed entries, tool-call evidence |
| CloudWatch failure path | `services/api/tests/test_api.py::test_cloudwatch_incident_adapter_fails_closed_without_fixture_fallback` | Failed query returns unavailable context, no fixture fallback |
| Cost Explorer failure path | `services/api/tests/test_api.py::test_cost_explorer_permission_denied_fails_closed` | IAM/API denial raises unavailable cost path |

## Why Contract Tests Instead Of Live Sandbox Credentials

The repository should not commit Jira, ServiceNow, or customer AWS sandbox credentials. The contract tests record the exact request shape and failure behavior. A customer pilot should add one environment-specific smoke test with customer-provided sandbox credentials.

## Run

```bash
npm run test:api
```

The API test suite also covers identity-derived roles, policy decisions, approvals, request replay, audit export, customer data boundary mode, Bedrock failure, and OPA failure.
