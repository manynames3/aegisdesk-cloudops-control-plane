# Load Smoke Evidence

This is a small local smoke test, not a capacity benchmark. It verifies that the API can process repeated governed chat requests through auth, quota, redaction, policy, routing, tool decisions, and audit writes without 5xx errors.

## Run

```bash
npm run smoke:load
```

The script uses FastAPI `TestClient`, local persona tokens, and the repository's configured local store. It does not call Bedrock, Cost Explorer, Jira, ServiceNow, or CloudWatch unless the local environment explicitly enables those paths.

## Example Output

```json
{
  "requests": 20,
  "failures": 0,
  "p50_ms": 5.03,
  "p95_ms": 6.61,
  "max_ms": 11.93,
  "store_metrics": {
    "requests_total": 20,
    "estimated_spend_usd": 0.008,
    "local_model_requests": 20,
    "cloud_model_requests": 0,
    "redactions_total": 0,
    "denied_actions": 0,
    "approvals_pending": 5,
    "tool_calls_total": 5
  }
}
```

## Hiring-Manager Read

The value is not the numbers; it is the existence of a repeatable load/smoke path that exercises the control plane rather than only rendering the frontend.

## Buyer Read

Before broad rollout, replace this with a customer-specific k6 or Locust test against a non-production deployment and include expected concurrent users, traffic mix, and acceptable latency/error thresholds.
