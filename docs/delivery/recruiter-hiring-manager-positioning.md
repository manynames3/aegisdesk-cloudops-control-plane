# Recruiter and Hiring Manager Positioning

## Short Pitch

AegisDesk is a policy-aware AI gateway for cloud operations. It lets employees use AI for incidents, access requests, tickets, and cost investigation while enforcing privacy, role-based permissions, approval workflows, model routing, and audit logs.

## Recruiter Version

I built a secure internal AI support platform for cloud operations teams. Employees can ask for help, create tickets, and request access, but the company can control sensitive data, approvals, model cost, and audit logs through an admin dashboard.

## Senior Hiring Manager Version

I built a local-first and AWS-hosted CloudOps AI control plane that separates natural language interaction from authorization and execution. The gateway derives identity from JWKS-verified token claims, inspects requests, redacts sensitive data, evaluates OPA/Rego policies, routes approved low-sensitivity prompts to Amazon Bedrock Nova Lite, gates MCP tools, persists audit state in DynamoDB, emits audit events and traces, and exposes operational state in an admin dashboard.

## Resume Bullets

- Built a CloudOps AI gateway with OPA/Rego policy enforcement, JWKS-verified auth, MCP server tooling, PII/secret redaction, Bedrock/local model routing, approval workflows, quotas, and audit logging.
- Implemented enterprise AI governance controls including pre-model redaction, role-based tool authorization, cost-aware Bedrock routing, DynamoDB audit persistence, and admin-visible policy decision traces.
- Packaged a reproducible cloud-native demo with Docker Compose, API/policy tests, OpenTelemetry instrumentation, manual GitHub Actions deployment, and a low-cost AWS deployment using S3, CloudFront, Lambda, HTTP API Gateway, DynamoDB, Bedrock, IAM, CloudWatch, and AWS Budget.

## Interview Talking Points

- The project is intentionally more than a chatbot.
- Policy is enforced outside the model.
- Sensitive data routing happens before model calls.
- Bedrock is real but only used behind policy and quota controls.
- Destructive actions are mocked in the portfolio demo by design.
- Docker Compose proves the local workflow; Terraform deploys a low-cost AWS portfolio environment without always-on compute.
- The admin dashboard exists because enterprise AI needs evidence, not just answers.

## Honest Limitation Statement

This is a portfolio MVP, not a production SaaS. It demonstrates the architecture and control pattern using local services, a low-cost AWS hosted demo, a real Bedrock route, DynamoDB persistence, JWKS verification, and mocked destructive cloud tools. In production, I would add enterprise SSO, managed secrets, immutable audit storage, tenant isolation, signed artifacts, and scoped cloud IAM roles for real tools.
