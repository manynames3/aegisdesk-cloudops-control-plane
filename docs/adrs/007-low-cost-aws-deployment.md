# ADR-007: Deploy a Low-Cost AWS Portfolio Environment After Approval

## Status

Accepted

## Context

The project should prove AWS architecture and infrastructure-as-code ability without creating surprise spend. The initial portfolio stage validated Terraform without applying resources. Once deployment was explicitly approved, the hosted environment still needed to stay within a very small monthly cost boundary.

## Decision

Use Terraform to deploy a low-idle-cost AWS shape: private S3 and CloudFront for the static frontend, a FastAPI Lambda zip behind HTTP API Gateway, DynamoDB for durable demo state, least-privilege IAM, Bedrock invoke permission for the approved model, CloudWatch logs with short retention, S3 encryption and lifecycle cleanup, S3 remote Terraform state, and an AWS Budget guardrail.

Keep destructive cloud actions mocked or approval-only. Only approved low-sensitivity prompts can call Bedrock, and quota policy limits role/team usage.

## Consequences

- Reviewers can inspect real deployed AWS resource choices, IAM boundaries, logging, and cost guardrails.
- The hosted demo avoids EKS, NAT gateways, RDS, and always-on compute until there is a stronger reason to pay for them.
- Remote Terraform state contains deployment metadata and demo JWKS private key material, so access to the state bucket must stay restricted.
- Production identity, managed secrets, immutable audit storage, and stronger tenant isolation remain future hardening work.
