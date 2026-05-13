# ADR-001: Build A CloudOps Control Plane Instead Of A Generic Chatbot

## Status

Accepted

## Context

A generic AI chatbot is easy to understand but weak as an enterprise CloudOps product. It does not prove much about production architecture, cloud operations, security controls, cost governance, or operational maturity.

The target roles value the ability to build systems that are useful, secure, observable, cost-aware, and deployable.

## Decision

Frame and build AegisDesk as a CloudOps AI control plane. The primary workflows are incident triage, access request governance, ticket automation, cost investigation, and AI governance.

## Consequences

- The product has a clearer enterprise value proposition.
- Business reviewers can understand the employee support workflow quickly.
- Technical reviewers can evaluate policy, routing, auditability, and deployment thinking.
- Scope must be controlled so the product does not become a shallow list of tools.
