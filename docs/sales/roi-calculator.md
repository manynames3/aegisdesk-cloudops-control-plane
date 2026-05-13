# Sample ROI Calculator

Use this worksheet with customer-specific numbers.

| Field | Value |
| --- | ---: |
| Requests per month |  |
| Minutes saved per request |  |
| Loaded hourly cost |  |
| Monthly cloud and AI spend under governance |  |
| Expected spend reduction percentage |  |
| Monthly AegisDesk operating cost |  |

## Formula

```text
time_savings =
  requests_per_month * minutes_saved_per_request / 60 * loaded_hourly_cost

spend_savings =
  monthly_cloud_ai_spend * spend_reduction_percentage

net_monthly_value =
  time_savings + spend_savings - monthly_operating_cost
```

## Example

| Field | Value |
| --- | ---: |
| Requests per month | 80 |
| Minutes saved per request | 15 |
| Loaded hourly cost | $90 |
| Monthly cloud and AI spend under governance | $25,000 |
| Expected spend reduction percentage | 2% |
| Monthly AegisDesk operating cost | $20 |

```text
time_savings = 80 * 15 / 60 * 90 = $1,800
spend_savings = 25,000 * 0.02 = $500
net_monthly_value = 1,800 + 500 - 20 = $2,280
```
