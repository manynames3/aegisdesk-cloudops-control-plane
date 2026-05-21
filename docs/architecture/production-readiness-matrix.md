# Production Readiness Matrix

| Area | Status | Evidence | Next step |
| --- | --- | --- | --- |
| Live AWS deployment | Implemented | CloudFront, API Gateway, Lambda, DynamoDB, Cognito, Budget, throttling | Keep deploy evidence current after each release |
| Identity | Partially implemented | Cognito Hosted UI, JWKS verification, evaluation personas | Federate customer Okta/Entra and disable persona issuer |
| Policy | Implemented | OPA/Rego policies and tests, Python fallback | Add customer-specific Rego bundle workflow |
| Redaction | Implemented | Secret/PII detection tests and response badges | Add customer-specific detectors |
| Bedrock route | Implemented | Env-gated Nova Lite path with kill switch | Validate model access in customer AWS account |
| Customer data boundary | Implemented | Strict mode blocks external model and fixture context | Add UI toggle only for admins after auth hardening |
| Audit store | Implemented | SQLite local, DynamoDB hosted, TTL/retention/export | Add S3/SIEM export for long-term archive |
| Request replay | Implemented | Governance replay UI and API | Add immutable archive option |
| Cost governance | Implemented | Cost Explorer path, cache, quotas, API throttles | Validate payer/member account access |
| Incident context | Partially implemented | Local fixture and CloudWatch adapter | Connect a real customer log group for main pilot |
| Ticketing | Partially implemented | Jira/ServiceNow adapters and contract tests | Run sandbox live integration tests with customer credentials |
| Access workflow | Partially implemented | Local approval workflow | Add Okta/IAM Identity Center adapter implementation |
| Observability | Partially implemented | Structured logs, trace IDs, Jaeger path | Export sample OTel trace from hosted environment |
| CI/CD | Implemented | CI, Playwright, Terraform validate, manual AWS deploy | Add container scan if publishing images |
| Security scanning | Partially implemented | npm audit and high-confidence secret scan | Add CodeQL and container scanning gates |
| Billing | Missing | Pilot pricing docs only | Use paid pilot contract before building in-app billing |
| Support | Partially implemented | Error IDs, troubleshooting, runbooks | Add support SLAs and escalation process for paid pilots |
| Scale testing | Partially implemented | Local load smoke | Run k6/Locust against staging before larger rollout |
