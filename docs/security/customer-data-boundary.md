# Customer Data Boundary Mode

Customer data boundary mode is the strictest runtime posture for a customer pilot. It is intended for environments where incident logs, prompts, ticket details, and access requests must remain inside the customer-controlled boundary unless an administrator explicitly enables an external path.

## Enable It

```bash
AEGISDESK_DATA_BOUNDARY_MODE=customer_strict
AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true
AEGISDESK_ENABLE_BEDROCK=false
AEGISDESK_INCIDENT_CONTEXT_ADAPTER=cloudwatch
AEGISDESK_TICKET_ADAPTER=jira # or servicenow
```

## Enforced Behavior

| Boundary | Behavior |
| --- | --- |
| External model calls | Blocked before any Bedrock call; route becomes `customer-data-boundary-local-control` |
| Fixture data | Local incident fixtures fail closed; CloudWatch or another real adapter is required |
| Audit retention | Request replay stores sanitized prompt evidence and policy/tool metadata |
| Tooling | Ticket and incident workflows must use configured adapters, not local fixtures |
| Evidence | Boundary decisions are written as audit events for governance review |

## When To Use It

- First production-like pilot with customer incident logs
- Security review before enabling Bedrock
- Regulated or high-sensitivity CloudOps environments
- Customer environments that want AI governance before AI generation

## Limits

Redaction is a defense-in-depth control, not a guarantee that every sensitive value will be detected. Strict mode prevents external model calls, but administrators still need to choose retention windows, configure SSO, scope IAM permissions, and connect real operational systems.
