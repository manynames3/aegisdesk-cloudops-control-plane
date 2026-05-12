# AWS Terraform Deployment

This directory contains the low-cost AWS deployment path for AegisDesk.

## What It Provisions

- Private S3 bucket for the exported static frontend
- CloudFront distribution with origin access control
- FastAPI Lambda zip package behind HTTP API Gateway
- Least-privilege Lambda execution role
- CloudWatch log group with seven-day retention
- S3 public access block, server-side encryption, versioning, and noncurrent version cleanup
- AWS Budget capped at the portfolio threshold
- Consistent default tags for ownership and cost tracking

## Why This Shape

This avoids EKS, NAT gateways, RDS, ECS/Fargate, and always-on compute. The goal is to prove AWS architecture and infrastructure-as-code judgment while keeping idle cost low for a portfolio demo.

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
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*"
```

## Cost Guardrails

The Terraform path includes an AWS Budget resource set by `monthly_budget_usd`, which defaults to `1`. The architecture avoids fixed-cost infrastructure; actual cost depends on request volume, log volume, and data transfer.

## State Boundary

Terraform state contains deployment metadata and the generated demo auth secret. Do not commit `*.tfstate` files. For a team or production environment, move state to a remote backend with encryption and access controls.
