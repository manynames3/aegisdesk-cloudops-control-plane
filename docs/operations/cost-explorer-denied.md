# Runbook: Cost Explorer Denied

## Symptoms

- Manager/admin cost prompt returns local fallback or unavailable result
- Lambda logs show `cost_explorer_unavailable`
- Cost answer source does not show `aws_cost_explorer`

## First Checks

```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-05-01,End=2026-05-02 \
  --granularity DAILY \
  --metrics UnblendedCost
```

## Likely Causes

- AWS account has not enabled Cost Explorer
- Lambda execution role lacks `ce:GetCostAndUsage`
- Customer account uses a payer/member account split and the role is in the wrong account
- Tag-scoped query has no matching activated cost allocation tag

## Recovery

1. Confirm Cost Explorer is enabled in the payer account.
2. Verify Lambda IAM includes `ce:GetCostAndUsage`.
3. If using tag scope, activate and populate the tag used by `AEGISDESK_COST_EXPLORER_TAG_KEY`.
4. Temporarily use account-wide scope for pilot validation if the customer approves.
5. Inspect governance replay to confirm only manager/admin users can run cost summaries.

## Safety Note

Do not replace a denied Cost Explorer call with fabricated spend. AegisDesk should show unavailable evidence or documented fallback only.
