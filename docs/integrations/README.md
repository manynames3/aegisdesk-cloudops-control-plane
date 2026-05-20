# Integrations

AegisDesk uses adapter interfaces so customer systems can be connected without rewriting identity, policy, redaction, model routing, audit, or request replay logic.

## Integration Matrix

| Integration | Purpose | Current shape |
| --- | --- | --- |
| AWS Bedrock | Approved external model route | Implemented behind env flag |
| AWS Cost Explorer | Cloud cost summaries and spend governance | Implemented with DynamoDB cache |
| CloudWatch Logs | Incident context and operational evidence | Implemented behind env flag plus local fixture provider |
| Datadog | Incident context for customers using Datadog logs | Adapter interface |
| Jira | Ticket creation and support workflow | Implemented behind env flag |
| ServiceNow | ITSM ticket creation and support workflow | Implemented behind env flag |
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

Jira can be enabled without changing application code:

```bash
AEGISDESK_TICKET_ADAPTER=jira
AEGISDESK_JIRA_BASE_URL=https://your-domain.atlassian.net
AEGISDESK_JIRA_EMAIL=cloudops-bot@example.com
AEGISDESK_JIRA_API_TOKEN=replace-with-secret
AEGISDESK_JIRA_PROJECT_KEY=OPS
AEGISDESK_JIRA_ISSUE_TYPE=Task
```

If Jira is selected but missing configuration, or if Jira is unavailable at runtime, AegisDesk does not fall back to a local fake ticket. It returns a blocked tool result, explains that ticket creation did not complete, and records the failure in the audit trail.

ServiceNow can be enabled through the same `TicketAdapter` boundary:

```bash
AEGISDESK_TICKET_ADAPTER=servicenow
AEGISDESK_SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
AEGISDESK_SERVICENOW_USERNAME=aegisdesk.integration
AEGISDESK_SERVICENOW_PASSWORD=replace-with-secret
AEGISDESK_SERVICENOW_ASSIGNMENT_GROUP=
AEGISDESK_SERVICENOW_TABLE=incident
```

The ServiceNow adapter creates a record through the Table API, maps severity to impact/urgency, returns the ticket number, sys_id, status, source system, and record URL, and records blocked failures in the audit trail.

### IncidentContextAdapter

```text
IncidentContextAdapter
  LocalFixtureIncidentAdapter
  CloudWatchIncidentAdapter
  DatadogIncidentAdapter
```

Use for read-only log or incident evidence retrieval. The adapter returns structured context that can be cited in the answer and stored in request replay.

CloudWatch Logs can be enabled without changing application code:

```bash
AEGISDESK_INCIDENT_CONTEXT_ADAPTER=cloudwatch
AEGISDESK_CLOUDWATCH_LOG_GROUP=/aws/lambda/your-service
AEGISDESK_CLOUDWATCH_LOGS_REGION=us-east-1
AEGISDESK_CLOUDWATCH_QUERY_LOOKBACK_MINUTES=60
AEGISDESK_CLOUDWATCH_QUERY_LIMIT=20
```

The CloudWatch adapter uses Logs Insights with bounded lookback, bounded result count, and read-only IAM. If CloudWatch is selected without a log group or the query cannot complete, AegisDesk does not substitute fixture logs. It returns an unavailable incident context, blocks the tool result, and records that outcome in the audit trail.

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
