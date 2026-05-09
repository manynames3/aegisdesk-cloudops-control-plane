# Architecture Decisions

This file records early decisions and tradeoffs. The goal is to show practical architecture thinking, not to overbuild.

## ADR-001: Build AegisDesk As A CloudOps Control Plane, Not A Generic Chatbot

Decision:

Build around cloud operations workflows: incident triage, access requests, ticket automation, cost investigation, and governance.

Reason:

Generic chatbots are easy to dismiss. A CloudOps control plane demonstrates higher-value cloud skills: security, cost control, policy, observability, deployment, and enterprise architecture.

Tradeoff:

The project becomes more complex than a basic chat UI. Scope must stay narrow and demo-driven.

## ADR-002: Local-First MVP

Decision:

The first complete demo should run locally with Docker Compose and Ollama.

Reason:

This keeps initial cost near zero, makes the demo reproducible, and highlights cost-conscious engineering.

Tradeoff:

Local runtime does not prove managed cloud operations by itself. Terraform, Helm, and deployment docs will show the production path.

## ADR-003: Use OPA/Rego For Policy

Decision:

Use OPA/Rego for authorization and governance decisions instead of hardcoded if-statements.

Reason:

Policy-as-code is more credible for enterprise AI governance. It also maps directly to job requirements for OPA/Rego and compliance controls.

Tradeoff:

OPA adds complexity. The MVP should use a small number of readable policies and tests.

## ADR-004: Mock Destructive Cloud Actions

Decision:

Do not grant real production access or modify real cloud resources in the portfolio demo.

Reason:

The goal is to prove safe architecture, not create unnecessary risk or cost.

Tradeoff:

Some cloud actions are simulated. The documentation must clearly distinguish mocked demo actions from production implementation.

## ADR-005: Show Cost Decisions In The Product UI

Decision:

Cost should be visible in the admin dashboard and request metadata.

Reason:

AI cost management is now part of cloud governance. Showing route and cost decisions makes the project stronger for cloud and FinOps-oriented roles.

Tradeoff:

MVP cost numbers may be estimates. They should be labeled as estimates and calculated consistently.

