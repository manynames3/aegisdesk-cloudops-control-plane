# Policies

Policy files:

- `model_routing.rego`
- `tool_authorization.rego`
- `approval_rules.rego`

Policy examples:

- Employees can create support tickets.
- Employees cannot grant production admin access.
- Temporary read-only production access requires manager approval.
- Requests containing secrets cannot be sent to cloud models.
- Cost summaries require manager or admin role.
