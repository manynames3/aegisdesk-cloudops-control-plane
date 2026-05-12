# Production Access Control Policy

| Field | Value |
| --- | --- |
| Document ID | POL-SEC-014 |
| Owner | Security Engineering |
| Applies to | Production cloud resources, databases, and privileged tools |
| Review cadence | Semiannual |
| Last reviewed | 2026-04-20 |
| Classification | Internal Restricted |

## Purpose

This policy defines how AegisDesk handles production access requests made through AI-assisted CloudOps workflows. The policy exists to prevent natural-language requests from bypassing identity, authorization, approval, or audit controls.

## Core Rule

Production admin access is not self-service. Employees cannot receive production admin privileges through chat, ticket automation, or agent tool invocation.

## Approved Access Pattern

When an employee needs production evidence, the approved path is:

1. Request temporary read-only access.
2. Provide an incident ID, business justification, and expected duration.
3. Route the request to a manager or admin approver.
4. Record the approval decision and timestamp.
5. Grant only the minimum scoped permission needed.
6. Expire access automatically.
7. Preserve the audit trail.

## Denied Patterns

The following requests must be denied:

- production admin access
- standing privileged access
- direct credential disclosure
- bypassing manager approval
- destructive database operations
- disabling monitoring or audit controls
- broad access without an incident or ticket reference

## Manager Approval Requirements

Manager approval is required for temporary read-only production access. Approval records must include:

- requester identity
- approver identity
- resource
- permission
- incident or ticket reference
- decision timestamp
- expiration window
- policy reason

## AI Gateway Enforcement

The AI gateway must enforce this policy outside the model. The model may explain the policy, but it must not decide access by itself.

Required controls:

- identity derived from verified token claims
- OPA/Rego policy decision
- tool allow, deny, or approval-required result
- audit event for the request
- audit event for the approval decision
- no trust in frontend-submitted role fields

## User-Facing Explanation

When production admin access is denied, the system should explain:

> Production admin access is not self-service. A safer temporary read-only request can be routed for manager approval.

The answer should show the technical policy ID separately from the plain-English explanation.
