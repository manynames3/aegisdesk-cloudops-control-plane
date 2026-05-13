# ADR-010: Use Seeded CloudWatch-Style Incident Context Before Real Log Queries

## Status

Accepted

## Context

Incident triage is more credible when AI answers are grounded in operational evidence instead of generic troubleshooting text. A direct CloudWatch Logs Insights integration can create recurring cost, needs real workload logs, and requires tight query controls.

## Decision

Use a read-only local fixture incident source for the hosted path and define CloudWatch/Datadog adapter boundaries for customer environments. The gateway returns the log group, query text, matching entries, and suspected cause, exposes the lookup through the same governed tool-call surface, and writes `incident.context.loaded` into the audit trail.

## Consequences

- Reviewers can see an incident workflow that feels practical without needing a live production workload.
- Technical reviewers can inspect the intended CloudWatch shape: log group, query, timestamps, entries, and audit event linkage.
- The project stays low-cost and avoids running unbounded log queries during public review.
- Customer production versions should replace the local fixture provider with CloudWatch Logs Insights or Datadog under strict role checks, time windows, query limits, and cost controls.
