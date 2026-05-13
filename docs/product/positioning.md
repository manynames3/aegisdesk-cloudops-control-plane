# Product Positioning

## Category

AegisDesk is a self-hosted CloudOps AI control plane for companies that want employee-facing AI assistance without giving up control over identity, policy, sensitive data, approvals, model routing, cost, and audit evidence.

## One-Liner

Give employees AI help for incidents, tickets, access requests, and cloud cost questions while enforcing identity, policy, redaction, approval, model routing, and audit trails.

## Why This Exists

CloudOps teams already use AI to move faster during incidents and operational support work. The problem is that unmanaged chat tools do not provide the controls a company needs:

- Verified identity and role-aware decisions
- Redaction before data reaches an external model
- Policy enforcement outside the model response
- Approval workflows for production access
- Cost-aware model routing and usage controls
- Evidence for security, compliance, and management review

AegisDesk puts those controls in front of the AI workflow.

## Target Customer

The initial target customer is a mid-market or enterprise engineering organization with:

- Cloud operations or platform engineering teams
- AWS usage and growing AI adoption
- Existing SSO, ticketing, logging, and audit requirements
- Security or compliance concern around uncontrolled AI usage
- A need to show cost governance for AI and cloud operations

## Product Promise

AegisDesk should make the approved path easier than the unsafe path. Employees can ask operational questions naturally, but the system decides when to answer, when to redact, when to use Bedrock, when to stay local, when to call tools, and when to route for approval.

## Differentiation

- It is not just a chatbot. It is the control layer around CloudOps AI.
- Policy decisions are made by OPA/Rego, not hidden in a prompt.
- Identity, role, team, and quota are evaluated by the backend.
- Every response includes source, policy, route, and audit context.
- The integration layer is adapter-based, so customers can connect Jira, ServiceNow, CloudWatch, Datadog, Okta, Entra, Cognito, Slack, Teams, and MCP clients without rewriting the control logic.

## Product Boundary

AegisDesk does not directly mutate production systems by default. It supports read-only incident context, ticket creation, governed access requests, cost summary lookup, and approval workflows. Destructive actions should remain behind customer-specific approval and change-management controls.
