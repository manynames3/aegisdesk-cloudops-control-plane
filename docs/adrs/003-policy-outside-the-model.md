# ADR-003: Enforce Policy Outside The Model With OPA/Rego

## Status

Accepted

## Context

LLMs can explain policy, but they should not be the source of authority for access, routing, approvals, or tool execution. Enterprise AI workflows need explicit controls that can be tested and audited.

## Decision

Use OPA/Rego as the policy engine for model routing, tool authorization, approval requirements, and budget-related decisions.

## Consequences

- Policy decisions are testable and auditable.
- The system can deny unsafe actions even if the model suggests them.
- Rego adds implementation complexity.
- The product should keep policies small, readable, and covered by tests.
