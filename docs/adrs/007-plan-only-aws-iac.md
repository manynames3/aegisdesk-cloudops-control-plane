# ADR-007: Model AWS Deployment With Plan-Only Terraform Before Spending

## Status

Accepted

## Context

The project should prove AWS architecture and infrastructure-as-code ability, but the portfolio stage should not create ongoing cloud spend or surprise resources.

## Decision

Add Terraform for a low-idle-cost AWS reference path and validate it in CI without applying it. The modeled path uses S3, CloudFront, Lambda container runtime, HTTP API Gateway, ECR, IAM, CloudWatch logs, Secrets Manager reference, and an AWS Budget guardrail.

## Consequences

- Reviewers can inspect real AWS resource choices, IAM boundaries, logging, and cost guardrails.
- CI can validate IaC quality at no cloud cost.
- No cloud resources are created until deployment is explicitly approved.
- The plan avoids EKS, NAT gateways, RDS, and always-on compute until there is a stronger reason to pay for them.
