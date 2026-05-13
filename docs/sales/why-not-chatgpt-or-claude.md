# Why Not Just ChatGPT or Claude?

General AI chat tools are useful for brainstorming, drafting, and one-off questions. AegisDesk exists for governed CloudOps workflows where a company needs control, evidence, and integration with operational systems.

## The Difference

| Question | General chat tool | AegisDesk |
| --- | --- | --- |
| Who is asking? | Usually outside company workflow | Verified identity, role, and team |
| Can this user do this? | Prompt-dependent | OPA/Rego policy decision |
| Were secrets removed? | User responsibility | API redaction before routing |
| Which model is allowed? | User or vendor setting | Policy-based route and kill switch |
| Can tools run? | Depends on chat environment | Backend-governed adapter execution |
| Are approvals required? | Not built in | Manager/admin approval workflow |
| Is there an audit trail? | Limited or vendor-specific | Request replay with trace ID |
| Can it connect to our CloudOps systems? | Generic connectors | Ticket, incident, access, cost, and MCP adapters |
| Can we self-host? | Usually no | Docker Compose and AWS Terraform paths |

## When AegisDesk Is the Better Fit

- Incident triage needs internal runbooks and operational context
- Production access must follow least-privilege approval workflows
- Cloud cost investigation should be role-limited and cached
- Security needs prompt, redaction, route, source, tool, and audit evidence
- Platform teams need a repeatable pattern for internal AI workflows

## When a General Chat Tool Is Enough

- Personal productivity
- Non-sensitive drafting
- Research that does not need internal tools
- Questions that do not require identity, policy, audit, or approval evidence
