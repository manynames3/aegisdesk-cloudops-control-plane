# Threat Model

This threat model is scoped to the current self-hosted implementation and the documented customer production path.

## Assets

- User identity and role claims
- Internal support requests
- Incident details
- Logs and operational data
- Secrets and credentials
- Customer PII
- Tool execution permissions
- Audit logs
- Cost and usage data

## Threats

### 1. Sensitive Data Leakage

Risk:

User pastes secrets, customer data, or internal incident details into the chat.

Controls:

- Secret detection
- PII redaction
- Local model routing for sensitive content
- Cloud route blocking for high-risk content
- Audit events for redaction findings

### 2. Unauthorized Tool Use

Risk:

User asks the AI to perform an action they are not allowed to perform.

Controls:

- OPA policy check before every tool call
- Role-based action matrix
- Approval workflow for sensitive actions
- Schema validation for tool inputs

### 3. Prompt Injection

Risk:

Malicious text in a document or prompt tells the agent to ignore policy or leak data.

Controls:

- Policy enforced outside the model
- Tool calls evaluated by gateway, not by model alone
- System instructions separated from user/tool content
- Control evals for policy denial, routing, redaction, and tool authorization

### 4. Cost Abuse

Risk:

Users trigger expensive model calls or high-volume usage.

Controls:

- Per-request cost estimate
- Budget-aware route decisions
- Admin dashboard usage visibility
- Optional quota policies

### 5. Audit Tampering

Risk:

Actions occur without traceability or logs are modified.

Controls:

- Append-style event model
- Trace IDs linked to requests
- Production path: immutable storage or write-once audit sink

### 6. Over-Privileged Cloud Credentials

Risk:

Tool layer uses credentials that are broader than required.

Controls:

- Destructive actions remain approval-only in the current implementation
- Customer production path uses scoped IAM roles
- Short-lived credentials
- Separate read-only and write-capable tools
- Approval required for privileged operations

## Current Non-Goals

- Real production access grants
- Real destructive cloud operations
- Full enterprise identity federation
- Full compliance certification
- Real prompt-injection corpus coverage

## Production Hardening Path

- OIDC integration with Entra ID, Okta, or Cognito
- Managed secrets
- Tenant isolation
- Immutable audit storage
- SAST/DAST and container scanning
- Signed container images
- Network policies
- Rate limits and quotas
- Formal incident response runbook
