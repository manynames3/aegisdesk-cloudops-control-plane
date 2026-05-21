# Troubleshooting

## Error IDs

API errors include an `error_id` and the response header `X-AegisDesk-Error-ID`. Use that ID when searching Lambda logs or sharing support details.

Example response:

```json
{
  "error_id": "err-1234abcd",
  "detail": "policy_engine_unavailable",
  "path": "/chat"
}
```

## Health Checks

| Endpoint | Meaning |
| --- | --- |
| `/health` | API process is reachable |
| `/health/live` | Basic liveness check |
| `/health/ready` | Store and policy are ready |
| `/setup/status` | Non-secret admin checklist data for identity, policy, model, data, and integrations |

## Common Issues

| Symptom | First place to look |
| --- | --- |
| API offline in UI | [API Down runbook](../operations/api-down.md) |
| Local answers only | [Bedrock Disabled runbook](../operations/bedrock-disabled.md) |
| Policy 503 | [OPA Unavailable runbook](../operations/opa-unavailable.md) |
| Audit export slow | [DynamoDB Throttling runbook](../operations/dynamodb-throttling.md) |
| Cost summary unavailable | [Cost Explorer Denied runbook](../operations/cost-explorer-denied.md) |
| Ticket not created | [Ticket Adapter Failure runbook](../operations/ticket-adapter-failure.md) |

## Support Packet To Collect

- Error ID
- Request ID
- Trace ID
- User role and team, not personal secret values
- `/setup/status` output
- Relevant audit export row
- Latest deploy run URL
- Whether customer data boundary mode is enabled
