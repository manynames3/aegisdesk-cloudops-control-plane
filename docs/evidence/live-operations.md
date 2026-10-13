# Live Operations Evidence

Latest application deployment verified on October 13, 2026. The AWS CLI baseline below was captured on May 13, 2026; its log, metric, and budget-spend samples are historical, not current measurements.

## Latest Deployment (2026-10-13)

Deployed revision: [`def6f81533b2cd2e591d12ef3fa215d0db05fe7e`](https://github.com/manynames3/aegisdesk-cloudops-control-plane/commit/def6f81533b2cd2e591d12ef3fa215d0db05fe7e). This documentation refresh changed no application source or Terraform resource definitions; the deployment workflow rebuilt the existing Lambda package and republished the frontend. Later evidence-only commits do not change the deployed application.

| Evidence | Result |
| --- | --- |
| [CI](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38352636804) | All nine jobs passed before deployment, including API/browser/policy tests, MCP smoke, security, Terraform validation, frontend and container builds. |
| [Plan-only preflight](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38352665461) | Only the existing Lambda function and S3 package object changed in place: zero adds, two changes, zero destroys. |
| [AWS deployment](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38352824446) | Plan and gated apply passed. Terraform reported zero added, two changed, zero destroyed. Frontend publication and API smoke passed. |
| CloudFront invalidation | AWS CLI confirmed `I9ZHI11U1JGNQFURM5ZF087KWM` on distribution `EYXXWE0YJP0QZ` completed. |
| Public API checks | `/health` and `/health/ready` returned 200; DynamoDB and OPA subprocess readiness were true. Anonymous `GET /incidents` returned 401. |
| Frontend delivery | CloudFront `/` and `/marketing` returned HTTP 200 after publication. |
| Setup status | Evaluation personas remain enabled; Jira, ServiceNow, and customer CloudWatch evidence remain unconfigured. Configuration flags are not live integration proof. |

No hosted case write, authenticated case read, provider execution, trace export, or recovery drill was repeated in this redeploy smoke check. It created no cases and executed no operational API tools. The screenshots and authenticated read/browser evidence below remain dated October 10, not new customer activity.

## Incident Release (2026-10-10)

Runtime revision: [`e80927c41f87de8cf95fff5799ed447df278902c`](https://github.com/manynames3/aegisdesk-cloudops-control-plane/commit/e80927c41f87de8cf95fff5799ed447df278902c). README and evidence updates made after deployment do not change the deployed application.

| Evidence | Result |
| --- | --- |
| [Runtime CI](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027293724) | All nine jobs passed, including 13 browser tests, API/policy tests, MCP smoke, security checks, Terraform validation, and three container builds. |
| [Preflight plan](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027153191) | Existing Lambda update and artifact upload; zero resource deletions. |
| [AWS deployment](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38027407776) | OIDC, plan, gated apply, frontend publish, and API smoke passed. AWS CLI confirmed CloudFront invalidation `I1GT4Q8HOMXYFYFOTSHFE195ZG` completed. Terraform reported one S3 artifact object added, one Lambda function changed, zero resources destroyed. |
| API liveness/readiness | `/health` and `/health/ready` returned 200; DynamoDB store and OPA subprocess were ready. |
| Incident authentication/read | Anonymous `GET /incidents` returned 401; a Cognito evaluation persona's request returned 200 from the DynamoDB-backed case listing. |
| Branding | CloudFront wordmark and favicon bytes exactly matched the committed SVG assets. |
| Browser rendering | Playwright verified the app at 1440px and 375px and the marketing header. [Hosted desktop screenshot](screenshots/incident-hosted-desktop.png). |

This remains an evaluation deployment: reviewer personas are enabled, Jira and CloudWatch are unconfigured, and no customer integration success is claimed. Hosted case writes, real ticket execution, and trace export were not tested in this deployment smoke check. No incident was created and no operational tool was executed by the check. Local fixture tests are not hosted integration evidence.

## Historical Baseline

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

The historical AWS sample shows a Budget threshold of `$1/month`. This records a budget target, not a hard spending cap or proof of configured alert delivery.

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
