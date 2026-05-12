# API Contracts

These contracts describe the current portfolio shape. Protected endpoints require `Authorization: Bearer <token>`. The hosted deployment uses Cognito ID tokens verified through Cognito JWKS.

## POST /auth/persona-token

Request:

```json
{
  "role": "employee",
  "team": "payments"
}
```

Response:

```json
{
  "access_token": "cognito.id.token",
  "token_type": "bearer",
  "actor": {
    "user_id": "aegisdesk-employee",
    "role": "employee",
    "team": "payments"
  }
}
```

This endpoint creates reviewer personas for the hosted portfolio environment. In AWS it uses Cognito Admin APIs to issue Cognito ID tokens; direct local runs can use a local token issuer for fast testing.

## GET /.well-known/jwks.json

Returns the public JSON Web Key Set used to verify hosted Cognito tokens.

## POST /chat

Request:

```json
{
  "message": "The checkout service is timing out. What should I check first?",
  "context": {
    "incident_id": "INC-1042"
  }
}
```

Response:

```json
{
  "request_id": "req-abc123",
  "answer": "Start by checking recent deploys, upstream payment provider latency, and database connection pool saturation.",
  "model_route": {
    "provider": "local",
    "model": "llama3.1",
    "reason": "internal_operational_context",
    "estimated_cost_usd": 0.0,
    "external_call": false,
    "input_tokens": 0,
    "output_tokens": 0
  },
  "redaction": {
    "pii_detected": false,
    "secrets_detected": false,
    "redacted_fields": []
  },
  "policy": {
    "decision": "allow",
    "reason": "incident_triage_allowed_for_employee",
    "policy_name": "chat_policy",
    "metadata": {}
  },
  "tool_calls": [],
  "trace_id": "trace-123"
}
```

## Tool Calls Through /chat

The public API does not expose separate public tool endpoints. Tool actions are selected by intent inside `/chat`, authorized by OPA, and returned as structured `tool_calls`. The same deterministic tool set is also exposed by `services/mcp-tools` as a real MCP server for local agent clients.

Example tool call response:

```json
{
  "tool_call_id": "tool-001",
  "name": "ticket.create",
  "status": "allowed",
  "policy": {
    "decision": "allow",
    "reason": "employees_can_create_support_tickets",
    "policy_name": "tool_authorization",
    "metadata": {}
  },
  "result": {
    "ticket_id": "TCK-4821",
    "status": "open"
  }
}
```

Manager/admin cost investigations call AWS Cost Explorer when enabled and cache the summary in DynamoDB. Employee cost investigations return `approval_required`.

## GET /events

Requires admin role.

Response:

```json
{
  "events": [
    {
      "event_id": "evt-001",
      "request_id": "req-abc123",
      "event_type": "model.route.selected",
      "timestamp": "2026-05-09T05:00:00Z",
      "summary": "Request routed to local model due to internal operational context."
    }
  ]
}
```

## GET /metrics/summary

Requires admin role.

Response:

```json
{
  "requests_total": 128,
  "estimated_spend_usd": 2.41,
  "local_model_requests": 91,
  "cloud_model_requests": 37,
  "redactions_total": 14,
  "denied_actions": 9,
  "approvals_pending": 3,
  "tool_calls_total": 42
}
```
