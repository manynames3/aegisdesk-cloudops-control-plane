# Data Handling

## Data Classes

| Data class | Examples | Default handling |
| --- | --- | --- |
| Identity claims | user ID, role, team | Verified by API and stored in audit events |
| Prompt text | employee request | Redacted before model routing; retained for request replay by default |
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

The current implementation uses full audit because request replay is a core governance feature. Customers with stricter requirements should switch to sanitized or minimal audit before production rollout.

## Redaction

Redaction runs before model routing. Findings are returned in the response and stored in audit metadata so reviewers can confirm whether secrets or PII were removed.

## Audit Export

Recommended export paths:

- DynamoDB export to S3 for long-term archive
- DynamoDB Streams to a security data lake
- CloudWatch log subscription to SIEM
- API endpoint export for governance reviewers

## External Model Disablement

External model calls can be disabled through:

```bash
AEGISDESK_ENABLE_BEDROCK=false
AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true
```

With those settings, AegisDesk keeps requests on the local control path.
