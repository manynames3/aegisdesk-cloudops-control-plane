# ADR-009: Pair Cognito Identity, Live OPA/Rego, And Cost Explorer Governance

## Status

Accepted

## Context

A CloudOps AI control plane is only credible if identity, policy, model routing, cost visibility, and audit state work together. The earlier hosted version had strong architecture but still left too much of that story at the framework level.

## Decision

Use Amazon Cognito for hosted reviewer personas and backend JWT/JWKS verification. Run OPA/Rego as the live policy engine in Lambda by bundling the OPA binary and policy directory into the deployment artifact. Use AWS Cost Explorer for manager/admin cost investigations and cache summaries in DynamoDB to avoid repeated API calls.

## Consequences

- Hosted requests now prove managed identity, group-derived roles, externalized policy, AWS AI routing, durable audit state, and cost governance in one flow.
- The architecture stays low-idle-cost because it uses serverless/static AWS services instead of always-on control-plane services.
- Cost Explorer responses depend on AWS billing data and tag availability, so zero tagged spend is a valid outcome that must be shown honestly.
- Production hardening should replace reviewer personas with corporate federation and add stronger audit retention controls.
