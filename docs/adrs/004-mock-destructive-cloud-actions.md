# ADR-004: Mock Destructive Cloud Actions In The Portfolio Environment

## Status

Accepted

## Context

The project needs to demonstrate enterprise cloud workflows without creating real risk or cost. Granting real production access or modifying real infrastructure is unnecessary for a portfolio environment.

## Decision

Mock destructive cloud actions in the MVP. Access grants, privileged changes, and risky operational actions are represented as denied requests, approval records, or simulated tool results.

## Consequences

- The app remains safe to run and review.
- The project can focus on authorization, approval, and audit patterns.
- Documentation must clearly distinguish simulated actions from production implementation.
- Production versions would require scoped IAM roles, short-lived credentials, approval gates, and immutable audit storage.
