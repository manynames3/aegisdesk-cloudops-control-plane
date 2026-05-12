# ADR-008: Add Real Bedrock, DynamoDB, MCP, and Quota Paths

## Status

Accepted

## Context

The first hosted version proved the control-plane architecture but still relied on deterministic model and tool simulations. To be credible for cloud AI roles, the project needs at least one real managed AI provider path, durable hosted state, real MCP protocol evidence, and cost-abuse controls.

## Decision

Route approved low-sensitivity requests to Amazon Bedrock Nova Lite, persist hosted audit state in DynamoDB, expose the tool set through a real Python MCP server, and enforce per-role/team quota policy before model or tool execution. Keep deterministic fallback paths for local development, tests, and Bedrock failures.

## Consequences

- Hiring managers can see real AWS AI, data, auth, policy, and deployment boundaries working together.
- Costs remain bounded because sensitive or denied requests do not call Bedrock and quota checks happen before execution.
- Local development remains deterministic and does not require paid model access.
- The MCP server proves interoperability, while Lambda keeps an in-process adapter to avoid subprocess overhead.
