# Recruiter and Hiring Manager Positioning

## Short Pitch

AegisDesk is a policy-aware AI gateway for cloud operations. It lets employees use AI for incidents, access requests, tickets, and cost investigation while enforcing privacy, role-based permissions, approval workflows, model routing, and audit logs.

## Recruiter Version

I built a secure internal AI support platform for cloud operations teams. Employees can ask for help, create tickets, and request access, but the company can control sensitive data, approvals, model cost, and audit logs through an admin dashboard.

## Senior Hiring Manager Version

I built a local-first CloudOps AI control plane that separates natural language interaction from authorization and execution. The gateway inspects requests, redacts sensitive data, evaluates OPA/Rego policies, routes between local and optional cloud models, gates MCP-style tool calls, emits audit events, and exposes the operational state in an admin dashboard.

## Resume Bullets

- Built a local-first CloudOps AI gateway with OPA/Rego policy enforcement, MCP-style tool adapters, PII/secret redaction, model routing, approval workflows, and audit logging.
- Implemented enterprise AI governance controls including pre-model redaction, role-based tool authorization, cost-aware local/cloud routing, and admin-visible policy decision traces.
- Packaged a reproducible cloud-native demo with Docker Compose, API/policy tests, OpenTelemetry tracing plan, and Kubernetes/Terraform production deployment artifacts.

## Interview Talking Points

- The project is intentionally more than a chatbot.
- Policy is enforced outside the model.
- Sensitive data routing happens before model calls.
- Destructive actions are mocked in the portfolio demo by design.
- Docker Compose proves the local workflow; Helm/Terraform show the production path.
- The admin dashboard exists because enterprise AI needs evidence, not just answers.

## Honest Limitation Statement

This is a portfolio MVP, not a production SaaS. It demonstrates the architecture and control pattern using local services and mocked cloud tools. In production, I would add enterprise SSO, managed secrets, immutable audit storage, rate limiting, tenant isolation, signed images, and scoped cloud IAM roles.

