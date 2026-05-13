# Use Cases for CloudOps

## 1. Incident Triage Assistant

An engineer asks, "The checkout service is timing out. What should I check first?"

AegisDesk:

- Detects incident intent and extracts incident ID when present
- Redacts secrets and PII before model routing
- Retrieves trusted runbook guidance
- Loads read-only incident context through the incident adapter
- Routes approved low-sensitivity requests to Bedrock or local control fallback
- Shows citations, source score, policy result, and trace ID

## 2. Governed Ticket Creation

An employee asks the assistant to open a support ticket for a cloud operations issue.

AegisDesk:

- Clarifies missing system, impact, urgency, or owner fields
- Evaluates tool authorization through OPA/Rego
- Calls the configured `TicketAdapter`
- Records tool call status, policy reason, actor, and request ID

Supported adapter shape:

- `LocalTicketAdapter`
- `JiraTicketAdapter`
- `ServiceNowTicketAdapter`

## 3. Production Access Request

An employee asks for production database admin access.

AegisDesk:

- Denies unsafe admin access for employee role
- Offers a safer temporary read-only access path
- Routes scoped access to manager approval
- Captures requester, resource, permission, reason, status, approver, timestamp, and audit events

Supported adapter shape:

- `LocalApprovalAdapter`
- `OktaGroupRequestAdapter`
- `IAMIdentityCenterAdapter`

## 4. Cloud Cost Investigation

A manager asks why AI and cloud costs spiked this week.

AegisDesk:

- Enforces manager/admin access for cost investigation
- Queries AWS Cost Explorer when enabled
- Caches summaries in DynamoDB to reduce repeated billing API calls
- Shows largest driver, source, cache status, recommendation, estimated savings, and model route evidence

## 5. Governance Review

A security or platform reviewer selects a request from the audit explorer.

AegisDesk shows:

- Original prompt and sanitized prompt
- Redaction findings
- Policy input and output
- Model route and estimated cost
- Tool calls
- Answer sources and trusted citations
- Audit events
- Trace ID

## 6. Agent Client Access Through MCP

A developer or operator uses an agent client such as Codex to call governed tools.

AegisDesk:

- Exposes CloudOps tools through the MCP server
- Keeps tool behavior behind the same product boundary
- Provides a path for agent interoperability without bypassing policy and audit design
