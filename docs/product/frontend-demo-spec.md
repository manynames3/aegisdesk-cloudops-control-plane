# Frontend Demo Spec

The frontend should make the enterprise value obvious within one minute.

## Navigation

Primary tabs:

- Chat
- Approvals
- Governance
- Evaluations

## Screen 1: Chat

Audience:

- Employee
- Recruiter
- Hiring manager

Purpose:

Show that AegisDesk is useful, not only a governance dashboard.

Key UI elements:

- Chat transcript
- Suggested actions
- Source/runbook references
- Model route badge
- Estimated cost
- PII/secret warning badge
- Policy decision badge
- Tool call result

Demo prompts:

- `The checkout service is timing out. What should I check first?`
- `Create a ticket for the VPN outage and assign it to CloudOps.`
- `Here is the log with an example database secret. Why is this failing?`
- `Give me admin access to the production database.`

## Screen 2: Approvals

Audience:

- Manager
- Hiring manager

Purpose:

Show that risky actions are controlled by workflow, not model output.

Key UI elements:

- Approval queue
- Requestor
- Requested action
- Resource
- Risk level
- Policy reason
- Approve button
- Deny button
- Expiration/scoping fields

Example approval:

- Temporary read-only database access
- Incident ID: `INC-1042`
- Expiration: `2 hours`
- Scope: `read-only`

## Screen 3: Governance

Audience:

- Admin
- Security reviewer
- FinOps reviewer
- Senior cloud hiring manager

Purpose:

Show that AI activity is observable, auditable, and cost-aware.

Key UI elements:

- Total requests
- Estimated spend
- Local vs cloud model split
- Redactions count
- Denied actions count
- Approval count
- Tool calls table
- Policy decision table
- Request timeline
- Trace ID links

## Screen 4: Evaluations

Audience:

- Senior hiring manager
- Security reviewer

Purpose:

Show that controls are tested.

Key UI elements:

- Secret leakage tests
- PII redaction tests
- Prompt injection tests
- Unauthorized tool use tests
- Model routing tests
- Pass/fail summary

## Design Principle

The UI should not lecture users about the architecture. It should expose decisions naturally:

- Why was this model selected?
- Why was this tool allowed or denied?
- What data was redacted?
- What did this request cost?
- Who approved this action?
- Where is the audit trail?
