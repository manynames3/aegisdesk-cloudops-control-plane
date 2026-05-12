# Policies

Policy files:

- `model_routing.rego`
- `tool_authorization.rego`
- `approval_rules.rego`
- `chat_policy.rego`
- `quota.rego`
- `policy_test.rego`

Policy examples:

- Employees can create support tickets.
- Employees cannot grant production admin access.
- Temporary read-only production access requires manager approval.
- Requests containing secrets cannot be sent to cloud models.
- Low-sensitivity requests can route to Amazon Bedrock.
- Cost summaries require manager or admin role.
- Per-role daily quotas protect cost and abuse boundaries.

Local validation:

```bash
opa test policies
```
