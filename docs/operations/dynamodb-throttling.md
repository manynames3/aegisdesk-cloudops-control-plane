# Runbook: DynamoDB Throttling

## Symptoms

- Audit export is slow or incomplete
- Approval decisions fail intermittently
- Quota checks behave inconsistently
- Lambda logs contain DynamoDB throttling or throughput errors

## First Checks

```bash
aws dynamodb describe-table --table-name "$AEGISDESK_DYNAMODB_TABLE"
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value="$AEGISDESK_DYNAMODB_TABLE" \
  --statistics Sum \
  --period 300 \
  --start-time "$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

## Likely Causes

- Pilot traffic exceeded on-demand burst assumptions
- Audit export is reading too large a window
- A load test reused one role/team and hit hot partition patterns
- DynamoDB table was recreated without TTL or on-demand billing

## Recovery

1. Confirm the table is using on-demand billing for pilots.
2. Reduce `AEGISDESK_AUDIT_EXPORT_MAX_EVENTS` if exports are too broad.
3. Confirm TTL is enabled on `expires_at`.
4. Re-run local load smoke to separate app behavior from AWS throttling.
5. For production scale, split high-write entities or add GSIs based on observed query patterns.

## Safety Note

If audit writes fail, stop expanding pilot usage. Governance evidence is part of the product promise.
