# 30-Day Pilot Package

## Pilot Goal

Validate one governed CloudOps AI workflow with customer identity, one real operational integration, OPA policy, audit replay, and measurable operator value.

## Recommended First Workflow

Cost-governed CloudOps support:

1. Employee asks for incident, ticket, access, or cost help.
2. AegisDesk verifies identity and role/team claims.
3. Secrets and PII are redacted before model routing.
4. OPA decides whether the request is allowed, denied, or approval-gated.
5. Bedrock is used only for approved low-risk requests, or customer strict mode keeps all requests local.
6. DynamoDB stores audit events, route decisions, approvals, and replay evidence.
7. Managers export audit evidence for review.

## Onboarding Checklist

- Confirm buyer, executive sponsor, and technical owner
- Pick one workflow: incident triage, ticket creation, access approval, or cost review
- Configure Cognito federation or customer JWKS issuer
- Connect CloudWatch Logs or Cost Explorer
- Connect Jira or ServiceNow if ticket creation is part of the pilot
- Choose data boundary mode: evaluation or customer strict
- Set retention, export, and kill-switch defaults
- Run recorded contract tests and one live smoke test
- Agree on success metrics and weekly review cadence

## Success Metrics

| Metric | Target |
| --- | --- |
| Activation | 5-10 operators complete the workflow without vendor help |
| Governance | 100% of requests have replayable policy, route, tool, and audit evidence |
| Safety | No sensitive values sent to external models in strict or redacted flows |
| Time saved | 20% reduction in first-response or handoff time for the selected workflow |
| Cost control | Bedrock calls, Cost Explorer calls, quotas, and throttles are visible |

## Pricing

Suggested starting offer: `$2,500-$7,500` paid 30-day pilot, credited toward an annual self-hosted license.

Annual license after pilot: `$18,000-$60,000/year` depending on integrations, support, and deployment ownership.

## Bad-Fit Criteria

- No AWS footprint
- No team willing to connect identity and at least one operational system
- Buyer wants unrestricted employee ChatGPT, not governed operational workflows
- Requirement for direct production mutations from chat without approval controls
- No owner for policy, audit, or incident response workflows

## What Is Not Included

- Custom destructive automation
- Customer-specific compliance certification
- Full SIEM/data lake integration
- Multi-region active-active deployment
- Unlimited integration development
