# ADR-012: Persistent Incident Cases And Exact-Action Approval

## Status

Accepted for the local incident workflow increment; not production verified.

## Context

Chat requests did not preserve an incident lifecycle or provide an exact-action approval and dispatch record. A ticket network timeout can mean the ticket was created even though the caller received no confirmation. Automatically retrying that operation can create duplicates.

## Decision

Reuse the existing SQLite/DynamoDB store, bearer identity, OPA/Rego tool decisions, CloudWatch/Jira adapters, and runbook retrieval. Store a versioned team-scoped case snapshot with its timeline. Require independent approval of a fingerprint covering operation, target, arguments, requester, action version, and policy. Revalidate at dispatch and persist a conditional execution claim before external I/O.

Keep uncertain outcomes unresolved; reconcile by reading a matching Jira issue instead of automatically retrying. CloudWatch failures retain timestamped prior evidence. Incident cases never substitute fixtures. Case investigation remains useful without a model call; operator hypotheses are explicitly unverified.

## Consequences

No new production dependency, datastore, cloud service, or arbitrary operational command surface is required. Concurrent version writes prevent duplicate dispatch of the same stored action. This does not provide exactly-once delivery across Jira and the database; crashes and competing updates require reconciliation.

Whole-case snapshots have a storage bound and are suitable for a bounded initial workflow, not unlimited evidence ingestion. Timelines are mutable operational records, not immutable compliance archives. Case retention, backup recovery, queue pagination, and live integration verification remain required before a customer rollout. The extra human gate is enforced in server code alongside existing OPA policy, not by the model.
