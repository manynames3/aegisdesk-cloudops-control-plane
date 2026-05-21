# Operational Runbooks

These runbooks are written for a self-hosted AegisDesk operator. They focus on keeping the control plane safe, explainable, and low cost during a customer pilot.

| Runbook | Use when |
| --- | --- |
| [API Down](api-down.md) | The web app says the API is offline or `/health` fails |
| [Bedrock Disabled](bedrock-disabled.md) | Cloud model routing is off or Bedrock calls are failing |
| [OPA Unavailable](opa-unavailable.md) | Policy checks return 503 or OPA health fails |
| [DynamoDB Throttling](dynamodb-throttling.md) | Audit, approval, or quota writes are slow or failing |
| [Cost Explorer Denied](cost-explorer-denied.md) | Cost summaries fail because IAM or Cost Explorer access is denied |
| [Ticket Adapter Failure](ticket-adapter-failure.md) | Jira or ServiceNow ticket creation is blocked |

All runbooks assume destructive cloud changes remain outside chat workflows and that AegisDesk is a governed control plane, not a direct production-change executor.
