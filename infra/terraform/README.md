# Plan-Only AWS Terraform

This directory contains a production-style AWS reference path for AegisDesk. It is intentionally **plan-only** for the portfolio stage: CI validates syntax and provider configuration, but the project does not apply these resources unless deployment is explicitly approved.

## What It Models

- S3 private static web bucket behind CloudFront
- Lambda container API behind HTTP API Gateway
- ECR repository for the API image
- CloudWatch log group with short retention
- Secrets Manager reference for runtime secrets
- Least-privilege Lambda execution role
- AWS Budget capped at the portfolio threshold
- Consistent tags for ownership and cost tracking

## Why This Shape

This avoids EKS, NAT gateways, RDS, and always-on compute. The goal is to prove AWS architecture and infrastructure-as-code judgment while keeping idle cost close to zero if it is ever applied for a short demo.

## Validate Without Deploying

```bash
terraform init -backend=false
terraform fmt -check
terraform validate
```

Do not run `terraform apply` until the cost and account boundary are approved.
