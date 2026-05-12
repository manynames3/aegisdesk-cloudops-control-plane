# Portfolio Review Checklist

Use this before applying to jobs.

## Recruiter-Level Review

- README explains the project in plain English.
- Screenshots show a real frontend.
- Demo video is under six minutes.
- The first 30 seconds explain why the project matters.
- Use cases are obvious without deep technical knowledge.
- Resume bullets match the project exactly.

## Senior Hiring Manager Review

- Docker Compose demo works from clean checkout.
- API has tests.
- OPA policies have tests.
- Security controls are not only UI labels.
- API derives role from JWKS-verified token claims, not request body fields.
- Tool calls are actually policy checked.
- Audit events are real records.
- Cost routing is real for Bedrock and deterministic when falling back.
- Quotas are enforced before model/tool execution.
- Failure cases are documented.
- Production hardening path is honest.

## Cloud Role Evidence

- Containerized services
- CI pipeline
- AWS Terraform that validates and deploys the low-cost hosted demo
- Kubernetes/Helm path only if target roles require it
- Observability
- Secrets handling plan
- Least-privilege design
- Cost governance
- Manual deployment workflow
- Deployment runbook

## Red Flags To Avoid

- Listing tools that are not implemented
- Calling the project enterprise-grade without evidence
- Fake admin dashboard numbers with no event model
- Kubernetes files that do not render
- Terraform that cannot validate
- No tests
- No security model
- No explanation of tradeoffs
