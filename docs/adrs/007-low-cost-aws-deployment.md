# ADR-007: Deploy a Low-Cost AWS Portfolio Environment After Approval

## Status

Accepted

## Context

The project should prove AWS architecture and infrastructure-as-code ability without creating surprise spend. The initial portfolio stage validated Terraform without applying resources. Once deployment was explicitly approved, the hosted environment still needed to stay within a very small monthly cost boundary.

## Decision

Use Terraform to deploy a low-idle-cost AWS shape: private S3 and CloudFront for the static frontend, a FastAPI Lambda zip behind HTTP API Gateway, least-privilege IAM, CloudWatch logs with short retention, S3 encryption and lifecycle cleanup, and an AWS Budget guardrail.

Keep paid model providers disabled in the hosted demo. Keep destructive cloud actions mocked or approval-only.

## Consequences

- Reviewers can inspect real deployed AWS resource choices, IAM boundaries, logging, and cost guardrails.
- The hosted demo avoids EKS, NAT gateways, RDS, and always-on compute until there is a stronger reason to pay for them.
- Terraform local state now contains deployment metadata and the generated demo auth secret, so state files must remain uncommitted.
- Production identity, managed secrets, immutable audit storage, and rate limiting remain future hardening work.
