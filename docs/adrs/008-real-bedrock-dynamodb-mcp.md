# ADR-008: Add Real Bedrock, DynamoDB, MCP, and Quota Paths

## Status

Accepted

## Context

The first hosted version proved the control-plane architecture but needed stronger managed-service evidence. To be credible for cloud AI operations, the project needs at least one real managed AI provider path, durable hosted state, real MCP protocol evidence, and cost-abuse controls.

## Decision

Route approved low-sensitivity requests to Amazon Bedrock Nova Lite, persist hosted audit and cache state in DynamoDB, expose the tool set through a real Python MCP server, and enforce per-role/team quota policy before model or tool execution. Keep local control fallback paths for local development, tests, and Bedrock failures.

## Consequences

- Technical reviewers can see real AWS AI, data, policy, and deployment boundaries working together.
- Costs remain bounded because sensitive or denied requests do not call Bedrock and quota checks happen before execution.
- Local development does not require paid model access.
- The MCP server proves interoperability, while Lambda keeps an in-process adapter to avoid subprocess overhead.
