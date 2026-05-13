# ADR-002: Use A Local-First Runtime

## Status

Accepted

## Context

The project should be reviewable without requiring ongoing cloud spend. It also needs to show cost-conscious engineering and be reproducible by a reviewer.

## Decision

Make Docker Compose and local model routing the first runnable target. Use Ollama for the local model path. Keep cloud model integration optional and controlled by environment configuration.

## Consequences

- The app can run at low or zero cost.
- The project is easier to reproduce from a clean checkout.
- Cloud deployment artifacts remain available without blocking local installation.
- Local runtime does not replace the need to document cloud deployment, IAM, secrets, and observability hardening.
