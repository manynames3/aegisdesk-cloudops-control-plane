# Use Cases

These are the use cases the MVP should demonstrate clearly in the UI. Each use case is chosen because it is easy for recruiters to understand and meaningful enough for a senior cloud hiring manager to evaluate.

## Use Case 1: Cloud Incident Triage

### Scenario

An employee says:

> The checkout service is timing out. Here is the log excerpt.

### System Behavior

- Detects secrets or customer data in the pasted log.
- Redacts sensitive values.
- Searches approved runbooks.
- Summarizes likely cause.
- Suggests next steps.
- Offers to create an incident ticket.
- Logs model route, redaction result, and tool call.

### Enterprise Value

- Faster incident response
- Reduced accidental data leakage
- Consistent runbook-driven troubleshooting
- Auditable support workflow

## Use Case 2: Production Access Request

### Scenario

An employee says:

> Give me admin access to the production database so I can debug this.

### System Behavior

- Identifies this as a privileged action.
- Checks user role and request context.
- Runs OPA policy.
- Denies direct admin access.
- Suggests temporary read-only access tied to an incident ticket.
- Sends approval request to a manager.
- Records the policy decision and reason.

### Enterprise Value

- Least-privilege access
- Reduced production risk
- Clear approval trail
- Strong demo of policy-as-code

## Use Case 3: Cost Spike Investigation

### Scenario

An engineering manager says:

> Why did our AI and cloud costs spike this week?

### System Behavior

- Calls a mock cloud cost MCP tool.
- Summarizes usage by team, service, model, and time period.
- Identifies high-cost request patterns.
- Suggests lower-cost routing or caching options.
- Shows estimated savings.

### Enterprise Value

- FinOps visibility
- Executive-friendly cost explanation
- Practical cloud governance
- Demonstrates AI cost management

## Use Case 4: Model Routing Decision

### Scenario

Two users ask similar questions:

1. A public documentation question
2. A question containing internal incident details

### System Behavior

- Routes public/low-risk request to a cloud model if configured.
- Routes sensitive request to local Ollama or blocks it.
- Shows route reason in admin dashboard.
- Tracks estimated cost and budget impact.

### Enterprise Value

- Cost-conscious AI usage
- Privacy-aware architecture
- Vendor flexibility
- Clear model governance

## Use Case 5: Ticket Automation Through MCP Tools

### Scenario

An employee says:

> Create a ticket for the VPN outage and assign it to CloudOps.

### System Behavior

- Converts request into a structured tool call.
- Checks whether the user can create that type of ticket.
- Calls the ticket MCP tool.
- Returns ticket ID and status.
- Logs tool name, inputs, result, and policy decision.

### Enterprise Value

- Practical workflow automation
- Demonstrates controlled tool use
- Shows MCP interoperability in a business workflow

## Use Case 6: Governance Report

### Scenario

An admin clicks:

> Generate AI governance summary

### System Behavior

- Summarizes request volume, cost, redactions, denied actions, approvals, tool usage, and eval results.
- Produces an exportable markdown or PDF report.

### Enterprise Value

- Compliance evidence
- Executive reporting
- Clear proof that controls are measurable

