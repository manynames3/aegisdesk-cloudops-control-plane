# Audit Event Model

The audit event model is central to AegisDesk. The system should be able to explain what happened, why it happened, and who approved it.

## Event Principles

- Events are append-style records.
- Events link to a request ID.
- Events include user and role context.
- Events include policy decisions and reasons.
- Events include trace IDs for operational debugging.
- Sensitive values must be redacted before replay storage; request replay stores sanitized prompt data, not raw secrets.

## Base Event Shape

```json
{
  "event_id": "evt-001",
  "request_id": "req-abc123",
  "timestamp": "2026-05-09T05:00:00Z",
  "actor": {
    "user_id": "u-1001",
    "role": "employee",
    "team": "payments"
  },
  "event_type": "policy.denied",
  "summary": "Production admin access denied for employee role.",
  "metadata": {
    "resource": "prod-payments-db",
    "action": "grant_admin_access",
    "policy_name": "tool_authorization",
    "policy_reason": "employees_cannot_request_production_admin_access"
  },
  "trace_id": "trace-123"
}
```

## Event Types

| Event Type | Meaning |
| --- | --- |
| `request.received` | User submitted a request and sanitized replay data was stored |
| `request.rejected` | Request was rejected before routing, usually by size or abuse controls |
| `redaction.completed` | Redaction ran before policy and model routing |
| `pii.detected` | PII was found |
| `secret.detected` | Secret-like value was found |
| `model.route.selected` | Model route was chosen |
| `model.fallback` | Bedrock was unavailable and deterministic fallback was used |
| `model.kill_switch_applied` | Cloud model kill switch forced local routing |
| `quota.allowed` | Request was within role/team quota |
| `quota.denied` | Request exceeded role/team quota |
| `incident.context.loaded` | Read-only incident context was loaded for triage |
| `policy.allowed` | Policy allowed an action |
| `policy.denied` | Policy denied an action |
| `approval.requested` | Human approval was required |
| `approval.granted` | Manager approved an action |
| `approval.denied` | Manager rejected an action |
| `tool.called` | Governed tool was called |
| `tool.blocked` | Tool call was blocked |
| `response.completed` | Sanitized request replay snapshot was persisted |
| `eval.failed` | Safety or policy evaluation failed |

## Dashboard Use

The admin dashboard should not invent its own data. It should render summaries from the event model:

- Redactions count comes from `pii.detected` and `secret.detected`.
- Denied actions come from `policy.denied` and `tool.blocked`.
- Approval metrics come from approval events.
- Tool call history comes from `tool.called`.
- Route split comes from `model.route.selected`.
- Incident evidence comes from `incident.context.loaded`.

The governance dashboard supports filtering these persisted records by request ID, user, policy decision, route, and tool so reviewers can inspect one workflow end to end instead of reading raw logs.

Clicking an audit event opens the request replay viewer. The replay is built from the `response.completed` snapshot and correlated audit events, including sanitized prompt, redaction result, policy input/output, model route, governed tool calls, answer sources, trust score, and trace ID.

## Approval Trail

Approval records link back to audit events through request IDs and approval metadata:

- `approval.requested` records requester, resource, permission, and approval ID.
- `approval.granted` or `approval.denied` records approver, status, decision timestamp, and approval ID.
- The frontend shows a plain-English approval timeline on the approval card so the workflow is understandable without inspecting DynamoDB directly.
- Admin users can expand technical audit details when they need event names and request IDs.
