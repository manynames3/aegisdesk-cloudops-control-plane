# AI And Cloud Cost Governance Policy

| Field | Value |
| --- | --- |
| Document ID | GOV-FINOPS-007 |
| Owner | FinOps And Platform Engineering |
| Applies to | AI model usage, cloud operations tooling, and cost investigation workflows |
| Review cadence | Quarterly |
| Last reviewed | 2026-05-05 |
| Classification | Internal |

## Purpose

This policy defines how AegisDesk manages AI and cloud spend in governed CloudOps workflows. It supports fast incident response while keeping model usage, cloud API calls, and operational automation accountable to team budgets.

## Cost Governance Principles

1. Route sensitive or internal operational context locally when possible.
2. Use cloud models only for approved low-sensitivity requests.
3. Cache repeated cost summaries to avoid duplicate billing API calls.
4. Attribute requests to a user, role, team, model, and trace ID.
5. Enforce role and team quotas before expensive model or tool execution.
6. Deny or require approval for broad cost investigations by employees.
7. Record estimated cost and route decision for every request.

## Approved Cost Investigation Pattern

Managers and admins may request cost summaries when they need to investigate spend spikes, route changes, model usage, or cloud service drivers.

The system should:

- query AWS Cost Explorer when enabled
- use a DynamoDB cache when a recent summary exists
- show the largest cost driver
- recommend a control action
- record cache hit status
- include the trace ID and requester identity

## Employee Restrictions

Employees should not trigger broad cost investigations. Employee cost requests require manager or admin access because billing data can expose business-sensitive usage patterns, project priorities, and vendor spend.

Employees may ask for general cost-safe behavior, such as:

- how to avoid unnecessary model calls
- why sensitive prompts are routed locally
- how to request a manager review

## AI Spend Controls

The control plane should expose:

- local vs cloud model route counts
- estimated model spend
- quota usage
- denied high-cost requests
- cache hit indicators
- route reasons
- monthly budget guardrail

## Recommended Response Pattern

When explaining a cost spike, the answer should identify:

1. source of the cost data
2. reporting window
3. largest driver
4. cache status
5. recommended governance action

The model should not invent billing figures. If Cost Explorer is unavailable, the system should label deterministic fallback data clearly.
