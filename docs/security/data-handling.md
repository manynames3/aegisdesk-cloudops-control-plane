# Data Handling

## Data Classes

| Data class | Examples | Default handling |
| --- | --- | --- |
| Identity claims | user ID, role, team | Verified by API and stored in audit events |
| Prompt text | employee request | Redacted before model routing; raw prompt is not intentionally persisted in replay |
| Sanitized prompt | prompt after redaction | Used for policy, routing, and model calls |
| Redaction metadata | finding type, label, replacement | Stored for governance review |
| Policy data | input and decision output | Stored in audit events and request replay |
| Tool data | ticket ID, approval ID, cost summary, incident source | Stored as tool call results |
| Model route data | provider, model, reason, estimated cost | Stored for cost and audit reporting |
| Operational context | incident logs, runbook excerpts | Attached only when relevant and shown as answer sources |

## Data Sent to External Models

When Bedrock is enabled and policy allows the route, AegisDesk sends:

- Sanitized user request
- Selected internal knowledge context
- High-level intent context

AegisDesk does not intentionally send:

- Raw detected secrets
- Raw detected PII
- Denied production admin requests
- Approval workflow state beyond what is needed to answer the user

## Data Stored Locally or in AWS

Local Docker Compose uses SQLite for API state unless configured otherwise. AWS deployments use DynamoDB for audit events, approvals, route records, metrics, quota counters, and cache entries.

## Prompt Retention Choices

Recommended retention modes:

| Mode | Behavior |
| --- | --- |
| Full audit | Store raw and sanitized prompts for request replay |
| Sanitized audit | Store sanitized prompts only |
| Minimal audit | Store metadata, policy, route, and tool evidence without prompt body |

The current implementation uses sanitized audit for request replay: the prompt preview and replay prompt are generated from redacted text. Customers with stricter requirements can enable customer data boundary mode and reduce audit export windows before production rollout.

## Customer Data Boundary Mode

Set `AEGISDESK_DATA_BOUNDARY_MODE=customer_strict` to enforce the strictest customer posture:

- external model routes are forced to local control before Bedrock is called
- local fixture incident context is blocked; a real integration such as CloudWatch is required
- setup status reports whether fixture data and external models are allowed
- boundary decisions are written to audit events

See [Customer Data Boundary Mode](customer-data-boundary.md).

## Redaction

Redaction runs before model routing. Findings are returned in the response and stored in audit metadata so reviewers can confirm whether secrets or PII were removed.

## Audit Export

Available export path:

- `GET /audit/export` returns manager/admin-scoped JSON evidence for the current audit window
- `GET /audit/export?format=csv` returns manager/admin-scoped CSV evidence for security review

Recommended production archive paths:

- DynamoDB export to S3 for long-term archive
- DynamoDB Streams to a security data lake
- CloudWatch log subscription to SIEM

Configure the short-term product window with:

```bash
AEGISDESK_AUDIT_RETENTION_DAYS=30
AEGISDESK_AUDIT_EXPORT_MAX_EVENTS=500
```

Retention is enforced in the local SQLite store when audit events are read or exported. Hosted DynamoDB records include an `expires_at` attribute for DynamoDB TTL, and export/replay paths prune expired audit records before returning evidence.

## External Model Disablement

External model calls can be disabled through:

```bash
AEGISDESK_ENABLE_BEDROCK=false
AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true
```

With those settings, AegisDesk keeps requests on the local control path.
