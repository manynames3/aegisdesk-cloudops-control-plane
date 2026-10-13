# Trace Sample

Every chat response includes a `trace_id` field, and request replay preserves it alongside redaction, policy, routing, sources, and audit events. Without a configured trace exporter it can be `trace-unavailable`. The separate server-generated request correlation ID does not prove trace export.

## Illustrative Replay Shape

This schematic example is not a captured OpenTelemetry trace or hosted span export. It shows a local decision without an available trace; the request ID is a placeholder.

```json
{
  "request_id": "<chat-request-id>",
  "trace_id": "trace-unavailable",
  "actor": {
    "user_id": "u-1001",
    "role": "employee",
    "team": "payments"
  },
  "sanitized_prompt": "Here is the checkout log with token=[REDACTED_CREDENTIAL] and [REDACTED_EMAIL]. Why is this timing out?",
  "policy_input": {
    "intent": "incident_triage",
    "redaction": {
      "pii_detected": true,
      "secrets_detected": true
    }
  },
  "model_route": {
    "provider": "local",
    "reason": "secrets_detected_and_redacted",
    "external_call": false
  },
  "audit_events": [
    "quota.allowed",
    "request.received",
    "redaction.completed",
    "policy.allowed",
    "model.route.selected",
    "response.completed"
  ]
}
```

## Where To Inspect It

- UI: Governance tab, select an audit event, then inspect Request Replay
- API: `GET /requests/{request_id}/replay`
- Logs: search Lambda logs by `trace_id` or `X-AegisDesk-Error-ID`
- Local tracing: run Docker Compose and open Jaeger at `http://localhost:16686`

## Production Next Step

For a customer pilot, export one OpenTelemetry trace from the customer environment and attach a screenshot or JSON span export to this evidence folder.
