# Incident Investigation And Governed Response

This increment adds a persistent incident workspace. It is locally tested; it has not been deployed or verified against a live customer CloudWatch log group or Jira project. Existing hosted screenshots and deploy evidence describe the earlier chat application.

## Operator Workflow

1. Sign in and open **Incidents**. Cases are scoped to the signed-in team, including for administrators.
2. Create a case with title, description, severity, AWS service/resource, environment, and optional log search reference. The creating identity becomes the owner.
3. Open **Evidence** and refresh CloudWatch logs. No incident fixture data is substituted. An empty result means the query completed with no matching events; unavailable means evidence could not be collected.
4. Review case-linked runbook excerpts. Record operator notes, unverified hypotheses, and recommended next steps under **Investigation**. No hypothesis is a verified root cause. Automatic case AI analysis is not implemented; existing Bedrock chat remains a separate capability.
5. Under **Actions**, propose a Jira ticket and inspect its exact target and arguments. Request approval. A different manager/admin identity in the same team must approve it.
6. Execute the approved action as its requester or a team manager/admin. The API rechecks tool policy, fingerprint, version, target configuration, and expiration before dispatch.
7. A confirmed Jira create response records the ticket key and link. Review **Ticket** and **Timeline**. Ticket creation does not verify cloud mitigation or resolution; the operator must verify recovery outside this application before marking the incident resolved.

## Configuration

Use the existing secret delivery mechanism to set these server-side variables. Never put integration credentials in browser variables or commit them.

```text
AEGISDESK_INCIDENT_CONTEXT_ADAPTER=cloudwatch
AEGISDESK_CLOUDWATCH_LOG_GROUP=/aws/lambda/your-service
AEGISDESK_CLOUDWATCH_LOGS_REGION=us-east-1
AEGISDESK_TICKET_ADAPTER=jira
AEGISDESK_JIRA_BASE_URL=https://your-company.atlassian.net
AEGISDESK_JIRA_PROJECT_KEY=OPS
AEGISDESK_JIRA_EMAIL=<integration-account>
AEGISDESK_JIRA_API_TOKEN=<secret>
```

Restart the API after changing adapter settings. Direct local execution reads these environment variables; Compose currently supplies its own environment defaults, so override its service configuration explicitly. The AWS Terraform deployment does not yet expose all these integration settings; do not assume that local configuration also configures Lambda.

The API role needs CloudWatch Logs Insights query permissions for the configured log group, and the Jira account needs issue creation plus issue read permissions for reconciliation. The log group is operator-configured, not selected by a browser-supplied URL. Queries use the existing bounded lookback, polling, and result limits. Logs are not restricted to a case resource ARN automatically: choose a suitably scoped log group and explicit search reference. Per-team AWS credentials/log-group mapping is not implemented.

For a customer deployment, retain Cognito/JWKS, disable evaluation personas, configure OPA explicitly, and use `AEGISDESK_DATA_BOUNDARY_MODE=customer_strict`. Strict mode blocks external model routing and local ticket fixtures. Incident cases do not accept fixtures in any mode. No new cloud resources are provisioned by this increment.

## Failure And Recovery

| Condition | Behavior | Operator response |
| --- | --- | --- |
| CloudWatch unavailable | `unavailable`, or `stale` with previously collected evidence and its original timestamp | Check IAM/log group; refresh evidence |
| Completed query with no logs | `empty`, with collection metadata | Check time window/search reference; do not infer a healthy service |
| Policy unavailable | Mutation returns 503; no ticket dispatch | Restore OPA/configured policy engine; retry after refresh |
| Another operator changed the case | Version conflict returns 409 | Refresh and review the updated case before retrying |
| Approval expired | Execution blocked | Cancel the undispatched action and propose a new action |
| Jira rejects the request | Failed action; case returns to investigation | Correct permissions/configuration; propose a new action after review |
| Jira times out, returns malformed success, or dispatch is interrupted | `outcome_uncertain` or persisted `executing`; no automatic redispatch | Find the issue in Jira using the incident/action reference in its summary, then reconcile |
| Reconciliation does not match | Action remains unresolved | Check project, exact summary, and ticket key; do not create a replacement blindly |
| Outcome saved after a competing case update | Dispatch may be complete, but response can be 409 and stored action remains `executing` | Refresh and reconcile the external issue |
| Case exceeds storage bound | 413 before further persistence | Escalate storage capacity; no automatic truncation or evidence deletion |

**Reconcile outcome** performs a Jira issue read and checks the ticket key, project, and exact proposed summary. It does not simply trust an operator-entered ticket key. A missing issue is not proof that the original creation never occurred. Unresolved actions block incident resolution. Approved but undispatched actions can be cancelled; dispatched actions cannot.

## Persistence And Audit

- SQLite stores cases in an additive `incident_cases` table. Existing installations migrate on startup.
- DynamoDB uses `pk=INCIDENT#<team>`, `sk=<incident_id>` in the existing table. Lists paginate DynamoDB query responses and use consistent reads.
- Conditional version writes serialize case updates and ticket dispatch claims. The complete case snapshot and activity timeline are saved together; this is not a distributed transaction with Jira.
- Case payloads are bounded to 280,000 bytes before storage. An external outcome that cannot be persisted leaves a reconcilable dispatch claim.
- Every mutation records identity, time, event, details, trace ID when available, and a separate server-generated request correlation ID. Responses expose `X-AegisDesk-Correlation-ID`; this identifier does not prove trace export.
- Case input, notes, and log messages use existing pattern-based redaction. This does not detect every possible secret or sensitive identifier.
- Legacy governance events/replay/JSON exports are redacted on read. Managers see their team's records; the existing admin role retains global legacy audit access. Incident timelines remain team scoped and separate from legacy chat replay/export.
- Case snapshots have no automatic TTL, immutable archive, or backup/recovery mechanism added here. Define case retention and backups before customer use. Evaluation reset deletes local cases; seed/reset endpoints are disabled when evaluation personas are disabled. Do not use reset as a customer teardown procedure.

## API Surface

All case routes require the existing bearer identity. Mutations evaluate existing policy; ticket operations additionally enforce the case approval gate in server code.

| Route | Purpose |
| --- | --- |
| `GET /incidents` | List team cases |
| `POST /incidents` | Create case |
| `GET /incidents/{id}` | Inspect team case |
| `PATCH /incidents/{id}` | Validated lifecycle transition |
| `POST /incidents/{id}/notes` | Redacted operator finding |
| `POST /incidents/{id}/evidence` | Refresh CloudWatch evidence |
| `POST /incidents/{id}/actions` | Propose exact Jira ticket |
| `POST /incidents/{id}/actions/{action}/request-approval` | Request human review |
| `POST /incidents/{id}/actions/{action}/approve` | Independent team approval |
| `POST /incidents/{id}/actions/{action}/cancel` | Cancel undispatched action |
| `POST /incidents/{id}/actions/{action}/execute` | Revalidated dispatch |
| `POST /incidents/{id}/actions/{action}/reconcile` | Verify ambiguous Jira outcome |

Mutations of an existing case require the currently displayed `version`. No endpoint accepts arbitrary operational commands or editable approved arguments. Chat cannot dispatch Jira ticket creation around this gate. Existing ServiceNow chat and local access approval records are preserved, but do not have the new incident action lifecycle. Access approval does not provision external access.

The standalone MCP server remains local fixture tooling and does not dispatch this authenticated incident lifecycle. Runbook excerpts come from the packaged knowledge corpus; review and replace these examples for the customer's actual services before operational use.

## Verification And Remaining Scope

Run `npm run test:api`, `npm run test:e2e`, `npm run build:web`, `npm run evals`, and `npm run security:scan`. API tests inject controlled CloudWatch/Jira adapters. Playwright launches a loopback Jira HTTP fixture from `apps/web/tests/fixtures/jira.py`; it is not an operational integration and is never imported by the production API. E2E uses in-memory API storage; SQLite persistence and version races have separate API tests. DynamoDB conditional-write/pagination tests use a table double, not live AWS.

Playwright captures the real running UI at desktop/tablet sizes:

- [Incident queue, controlled test](../evidence/screenshots/incident-queue-controlled-desktop.png)
- [Approved Jira action, controlled test](../evidence/screenshots/incident-actions-controlled-desktop.png)
- [Incident timeline, controlled test](../evidence/screenshots/incident-timeline-controlled-tablet.png)

Still needed for the full product mission: live customer integration verification, integration connection-test endpoints and permission diagnostics, CloudWatch metrics/trace correlation, editable ownership, case AI hypotheses with evidence citations, ticket updates, unified case/chat audit export, scalable queue pagination, configurable case retention/backups, revocation/recovery exercises, managed telemetry/alarms, and production rollout testing. This implementation creates tickets only; it performs no AWS mitigation actions.
