# ADR-006: Use JWKS-Verified Demo Tokens Before Production OIDC

## Status

Accepted

## Context

The app needs to demonstrate that role-based decisions are enforced by the backend, not by frontend state. A production identity-provider setup would add account configuration and login UX that is not essential for the portfolio demo, but a shared-secret token verifier is too weak for the hosted version.

## Decision

Keep the local HMAC issuer for fast tests, but run the hosted portfolio environment with RS256 demo tokens and a public JWKS endpoint. The API derives `user_id`, `role`, and `team` from verified token claims and ignores role fields sent in request bodies.

## Consequences

- Role spoofing through the frontend or request body is blocked in the MVP.
- Tests can prove backend-derived identity behavior without a hosted identity provider.
- The hosted demo proves JWKS verification mechanics without requiring recruiter login setup.
- A production deployment should replace the demo issuer with Cognito, Entra ID, Okta, or another OIDC provider.
