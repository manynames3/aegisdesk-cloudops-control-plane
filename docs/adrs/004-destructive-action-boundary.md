# ADR-004: Keep Destructive Cloud Actions Behind Approval Boundaries

## Status

Accepted

## Context

The product needs to support enterprise cloud workflows without creating unnecessary risk. Granting production access or modifying infrastructure directly from a chat request would bypass normal change-management controls.

## Decision

Keep destructive cloud actions behind denial, scoped approval, or customer-owned adapter boundaries. Access grants, privileged changes, and risky operational actions are represented as denied requests, approval records, or controlled adapter results unless a customer explicitly wires an approved production workflow.

## Consequences

- The app remains safe to run and review.
- The product can focus on authorization, approval, and audit patterns.
- Documentation must clearly distinguish local adapters from customer production integrations.
- Customer production versions should require scoped IAM roles, short-lived credentials, approval gates, and immutable audit storage.
