# ADR-010: Use Seeded CloudWatch-Style Incident Context Before Real Log Queries

## Status

Accepted

## Context

Incident triage is more credible when AI answers are grounded in operational evidence instead of generic troubleshooting text. A direct CloudWatch Logs Insights integration would demonstrate more AWS depth, but it can create recurring cost, needs real workload logs, and requires tighter query controls than this portfolio environment needs today.

## Decision

Use a read-only seeded CloudWatch Logs-style incident source for the hosted portfolio path. The gateway returns the log group, query text, matching entries, and suspected cause, exposes the lookup through the same governed tool-call surface, and writes `incident.context.loaded` into the audit trail.

## Consequences

- Recruiters can see an incident workflow that feels practical without needing a live production workload.
- Hiring managers can inspect the intended CloudWatch shape: log group, query, timestamps, entries, and audit event linkage.
- The project stays low-cost and avoids running unbounded log queries during public review.
- A production version should replace the seeded source with CloudWatch Logs Insights under strict role checks, time windows, query limits, and cost controls.
