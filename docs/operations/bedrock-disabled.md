# Runbook: Bedrock Disabled Or Unavailable

## Symptoms

- Responses show `local` route or `bedrock-disabled-local-control-fallback`
- Governance trail shows `model.fallback`
- Setup checklist shows Bedrock disabled, kill switch on, or customer strict boundary mode

## First Checks

```bash
aws bedrock list-foundation-models --region "$AWS_REGION"
aws logs filter-log-events --log-group-name /aws/lambda/aegisdesk-portfolio-api --filter-pattern bedrock
```

## Likely Causes

- `AEGISDESK_ENABLE_BEDROCK=false`
- `AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true`
- `AEGISDESK_DATA_BOUNDARY_MODE=customer_strict`
- Bedrock model access has not been enabled in the AWS account
- Lambda role lacks `bedrock:InvokeModel` or `bedrock:Converse`

## Recovery

1. Decide whether external models are allowed for this customer environment.
2. If strict boundary mode is active, keep Bedrock disabled.
3. If Bedrock should be enabled, grant model access in AWS and verify IAM.
4. Set `AEGISDESK_ENABLE_BEDROCK=true` and keep quotas/throttles in place.
5. Run one low-sensitivity support prompt and inspect request replay for route, cost, and redaction evidence.

## Safe Fallback

AegisDesk should continue returning local-control guidance. It should not fabricate a Bedrock answer when Bedrock is disabled or unavailable.
