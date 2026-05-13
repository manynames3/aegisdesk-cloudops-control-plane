# ROI Model

This ROI model is intentionally simple so a buyer can change the assumptions for their own environment.

## Value Drivers

1. Faster incident triage
2. Fewer unsafe production access paths
3. Reduced repeated support questions
4. Better cloud and AI spend governance
5. Lower security review burden for internal AI usage

## Inputs

| Input | Example |
| --- | ---: |
| CloudOps engineers using the system | 20 |
| Average incidents or support requests per month | 80 |
| Minutes saved per request | 15 |
| Loaded hourly cost per engineer | $90 |
| Monthly cloud/AI spend under review | $25,000 |
| Conservative spend reduction from routing/cache/approval | 2% |
| Expected AegisDesk monthly infrastructure cost | $1-$50 depending on usage |

## Formula

```text
monthly_time_savings =
  requests_per_month * minutes_saved_per_request / 60 * loaded_hourly_cost

monthly_spend_savings =
  cloud_ai_spend_under_review * expected_reduction_percent

monthly_roi =
  monthly_time_savings + monthly_spend_savings - monthly_aegisdesk_cost
```

## Example

```text
time savings = 80 * 15 / 60 * $90 = $1,800
spend savings = $25,000 * 2% = $500
monthly platform cost = $20
estimated monthly ROI = $2,280
```

## What to Validate in a Pilot

- Number of requests handled by role and team
- Percent of requests that required clarification
- Percent of requests blocked or routed to approval
- Time saved per incident or support request
- External model usage and estimated cost
- Cache hit rate for repeated cost and knowledge requests
- Number of audit reviews completed from request replay
