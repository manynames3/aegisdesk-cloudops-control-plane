# Checkout Timeout Triage Runbook

| Field | Value |
| --- | --- |
| Document ID | KB-CLOUDOPS-001 |
| Owner | CloudOps Platform Team |
| Service | checkout-api |
| Review cadence | Quarterly |
| Last reviewed | 2026-05-01 |
| Classification | Internal |

## Purpose

This runbook defines the first-response workflow for checkout latency, timeout, and partial failure incidents. It is written for CloudOps engineers who need to separate application regressions, database saturation, upstream provider latency, and infrastructure capacity issues before escalating.

## When To Use

Use this runbook when alerts, tickets, or customer reports mention:

- checkout timeout
- high p95 or p99 latency on `POST /checkout`
- database connection pool exhaustion
- inventory reservation failures
- payment authorization latency
- a checkout deployment completed shortly before an alert

## Initial Triage Sequence

1. Confirm the alert scope and user impact.
2. Compare the alert start time with the last checkout deployment.
3. Check database connection pool saturation and connection wait time.
4. Check upstream payment authorization latency and error rate.
5. Review inventory reservation errors.
6. Compare current latency with the last known healthy baseline.
7. Open or update the incident ticket with evidence, suspected owner, and next action.

## Evidence To Collect

Collect these fields before recommending a rollback, scaling action, or provider escalation:

- incident ID
- service name
- deploy version and deploy timestamp
- p95 latency and p99 latency
- database pool utilization and wait time
- upstream payment latency
- inventory reservation failure count
- customer impact estimate
- current mitigations already attempted

## Decision Guidance

If database connection pool saturation appears in logs, treat it as the first suspected cause. Check whether a recent deploy changed transaction scope, query fanout, retry behavior, or connection pool size.

If upstream payment latency increased at the same time, open a provider check but do not blame the provider until database pool health is ruled out.

If a deployment completed within 30 minutes before the alert, compare current behavior against the previous release and prepare rollback evidence for the incident commander.

## Safe Actions

Employees may:

- summarize incident evidence
- create or update a support ticket
- request temporary read-only production access
- ask for runbook guidance

Employees must not:

- grant themselves production admin access
- change database capacity
- rotate credentials
- disable checkout controls
- run destructive SQL

## Escalation

Escalate to the checkout service owner when:

- p95 latency stays above threshold for 15 minutes
- database pool exhaustion repeats after mitigation
- payment latency is confirmed by provider status or synthetic checks
- customer impact exceeds the incident manager threshold

Escalate to a manager for temporary read-only access if evidence collection requires production inspection.
