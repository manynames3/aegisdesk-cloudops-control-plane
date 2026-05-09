# Two-Week MVP Plan

Goal: build a complete, demoable, low-cost portfolio project in two weeks.

## Success Criteria

The project is successful if a reviewer can:

- Run the demo locally.
- Use the chat UI.
- Trigger PII/secret redaction.
- See OPA allow/deny decisions.
- Create or check a mock ticket through an MCP-style tool.
- Trigger an approval workflow.
- View admin dashboard events.
- Read clear architecture, cost, security, and deployment docs.

## Week 1

### Day 1: Repo and Product Definition

- Finalize docs
- Create architecture diagram
- Define use cases
- Define mock data
- Create API contracts

### Day 2: FastAPI Gateway Skeleton

- `/chat` endpoint
- request/response schemas
- audit event model
- basic tests

### Day 3: Policy Engine

- OPA container
- Rego policies
- policy test cases
- gateway policy integration

### Day 4: Redaction and Routing

- secret/PII detection
- local/cloud route decision
- model route metadata
- cost estimate placeholder

### Day 5: MCP Tool Layer

- ticket tool
- access request tool
- cloud cost mock tool
- tool authorization checks

## Week 2

### Day 6: Frontend Chat

- chat interface
- response metadata badges
- redaction and model route indicators

### Day 7: Admin Dashboard

- request log
- policy decisions
- cost summary
- model route summary
- tool call table

### Day 8: Approval Workflow

- approval queue
- approve/deny actions
- audit state transitions

### Day 9: Observability and CI

- OpenTelemetry traces
- Jaeger local setup
- GitHub Actions
- API and policy tests

### Day 10: Demo Polish

- seed demo data
- screenshot script
- demo video outline
- final README polish
- production hardening notes

## Scope Control

Must-have:

- Working local demo
- Policy decisions
- Redaction
- Model route explanation
- Tool call audit
- Admin dashboard

Should-have:

- OpenTelemetry traces
- Prompt injection tests
- Cost summary
- Approval workflow

Could-have:

- Helm chart
- Terraform skeleton
- PDF governance report

Not in MVP:

- Real production cloud writes
- Full enterprise SSO
- Multi-tenant SaaS billing
- Fine-tuning
- Complex multi-agent framework

