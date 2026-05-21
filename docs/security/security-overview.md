# Security Overview

## Security Model

AegisDesk is designed around a backend control plane. The frontend never decides whether a user is allowed to act. The API verifies identity, evaluates policy, redacts sensitive data, routes models, controls tools, writes audit events, and returns the decision trail.

## Core Controls

| Control | Implementation |
| --- | --- |
| Identity verification | Cognito Hosted UI and JWKS-verified ID tokens; local persona issuer for self-hosted evaluation |
| Authorization | OPA/Rego policies for chat, tools, model routing, quotas, and approvals |
| Sensitive data handling | PII and secret detection before model routing |
| Model governance | Bedrock route only for approved low-sensitivity requests; external model kill switch |
| Approval workflow | Scoped production access requests require manager/admin decision |
| Auditability | DynamoDB or SQLite audit events with request replay |
| Cost controls | Role quotas, request size limits, API Gateway throttling, Cost Explorer cache |
| Observability | Structured logs and OpenTelemetry trace IDs |
| Customer data boundary | Strict mode blocks external model calls and local fixture incident data |

## Common Security Questions

### What data is stored?

AegisDesk stores audit events, approval requests, model route records, quota counters, metrics summaries, and cached cost summaries. Request replay can include the original prompt, sanitized prompt, redaction metadata, policy input/output, tool calls, answer sources, and trace ID.

### What data is sent to Bedrock?

Only sanitized request text and selected trusted context are sent to Bedrock when policy allows an external model route. Secrets and detected PII are redacted before routing. Denied requests, approval-gated requests, and sensitive requests can stay on the local control path.

### Are prompts retained?

Prompts are retained in the audit store so governance reviewers can inspect request replay. The short-term retention window is controlled by `AEGISDESK_AUDIT_RETENTION_DAYS`. SQLite prunes expired audit events before evidence reads and exports; hosted DynamoDB records include `expires_at` for TTL. For stricter environments, store only sanitized prompts or add an immutable archive with a separate legal-hold policy.

### Can external models be disabled?

Yes. Set `AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true` or leave `AEGISDESK_ENABLE_BEDROCK=false`. The API will use the local control route and will not call Bedrock.

For customer pilots that require a harder boundary, set `AEGISDESK_DATA_BOUNDARY_MODE=customer_strict`. This also blocks local fixture incident context so the main workflow must use configured customer integrations.

### How are audit logs exported?

Hosted deployments store audit events in DynamoDB and emit structured logs to CloudWatch. Manager/admin users can export short-term JSON or CSV evidence from `/audit/export`. Customers can export DynamoDB records to S3, stream changes through DynamoDB Streams, or forward CloudWatch logs to a SIEM.

### How are secrets redacted?

The API inspects prompts for credential-like patterns and PII before policy and model routing. Redaction findings are included in the response and audit record so reviewers can verify whether sensitive values were removed.

### Does it support SSO?

The current hosted path uses Amazon Cognito Hosted UI with JWKS verification. The identity boundary is compatible with OIDC providers such as Okta and Microsoft Entra ID through Cognito federation or a direct JWKS-compatible issuer.

### Can we self-host?

Yes. The repo includes Docker Compose for local/self-hosted runtime and Terraform for AWS deployment. See [Self-Hosted Deployment](../deployment/self-hosted.md).

## Recommended Production Controls

- Use customer-owned OIDC/SSO instead of local persona tokens
- Disable external models until data-handling review is approved
- Configure retention for prompts and audit events
- Encrypt DynamoDB and S3 with customer-managed keys when required
- Forward audit logs to the company SIEM
- Limit Bedrock model access to approved model IDs
- Use ticketing and access adapters connected to real approval systems
- Add customer-specific Rego rules for teams, data classes, and environments
