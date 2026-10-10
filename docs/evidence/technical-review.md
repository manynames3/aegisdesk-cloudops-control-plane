# Technical Review Evidence

Use this page as the starting point for a senior hiring manager or technical buyer who wants proof paths instead of product copy.

## Live URLs

- Product page: <https://d27myiy7bbj1rz.cloudfront.net/marketing>
- Control plane: <https://d27myiy7bbj1rz.cloudfront.net>
- API health: <https://c2wcg4cdef.execute-api.us-east-1.amazonaws.com/health>

## CI And Deploy

- CI workflow: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/ci.yml>
- AWS deploy workflow: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/deploy-aws.yml>
- Latest passing CI observed before this readiness pass: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/26163874100>
- Live operations evidence: [live-operations.md](live-operations.md)

The deploy workflow uses GitHub OIDC, Terraform plan, manual environment-gated apply, frontend publish, CloudFront invalidation, and API smoke test.

## Key Code Paths

### Local Incident Increment (2026-10-10)

The persistent incident workflow has not been deployed. [Incident operations and verification](../operations/incident-workflow.md) describes its configuration, failure handling, storage boundaries, and controlled test screenshots. `services/api/app/incidents.py` implements team-scoped cases and exact-action approval/dispatch/reconciliation; `services/api/tests/test_incidents.py` exercises failure and concurrency paths. The new UI is isolated in `apps/web/app/incident-workspace.tsx`.

Live Jira/CloudWatch and DynamoDB case persistence remain unverified. Existing deploy links do not attest to these changes. Local screenshots show a controlled case and loopback Jira fixture; the evidence panel explicitly reports that CloudWatch is unavailable when not configured.

Local verification: 61 API tests, five Playwright tests (including the governed ticket lifecycle), six control evals, and nine OPA tests passed. Production frontend build/type checking and Terraform fmt/validate passed. Focused Ruff checks, edited-document relative links, and `git diff --check` passed. The security script found no high-confidence secrets, the updated frontend lockfile audited with zero vulnerabilities, and API dependency compatibility passed. MCP dependency checking was skipped because its environment was not installed; container builds, hosted incident persistence, and live integration tests were not run in this increment.

Read-only hosted setup inspection still reported evaluation personas, local ticket/incident adapters, and unconfigured Jira/CloudWatch. No production deployment or new AWS resources were created.

The 26 incident API tests also passed with the real local OPA executable in subprocess mode. CloudWatch/Jira remained controlled test adapters; this verifies local policy execution, not live external integrations.

| Control | Path |
| --- | --- |
| Chat gateway and request replay | `services/api/app/main.py` |
| Cognito/JWKS auth | `services/api/app/auth.py`, `services/api/app/cognito_auth.py` |
| OPA policy engine | `services/api/app/policy_engine.py`, `policies/*.rego` |
| Bedrock route | `services/api/app/model_router.py`, `services/api/app/llm.py` |
| Cost Explorer | `services/api/app/cost_explorer.py` |
| Ticket/incident/access adapters | `services/api/app/adapters.py`, `services/api/app/tools.py` |
| DynamoDB/SQLite store | `services/api/app/store.py` |
| Governance UI | `apps/web/app/page.tsx` |
| Terraform | `infra/terraform/main.tf` |

## Evidence Packet

- Integration contract tests: [integration-contract-tests.md](integration-contract-tests.md)
- Load smoke evidence: [load-smoke.md](load-smoke.md)
- Trace sample: [trace-sample.md](trace-sample.md)
- Architecture tradeoffs: [../architecture/tradeoffs.md](../architecture/tradeoffs.md)
- Production readiness matrix: [../architecture/production-readiness-matrix.md](../architecture/production-readiness-matrix.md)
- Security overview: [../security/security-overview.md](../security/security-overview.md)
- Customer data boundary: [../security/customer-data-boundary.md](../security/customer-data-boundary.md)
- Operational runbooks: [../operations/README.md](../operations/README.md)

## Manual Review Flow

1. Confirm `/health` and the product page load from AWS.
2. Run the guided walkthrough in the control plane.
3. Open Governance and inspect request replay for one sensitive request.
4. Export audit JSON.
5. Review CI for API tests, policy tests, Playwright smoke, MCP smoke, Terraform validate, container builds, and security scan.
6. Review deploy workflow and live operations evidence for OIDC, budget, Lambda logs, and API throttling.
