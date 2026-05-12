# Recruiter and Hiring Manager Reviewer Script

Goal: show the project in under six minutes.

## Setup

Open three views:

1. Employee chat
2. Manager approval queue
3. Admin governance dashboard

Before presenting, switch to `Admin` and click `Seed` so the governance dashboard has audit history. For a shorter path, click `Walkthrough` in the top bar and run the four guided steps.

## 30-Second Introduction

Say:

> AegisDesk is a secure AI gateway for cloud operations teams. It lets employees use AI for incident triage, access requests, and support workflows while the company controls privacy, cost, permissions, approvals, and audit logs.

## Flow 1: Helpful AI Support

Prompt:

> The checkout service is timing out. What should I check first?

Show:

- AI answer
- Model used
- Route reason and trace ID
- CloudWatch-style incident context when the checkout incident prompt is used

Explain:

> This is the simple employee-facing experience. The gateway is using read-only incident evidence, policy, model routing, and audit logging behind the answer.

## Flow 2: Secret Detection

Prompt:

> Here is the error log with an example database secret and customer email customer@example.test. Why is this failing?

Show:

- Sensitive values redacted
- Warning badge
- Local model route or cloud route blocked
- Admin event

Explain:

> The system detects sensitive values before the model call. The user still gets help, but the company does not blindly send secrets to an external provider.

## Flow 3: Policy Enforcement

Prompt:

> Give me admin access to the production database.

Show:

- Denied result
- Plain-English denial explanation
- OPA policy ID underneath
- Safer alternative: temporary read-only access with approval
- Backend-derived employee role from verified token claims

Explain:

> This is policy-as-code. The AI cannot bypass access rules just because the request is written in natural language.

## Flow 4: Manager Approval

Manager approves:

> Temporary read-only database access for incident INC-1042, expires in 2 hours.

Show:

- Approval record
- Scoped permission
- Requester and approver identity
- Decision timestamp
- Before and after audit events
- Audit event

Explain:

> Risky actions move through a human approval workflow. This is how AI becomes usable in enterprise operations.

## Flow 5: Admin Governance

Show:

- Requests today
- Estimated AI cost
- Local vs cloud model route
- Redactions
- Tool calls
- Denied actions
- Approval status
- Trace IDs
- Audit event filters by request ID, user, decision, route, and tool

Explain:

> The admin view turns AI from an uncontrolled chat tool into an observable platform.

## Flow 6: Cost Governance

Prompt as Manager or Admin:

> Why did our AI and cloud costs spike this week?

Show:

- AWS Cost Explorer path
- DynamoDB cache indicator when repeated
- Role-gated access
- Cost summary event in the audit trail

Explain:

> Cost governance is part of the product. Managers can investigate spend, while employees cannot trigger broad cost queries.

## Closing Statement

Say:

> The main point of this project is not the chatbot. The point is the control plane: policy, cost, privacy, observability, and safe tool execution around AI workflows.
