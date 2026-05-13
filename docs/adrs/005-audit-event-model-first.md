# ADR-005: Design Around Audit Events From The Start

## Status

Accepted

## Context

Enterprise AI systems need to explain what happened after the fact: who made a request, what data was detected, which model was used, why a policy allowed or denied an action, which tools ran, what was approved, and what the request cost.

## Decision

Make audit events a first-class system concept before building the dashboard. The admin UI should summarize backend events rather than display invented metrics.

## Consequences

- Governance views can be backed by real system state.
- Debugging and compliance review become easier.
- The API and data model need to capture decision metadata consistently.
- The product must avoid storing sensitive values in audit metadata.
