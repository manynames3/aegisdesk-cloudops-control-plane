# Technical Reviewer Guide

This is a production-style AWS/cloud engineering work sample, not proof of a production customer service. Start with the dated evidence and inspect the failure controls before evaluating the AI interface.

## First Five Minutes

1. Read the [README summary and evidence matrix](../README.md).
2. Inspect the [C4 context/container diagrams](architecture.md) and [ADR-012](adrs/012-persistent-incident-actions.md) for the approval/dispatch boundary.
3. Review [release CI and hosted smoke evidence](evidence/technical-review.md) alongside the [successful AWS deployment](evidence/live-operations.md). Hosted case listing is verified; hosted case writes and live ticket execution are not.
4. Read the [incident failure/reconciliation tests](../services/api/tests/test_incidents.py) and [operations procedure](operations/incident-workflow.md).
5. Open the [live evaluation](https://d27myiy7bbj1rz.cloudfront.net), inspect the actual empty queue, then use Walkthrough/Governance for the supporting evaluation flow.

## Implementation Map

| Area | Inspect |
| --- | --- |
| Infrastructure | [Terraform resources and IAM](../infra/terraform/main.tf), [variables](../infra/terraform/variables.tf) |
| Backend | [Incident lifecycle](../services/api/app/incidents.py), [store](../services/api/app/store.py), [auth](../services/api/app/auth.py), [policy](../services/api/app/policy_engine.py) |
| Frontend | [Incident workspace](../apps/web/app/incident-workspace.tsx), [chat/governance shell](../apps/web/app/page.tsx) |
| Tests | [Incident API tests](../services/api/tests/test_incidents.py), [API regression tests](../services/api/tests/test_api.py), [Playwright](../apps/web/tests), [Rego](../policies) |
| Delivery | [CI](../.github/workflows/ci.yml), [manual deploy](../.github/workflows/deploy-aws.yml), [Lambda packaging](../scripts/build-lambda-package.sh) |
| Operations | [Runbooks](operations/README.md), [incident recovery](operations/incident-workflow.md), [setup/rotation/teardown](deployment/self-hosted.md) |
| Evidence | [Hosted and controlled screenshots](../README.md#screenshots), [CI/test boundaries](evidence/technical-review.md), [historical logs/budget](evidence/live-operations.md) |

## What The Evidence Demonstrates

- AWS delivery through Terraform, OIDC credentials, a reviewed manual deploy path, static publication, invalidation, and health checks.
- Backend identity, team scoping, model-independent policy, redaction, and exact-action human approval.
- Explicit handling of version conflicts, policy failures, stale evidence, external ambiguity, and reconciliation.
- Automated API/browser/policy/MCP/container checks and a documented operational owner workflow.

It does not demonstrate production scale, measured customer impact, enterprise compliance, immutable audit retention, or a real end-to-end customer incident.

## Decisions Worth Discussing

- OPA is independently testable; model fluency cannot authorize a tool call.
- A stored execution claim prevents concurrent duplicate dispatch of one action, but cannot make Jira and DynamoDB an atomic transaction. Ambiguity remains visible.
- Lambda/DynamoDB reduce idle operational overhead; cold starts, bounded snapshots, query access patterns, and recovery still need deliberate handling.
- Deterministic fallback and strict boundary mode preserve controls when external AI is disabled. They are not network isolation or a substitute for customer-specific IAM.
- The deployment workflow replans during apply rather than promoting the preflight plan, and does not automatically require a passing CI run. These are explicit delivery gaps, not hidden guarantees.

See [ADRs](adrs/README.md), [tradeoffs](architecture/tradeoffs.md), and the [readiness matrix](architecture/production-readiness-matrix.md).

## Run Or Inspect

Use the [README local setup and validation commands](../README.md#local-run) or [self-hosted guide](deployment/self-hosted.md). No AWS account is required for the local evaluation. Adapter fixtures and test doubles are isolated test evidence; running them does not connect customer systems.

Next engineering evidence: one real sandbox CloudWatch/Jira workflow, hosted case write and recovery verification, defined retention/backups, a real exported trace, and actionable alerts. Review [limitations](support/known-limitations.md) and the [incident remaining scope](operations/incident-workflow.md#verification-and-remaining-scope) before treating it as end-user ready.
