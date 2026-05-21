# Runbook: Ticket Adapter Failure

## Symptoms

- Chat says ticket creation did not complete
- Tool call status is `blocked`
- Audit event `tool.blocked` includes `system=jira` or `system=servicenow`

## First Checks

```bash
curl -fsS "$JIRA_BASE_URL/rest/api/3/myself" -u "$JIRA_EMAIL:$JIRA_API_TOKEN"
curl -fsS "$SERVICENOW_INSTANCE_URL/api/now/table/incident?sysparm_limit=1" -u "$SERVICENOW_USERNAME:$SERVICENOW_PASSWORD"
```

## Likely Causes

- Missing adapter environment variables
- Expired Jira API token or ServiceNow password
- Project key, issue type, table, or assignment group mismatch
- Network egress blocked from the runtime
- Customer API rate limit or permission issue

## Recovery

1. Confirm `AEGISDESK_TICKET_ADAPTER` is set to `jira` or `servicenow`.
2. Verify all required credentials and target project/table settings.
3. Run the adapter contract tests locally.
4. Retry a ticket prompt and confirm the returned external ticket URL.
5. If the external API remains unavailable, leave the blocked result in the audit trail and open the issue manually.

## Safety Note

The adapter must fail closed. It should never return a fake external ticket ID when Jira or ServiceNow fails.
