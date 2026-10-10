# Technical Review Evidence

Use this page as the starting point for a senior hiring manager or technical buyer who wants proof paths instead of product copy.

## Live URLs

- Product page: <https://d27myiy7bbj1rz.cloudfront.net/marketing>
- Control plane: <https://d27myiy7bbj1rz.cloudfront.net>
- API health: <https://c2wcg4cdef.execute-api.us-east-1.amazonaws.com/health>

## CI And Deploy

- CI workflow: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/ci.yml>
- AWS deploy workflow: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/deploy-aws.yml>
- Passing runtime release CI: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027293724>
- Verified AWS deployment: <https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027407776>
- Live operations evidence: [live-operations.md](live-operations.md)

The deploy workflow uses GitHub OIDC, Terraform plan, manual environment-gated apply, frontend publish, CloudFront invalidation, and API smoke test.

## Key Code Paths

### Incident Release (2026-10-10)

The persistent incident workspace and divided-A branding are deployed at runtime revision `e80927c41f87de8cf95fff5799ed447df278902c`. [Incident operations and verification](../operations/incident-workflow.md) describes configuration, failure handling, storage boundaries, and controlled test screenshots. `services/api/app/incidents.py` implements team-scoped cases and exact-action approval/dispatch/reconciliation; `services/api/tests/test_incidents.py` exercises failure and concurrency paths. The UI is isolated in `apps/web/app/incident-workspace.tsx`.

Hosted `/health` and `/health/ready` returned 200 with DynamoDB and OPA subprocess readiness. Anonymous `GET /incidents` returned 401; a Cognito evaluation persona's authenticated request returned 200. The CloudFront wordmark/favicon matched the committed SVG files exactly, and desktop/mobile app rendering and `/marketing` were checked with Playwright. Hosted case writes and live Jira/CloudWatch workflows remain unverified. No incident was created and no external tool was executed during this hosted smoke check.

Verification: 61 API tests, 13 Playwright tests (five workflow tests and eight branding checks), six control evals, and nine OPA tests passed. Production frontend build/type checking, Terraform fmt/validate, secret scanning, dependency compatibility, MCP smoke, and all three container builds passed in the release CI. Local load smoke completed 20 controlled requests without failure; this is not a hosted performance benchmark. Local focused Ruff checks, edited-document relative links, and `git diff --check` passed. The frontend dependency audit reported zero vulnerabilities.

The first [CI run](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027124572) caught an incompatible MCP 2.x import. Constraining the existing SDK requirement to its supported 1.x API restored the MCP smoke test; the complete release CI then passed. No new production dependency was introduced.

Hosted setup still reports evaluation personas, local legacy adapters, and unconfigured Jira/CloudWatch. Deployment uploaded the Lambda artifact, updated the existing Lambda function, published the frontend, and requested CloudFront invalidation; no resource was destroyed. The [hosted screenshot](screenshots/incident-hosted-desktop.png) shows the actual empty evaluation queue. Controlled Jira lifecycle screenshots remain explicitly labeled local tests, not customer operational evidence.

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
