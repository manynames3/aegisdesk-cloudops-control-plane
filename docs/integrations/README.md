# Integrations

AegisDesk uses adapter interfaces so customer systems can be connected without rewriting identity, policy, redaction, model routing, audit, or request replay logic.

## Integration Matrix

| Integration | Purpose | Current shape |
| --- | --- | --- |
| AWS Bedrock | Approved external model route | Implemented behind env flag |
| AWS Cost Explorer | Cloud cost summaries and spend governance | Implemented with DynamoDB cache |
| CloudWatch Logs | Incident context and operational evidence | Adapter interface plus local fixture provider |
| Datadog | Incident context for customers using Datadog logs | Adapter interface |
| Jira | Ticket creation and support workflow | Adapter interface |
| ServiceNow | ITSM ticket creation and approval workflow | Adapter interface |
| Amazon Cognito | Hosted UI, OIDC-compatible sign-in, JWKS verification | Implemented |
| Okta | SSO and group-based access workflow | OIDC-compatible auth path plus access adapter interface |
| Microsoft Entra ID | SSO and enterprise identity | OIDC-compatible auth path |
| Slack | Employee entry point for CloudOps AI | Integration target |
| Microsoft Teams | Employee entry point for CloudOps AI | Integration target |
| MCP server | Agent client interoperability | Implemented with Python MCP SDK |

## Adapter Interfaces

### TicketAdapter

```text
TicketAdapter
  LocalTicketAdapter
  JiraTicketAdapter
  ServiceNowTicketAdapter
```

Use for ticket creation, ticket lookup, escalation, and support queue routing. Tool calls remain policy-gated before the adapter runs.

### IncidentContextAdapter

```text
IncidentContextAdapter
  LocalFixtureIncidentAdapter
  CloudWatchIncidentAdapter
  DatadogIncidentAdapter
```

Use for read-only log or incident evidence retrieval. The adapter returns structured context that can be cited in the answer and stored in request replay.

### AccessRequestAdapter

```text
AccessRequestAdapter
  LocalApprovalAdapter
  OktaGroupRequestAdapter
  IAMIdentityCenterAdapter
```

Use for temporary production access workflows. The control plane should never grant broad access directly from a chat request. It should route scoped access through an approval system.

## MCP Server

The MCP server lives in `services/mcp-tools` and exposes governed CloudOps tools to agent clients. See [Codex MCP Integration](codex-mcp.md).

## Integration Rules

- Authenticate the user before tool execution.
- Evaluate OPA policy before adapter execution.
- Redact secrets before model routing.
- Write an audit event for every adapter call.
- Return enough source metadata for request replay.
- Keep destructive actions behind explicit approval and customer change-management controls.
