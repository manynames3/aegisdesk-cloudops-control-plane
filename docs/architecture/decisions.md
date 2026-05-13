# Architecture Decisions

This file records early decisions and tradeoffs. The goal is to show practical architecture thinking, not to overbuild.

Formal ADRs now live in [../adrs/README.md](../adrs/README.md). This file is retained as the original decision summary.

## ADR-001: Build AegisDesk As A CloudOps Control Plane, Not A Generic Chatbot

Decision:

Build around cloud operations workflows: incident triage, access requests, ticket automation, cost investigation, and governance.

Reason:

Generic chatbots are easy to dismiss. A CloudOps control plane demonstrates higher-value cloud skills: security, cost control, policy, observability, deployment, and enterprise architecture.

Tradeoff:

The project becomes more complex than a basic chat UI. Scope must stay narrow and customer-workflow driven.

## ADR-002: Local-First Runtime

Decision:

The first complete operator path should run locally with Docker Compose and optional Ollama.

Reason:

This keeps initial cost near zero, makes the app reproducible, and highlights cost-conscious engineering.

Tradeoff:

Local runtime does not prove managed cloud operations by itself. Terraform, Helm, and deployment docs show the customer deployment path.

## ADR-003: Use OPA/Rego For Policy

Decision:

Use OPA/Rego for authorization and governance decisions instead of hardcoded if-statements.

Reason:

Policy-as-code is more credible for enterprise AI governance. It also maps directly to job requirements for OPA/Rego and compliance controls.

Tradeoff:

OPA adds complexity. The product should use a small number of readable policies and tests.

## ADR-004: Keep Destructive Cloud Actions Behind Approval

Decision:

Do not grant production access or modify cloud resources directly from a chat request.

Reason:

The goal is to prove safe architecture, not create unnecessary risk or cost.

Tradeoff:

Some actions use local adapters. The documentation must clearly distinguish local adapters from customer production integrations.

## ADR-005: Show Cost Decisions In The Product UI

Decision:

Cost should be visible in the admin dashboard and request metadata.

Reason:

AI cost management is now part of cloud governance. Showing route and cost decisions makes the project stronger for cloud and FinOps-oriented roles.

Tradeoff:

Cost numbers may be estimates. They should be labeled as estimates and calculated consistently.
