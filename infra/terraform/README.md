# AWS Terraform Deployment

This directory contains the low-cost AWS deployment path for AegisDesk.

## What It Provisions

- Private S3 bucket for the exported static frontend
- CloudFront distribution with origin access control
- FastAPI Lambda zip package behind HTTP API Gateway
- HTTP API Gateway default route throttling for abuse and cost control
- Amazon Cognito user pool, app client, and role groups for hosted identity
- DynamoDB table for hosted audit events, approvals, route history, metrics, quotas, and cached cost summaries
- Amazon Bedrock Nova Lite invoke permission for approved low-sensitivity prompts
- AWS Cost Explorer read permission for manager/admin cost investigations
- Least-privilege Lambda execution role
- CloudWatch log group with seven-day retention
- S3 public access block, server-side encryption, versioning, and noncurrent version cleanup
- S3 backend for shared Terraform state
- AWS Budget capped at the configured threshold
- GitHub Actions OIDC deploy role for keyless CI/CD
- Consistent default tags for ownership and cost tracking

## Why This Shape

This avoids EKS, NAT gateways, RDS, ECS/Fargate, and always-on compute. The goal is to provide a credible AWS architecture while keeping idle cost low for self-hosted evaluation.

## Build and Deploy

From the repository root:

```bash
scripts/build-lambda-package.sh
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform apply tfplan
```

After Terraform creates the API and frontend bucket:

```bash
API_URL=$(terraform -chdir=infra/terraform output -raw api_gateway_url)
BUCKET=$(terraform -chdir=infra/terraform output -raw frontend_bucket_name)
DIST_ID=$(terraform -chdir=infra/terraform output -raw frontend_distribution_id)

NEXT_PUBLIC_API_BASE_URL="$API_URL" npm run build:web
aws s3 sync apps/web/out "s3://$BUCKET" --delete
aws s3 cp apps/web/out/marketing.html "s3://$BUCKET/marketing" --content-type text/html
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*"
```

## GitHub Actions Deploy

The AWS deploy workflow uses GitHub Actions OIDC instead of long-lived AWS access keys.

Terraform provisions `aws_iam_role.github_deploy` and outputs `github_deploy_role_arn`. Store that ARN as the repository or environment variable `AWS_DEPLOY_ROLE_ARN`:

```bash
gh variable set AWS_DEPLOY_ROLE_ARN --body "$(terraform -chdir=infra/terraform output -raw github_deploy_role_arn)"
```

The workflow has two paths:

- `confirm=plan`: build the Lambda package, initialize Terraform, validate, and run `terraform plan`.
- `confirm=deploy`: run the plan job, then run a manually gated `aws-portfolio` environment job that applies Terraform, publishes the static frontend, invalidates CloudFront, and smoke-tests the API.

The IAM trust policy allows only this repository on `main` and the `aws-portfolio` deployment environment to assume the role.

## Cost Guardrails

The Terraform path includes an AWS Budget resource set by `monthly_budget_usd`, which defaults to `1`. The architecture avoids fixed-cost infrastructure; actual cost depends on request volume, log volume, and data transfer.

Additional runtime guardrails are controlled through Terraform variables:

- `api_throttling_rate_limit` and `api_throttling_burst_limit` configure HTTP API Gateway throttles.
- `max_request_chars` rejects oversized prompts before policy or model routing.
- `cloud_model_kill_switch` forces approved Bedrock routes back to local control handling when cost or abuse risk is elevated.

## State Boundary

Terraform state is stored in the encrypted S3 backend configured in `backend.tf`. It contains deployment metadata and generated persona seed material, so state bucket access must stay restricted.
