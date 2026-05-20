# ADR-011: Add Bounded CloudWatch Evidence and Enforce Audit Retention

## Status

Accepted

## Context

CloudOps incident help is more useful when answers can cite operational evidence from the customer's log source. The product also stores request replay evidence, which creates a real retention obligation. A sellable self-hosted product needs both capabilities to be explicit, bounded, and auditable.

## Decision

Implement a CloudWatch Logs Insights incident adapter behind environment configuration. Keep the local fixture provider for first-run evaluation, but when CloudWatch is selected, query the configured log group with a bounded lookback window, bounded result count, and read-only IAM. If CloudWatch is misconfigured or unavailable, do not fall back to fixture evidence.

Enforce audit retention in both storage paths. The SQLite store prunes expired audit events before evidence reads and exports. DynamoDB audit records include an `expires_at` attribute so deployments can use DynamoDB TTL, and replay/export paths prune expired records before returning evidence.

## Consequences

- Incident answers can be grounded in real customer logs without widening the rest of the control plane.
- Query cost and blast radius are constrained by time window, result limits, and IAM scope.
- Buyers can see how audit data leaves the short-term evidence window.
- DynamoDB TTL is eventually consistent, so strict archive or legal-hold workflows still need a dedicated immutable audit sink.
