# Runbook: API Down

## Symptoms

- Web UI shows `API is offline`
- `GET /health` fails or times out
- GitHub deploy smoke test fails after publishing

## First Checks

```bash
curl -fsS "$API_URL/health"
curl -fsS "$API_URL/health/ready"
aws logs filter-log-events --log-group-name /aws/lambda/aegisdesk-portfolio-api --max-items 20
```

## Likely Causes

- Lambda package was not rebuilt before Terraform apply
- API Gateway integration points to an old Lambda version
- Missing environment variable for auth, store, or policy runtime
- Lambda execution role lost DynamoDB, Bedrock, Logs, or Cost Explorer permissions

## Recovery

1. Check the latest deploy-aws run and confirm the `Smoke test API` step.
2. Review Lambda logs for the `X-AegisDesk-Error-ID` value returned to the UI.
3. Run Terraform plan and inspect Lambda environment variables.
4. If the API fails readiness but liveness works, check DynamoDB and OPA readiness first.
5. Redeploy from GitHub Actions only after the plan is clean.

## Customer Impact

No chat, approval, audit export, or governance replay requests can complete while the API is down. The static frontend may still load from CloudFront.
