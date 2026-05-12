# Architecture Decision Records

This directory records the major architecture decisions for AegisDesk.

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR-001](001-cloudops-control-plane.md) | Accepted | Build a CloudOps control plane instead of a generic chatbot |
| [ADR-002](002-local-first-mvp.md) | Accepted | Use a local-first MVP runtime |
| [ADR-003](003-policy-outside-the-model.md) | Accepted | Enforce policy outside the model with OPA/Rego |
| [ADR-004](004-mock-destructive-cloud-actions.md) | Accepted | Mock destructive cloud actions in the portfolio environment |
| [ADR-005](005-audit-event-model-first.md) | Accepted | Design around audit events from the start |
| [ADR-006](006-cognito-persona-auth-boundary.md) | Accepted | Use Cognito-backed persona tokens for hosted identity |
| [ADR-007](007-low-cost-aws-deployment.md) | Accepted | Deploy a low-cost AWS portfolio environment after approval |
| [ADR-008](008-real-bedrock-dynamodb-mcp.md) | Accepted | Add real Bedrock, DynamoDB, MCP, and quota paths |
| [ADR-009](009-cognito-opa-cost-explorer.md) | Accepted | Pair Cognito identity, live OPA/Rego, and Cost Explorer governance |
| [ADR-010](010-seeded-incident-context.md) | Accepted | Use seeded CloudWatch-style incident context before real log queries |
