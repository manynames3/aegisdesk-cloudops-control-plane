# Live Operations Evidence

Captured from the hosted AWS environment on May 13, 2026.

This page documents operational controls that are already active in the live deployment. It uses AWS CLI evidence instead of a provisioned CloudWatch Dashboard because managed CloudWatch dashboards introduce a fixed monthly cost. The same metrics can be promoted into a dashboard for a customer environment that wants one.

## Deployment Automation

GitHub Actions deploys through AWS OIDC rather than long-lived AWS access keys.

| Control | Evidence |
| --- | --- |
| OIDC provider | `arn:aws:iam::636305658578:oidc-provider/token.actions.githubusercontent.com` |
| Deploy role | `arn:aws:iam::636305658578:role/aegisdesk-portfolio-github-deploy` |
| Allowed repository subject | `repo:manynames3/aegisdesk-cloudops-control-plane:ref:refs/heads/main` |
| Manual apply subject | `repo:manynames3/aegisdesk-cloudops-control-plane:environment:aws-portfolio` |
| GitHub variable | `AWS_DEPLOY_ROLE_ARN` |

The workflow has two jobs:

- `plan`: assumes the deploy role through OIDC, builds the Lambda package, initializes Terraform, validates, and runs `terraform plan`.
- `apply`: runs only when the workflow input is exactly `deploy`, uses the `aws-portfolio` GitHub environment, reruns plan, applies Terraform, publishes the static frontend, invalidates CloudFront, and smoke-tests `/health`.

Successful GitHub Actions verification:

| Run | Input | Result |
| --- | --- | --- |
| [25779533980](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/25779533980) | `confirm=plan` | OIDC credential exchange, Lambda package build, Terraform init, validate, and plan passed. |
| [25779565098](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/25779565098) | `confirm=deploy` | Plan and manually gated apply path passed, including Terraform apply, static frontend publish, CloudFront invalidation, and API smoke test. |

Post-deploy endpoint checks:

```text
GET https://c2wcg4cdef.execute-api.us-east-1.amazonaws.com/health
{"status":"ok","service":"aegisdesk-api","mode":"hosted"}

HEAD https://d27myiy7bbj1rz.cloudfront.net/marketing
HTTP/2 200
content-type: text/html
```

## Lambda Logs

The API Lambda writes structured request logs to CloudWatch Logs.

```json
[
  {
    "name": "/aws/lambda/aegisdesk-portfolio-api",
    "retention": 7,
    "storedBytes": 155574
  }
]
```

Recent health-check log evidence:

```text
START RequestId: 9c42fa20-b614-4262-8764-915fb5c618da Version: $LATEST
{"level":"INFO","logger":"aegisdesk.api","message":"http_request","timestamp":"2026-05-13T04:53:25+0000","method":"GET","path":"/health","status_code":200,"duration_ms":2.3,"trace_id":"trace-unavailable"}
{"level":"INFO","logger":"mangum.http","message":"GET /health 200","timestamp":"2026-05-13T04:53:25+0000"}
REPORT RequestId: 9c42fa20-b614-4262-8764-915fb5c618da Duration: 136.35 ms Billed Duration: 2786 ms Memory Size: 512 MB Max Memory Used: 146 MB Init Duration: 2649.31 ms
```

## Budget Guardrail

The hosted environment has an AWS Budget resource capped at `$1/month`.

```json
{
  "BudgetName": "aegisdesk-portfolio-monthly-guardrail",
  "BudgetType": "COST",
  "Limit": {
    "Amount": "1.0",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "CalculatedSpend": {
    "ActualSpend": {
      "Amount": "0.0",
      "Unit": "USD"
    }
  }
}
```

## API Gateway Throttling

HTTP API Gateway throttling is configured on the default stage.

```json
[
  {
    "StageName": "$default",
    "AutoDeploy": true,
    "DefaultRouteSettings": {
      "DetailedMetricsEnabled": false,
      "ThrottlingBurstLimit": 20,
      "ThrottlingRateLimit": 5.0
    }
  }
]
```

This supports the cost-governance story alongside application-level prompt size limits, per-role quotas, Cost Explorer caching, and the cloud-model kill switch.

## Evidence Commands

Refresh this page with:

```bash
aws iam list-open-id-connect-providers
aws iam get-role --role-name aegisdesk-portfolio-github-deploy
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/aegisdesk-portfolio-api
aws logs filter-log-events --log-group-name /aws/lambda/aegisdesk-portfolio-api --max-items 10
aws budgets describe-budget --account-id 636305658578 --budget-name aegisdesk-portfolio-monthly-guardrail
aws apigatewayv2 get-stages --api-id c2wcg4cdef
```
