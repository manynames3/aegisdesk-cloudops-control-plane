# API Contracts

These contracts are the intended MVP shape. They may change during implementation, but they define the first build target.

## POST /chat

Request:

```json
{
  "user_id": "u-1001",
  "role": "employee",
  "team": "payments",
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
    "estimated_cost_usd": 0.0
  },
  "redaction": {
    "pii_detected": false,
    "secrets_detected": false,
    "redacted_fields": []
  },
  "policy": {
    "decision": "allow",
    "reason": "support_guidance_allowed"
  },
  "tool_calls": [],
  "trace_id": "trace-123"
}
```

## POST /tools/ticket

Request:

```json
{
  "request_id": "req-abc123",
  "user_id": "u-1001",
  "role": "employee",
  "action": "create_ticket",
  "payload": {
    "title": "Checkout service timeout",
    "team": "cloudops",
    "severity": "medium"
  }
}
```

Response:

```json
{
  "tool_call_id": "tool-001",
  "policy": {
    "decision": "allow",
    "reason": "employees_can_create_support_tickets"
  },
  "result": {
    "ticket_id": "TCK-4821",
    "status": "open"
  }
}
```

## POST /access-requests

Request:

```json
{
  "user_id": "u-1001",
  "role": "employee",
  "resource": "prod-payments-db",
  "permission": "admin",
  "reason": "debug incident INC-1042"
}
```

Response:

```json
{
  "request_id": "access-123",
  "policy": {
    "decision": "deny",
    "reason": "employees_cannot_request_production_admin_access"
  },
  "suggested_alternative": {
    "permission": "read_only",
    "requires_approval": true,
    "expires_in": "2h"
  }
}
```

## GET /events

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

