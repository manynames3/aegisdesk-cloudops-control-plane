# Runbook: OPA Unavailable

## Symptoms

- Chat requests return HTTP 503
- `/health/ready` reports policy not ready
- Audit trail stops before policy decisions

## First Checks

```bash
curl -fsS "$OPA_URL/health"
opa test policies
aws logs filter-log-events --log-group-name /aws/lambda/aegisdesk-portfolio-api --filter-pattern policy_engine_unavailable
```

## Likely Causes

- OPA sidecar/container is not running
- `OPA_URL` points to the wrong host
- Rego bundle did not load
- OPA timeout is too low for the environment
- Lambda is configured for `opa` mode without reachable OPA

## Recovery

1. Confirm whether this environment should use OPA HTTP, OPA subprocess, or Python fallback.
2. If OPA HTTP is required, restore OPA health before allowing sensitive requests.
3. If this is a local evaluation, switch `AEGISDESK_POLICY_MODE=auto` to allow explicit Python fallback.
4. Re-run policy tests and one denied production admin request.

## Safety Note

When OPA mode is selected and unavailable, the API fails closed instead of approving requests without policy.
