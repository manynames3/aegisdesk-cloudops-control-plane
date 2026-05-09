# ADR-006: Use Signed Demo Tokens Before Hosted OIDC

## Status

Accepted

## Context

The app needs to demonstrate that role-based decisions are enforced by the backend, not by frontend state. Full OIDC setup would add external account configuration and deployment work before the portfolio demo needs it.

## Decision

Use a local demo token issuer that returns signed JWT-style bearer tokens. The API derives `user_id`, `role`, and `team` from token claims and ignores role fields sent in request bodies.

## Consequences

- Role spoofing through the frontend or request body is blocked in the MVP.
- Tests can prove backend-derived identity behavior without a hosted identity provider.
- The demo issuer must be clearly documented as local-only.
- A hosted deployment should replace the demo issuer with OIDC/JWKS verification.
