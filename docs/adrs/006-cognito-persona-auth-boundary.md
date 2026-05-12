# ADR-006: Use Cognito-Backed Persona Tokens For Hosted Identity

## Status

Accepted

## Context

The app needs to demonstrate that role-based decisions are enforced by the backend, not by frontend state. A shared-secret token verifier is too weak for the hosted version, and a full corporate SSO setup would add login ceremony that distracts from the recruiter walkthrough.

## Decision

Keep the local HMAC issuer for fast tests, but run the hosted portfolio environment with Amazon Cognito ID tokens verified through Cognito JWKS. The `/auth/persona-token` endpoint creates controlled reviewer personas through Cognito Admin APIs and maps Cognito groups to `employee`, `manager`, and `admin` roles. The API derives `user_id`, `role`, and `team` from verified token claims and ignores role fields sent in request bodies.

## Consequences

- Role spoofing through the frontend or request body is blocked.
- The hosted deployment now proves managed identity, group-derived roles, and JWKS verification.
- Reviewer personas keep the walkthrough low-friction while still using real Cognito tokens.
- A production deployment should federate Entra ID, Okta, or another corporate IdP instead of using reviewer personas.
