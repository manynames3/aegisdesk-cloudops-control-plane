# API Contracts

These contracts describe the current control-plane API. Protected endpoints require `Authorization: Bearer <token>`. The hosted deployment uses Cognito ID tokens verified through Cognito JWKS.

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

This endpoint creates non-production reviewer personas for the hosted environment. In AWS it uses Cognito Admin APIs to issue Cognito ID tokens; direct local runs can use a local token issuer for fast testing.

## GET /auth/hosted-ui-config

Returns the Cognito Hosted UI OAuth endpoints and public app client ID used by the static frontend.

## POST /auth/hosted-ui-login

Creates or updates a controlled reviewer persona in Cognito, returns reviewer credentials, and returns Hosted UI config. The frontend uses this to send a reviewer to Cognito Hosted UI instead of silently switching roles in the browser.

The returned credentials are non-production personas. The frontend shows them in the sidebar so a reviewer can sign into Cognito without a separate secret handoff.

## POST /auth/oauth/exchange

Exchanges a Cognito Hosted UI authorization code and PKCE verifier for tokens. The API verifies the returned ID token through Cognito JWKS before returning the actor context to the frontend.

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
    "redacted_text": "The checkout service is timing out. What should I check first?",
    "findings": []
  },
  "policy": {
    "decision": "allow",
    "reason": "incident_triage_allowed_for_employee",
    "policy_name": "chat_policy",
    "metadata": {}
  },
  "tool_calls": [],
  "incident_context": {
    "incident_id": "INC-1042",
    "source": "seeded_cloudwatch_logs",
    "log_group": "/aws/lambda/aegisdesk/checkout",
    "query": "fields @timestamp, @message | filter incident_id = 'INC-1042' | sort @timestamp asc | limit 20",
    "entries": [
      {
        "timestamp": "2026-05-12T19:41:03Z",
        "level": "ERROR",
        "service": "checkout-api",
        "message": "Database connection pool exhausted while opening checkout transaction."
      }
    ],
    "suspected_cause": "Database connection pool saturation is the strongest signal."
  },
  "knowledge_citations": [
    {
      "doc_id": "KB-CLOUDOPS-001",
      "title": "Checkout Timeout Triage Runbook",
      "source_path": "docs/knowledge/checkout-timeout-triage-runbook.md",
      "section": "Initial Triage Sequence",
      "owner": "CloudOps Platform Team",
      "last_reviewed": "2026-05-01",
      "excerpt": "1. Confirm the alert scope and user impact. 2. Compare the alert start time with the last checkout deployment..."
    }
  ],
  "answer_sources": [
    {
      "kind": "local_control",
      "name": "AegisDesk local control responder",
      "detail": "Backend control-plane logic generated the response without a general LLM call.",
      "trusted": true
    },
    {
      "kind": "policy",
      "name": "OPA/Rego policy decision",
      "detail": "allow from chat_policy: incident_triage_allowed_for_employee.",
      "trusted": true
    },
    {
      "kind": "knowledge",
      "name": "Checkout Timeout Triage Runbook (KB-CLOUDOPS-001)",
      "detail": "Initial Triage Sequence; owner CloudOps Platform Team; reviewed 2026-05-01.",
      "trusted": true
    },
    {
      "kind": "operational_context",
      "name": "Seeded CloudWatch-style incident logs",
      "detail": "INC-1042; 4 entries from /aws/lambda/aegisdesk/checkout.",
      "trusted": true
    }
  ],
  "clarification": {
    "status": "complete",
    "risk_level": "medium",
    "missing_fields": [],
    "questions": [],
    "can_answer_partially": false,
    "blocks_tool_call": false,
    "reason": "Incident request includes enough context for read-only triage."
  },
  "trusted_source_score": {
    "score": 100,
    "trusted_source_found": true,
    "source_freshness": "fresh",
    "external_model_used": false,
    "sensitive_data_sent_externally": false,
    "policy_result": "allow",
    "rationale": [
      "Answer is grounded in internal runbook, policy, operational, or cost data.",
      "No detected sensitive values were sent to an external model."
    ]
  },
  "trace_id": "trace-123"
}
```

`knowledge_citations` identifies the trusted internal document excerpt used to ground the response. `answer_sources` exists so reviewers can tell whether an answer came from backend control logic, Amazon Bedrock, OPA/Rego policy, an internal runbook or policy, an MCP tool, incident context, AWS Cost Explorer, or a cached cost summary.

`clarification` shows whether the gateway had enough business and operational context to take action. For example, a vague incident can return safe partial guidance, but ticket creation, access approval, and cost lookup tool calls are paused until the request includes required fields such as service, severity, impact, resource, duration, reason, or time window.

`trusted_source_score` gives reviewers a plain-English quality and governance signal for each answer: trusted source presence, source freshness, external model use, sensitive external data status, and policy result.

## Tool Calls Through /chat

The public API does not expose separate public tool endpoints. Tool actions are selected by intent inside `/chat`, authorized by OPA, and returned as structured `tool_calls`. The same governed tool set is also exposed by `services/mcp-tools` as a real MCP server for local agent clients.

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

Incident triage responses include `incident_context` when the request supplies a known incident ID. The source can be `seeded_cloudwatch_logs`, `cloudwatch_logs`, or `incident_context_unavailable`. The local fixture source supports first-run evaluation; the CloudWatch adapter uses bounded Logs Insights queries when configured.

## GET /events

Requires manager or admin role.

Response:

```json
{
  "events": [
    {
      "event_id": "evt-001",
      "request_id": "req-abc123",
      "event_type": "model.route.selected",
      "timestamp": "2026-05-09T05:00:00Z",
      "summary": "Request routed to local model due to internal operational context.",
      "actor": {
        "user_id": "aegisdesk-employee",
        "role": "employee",
        "team": "payments"
      },
      "metadata": {
        "provider": "local",
        "model": "local-control-fallback",
        "reason": "sensitive_content_local_only"
      },
      "trace_id": "trace-123"
    }
  ]
}
```

## GET /requests/{request_id}/replay

Requires manager or admin role.

Returns a sanitized replay packet for a single request. The replay is designed for review and debugging, so it stores the redacted prompt rather than raw sensitive input.

Response includes:

- `prompt` and `sanitized_prompt`
- `redaction`
- `clarification`
- `policy_input` and `policy`
- `model_route`
- `tool_calls`
- `answer_sources` and `knowledge_citations`
- `trusted_source_score`
- correlated `audit_events`
- `trace_id`

## GET /controls/abuse

Requires manager or admin role.

Returns active production-style abuse and cost controls:

```json
{
  "api_gateway_throttling_rate_limit": 5,
  "api_gateway_throttling_burst_limit": 20,
  "max_request_chars": 2000,
  "quota_window_seconds": 86400,
  "role_quotas": {
    "employee": 25,
    "manager": 50,
    "admin": 100
  },
  "cloud_model_kill_switch": false,
  "bedrock_enabled": true,
  "request_body_limit_note": "Application rejects oversized prompts before policy/model routing; API Gateway enforces route throttles."
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
