# ADR-007: Deploy a Low-Cost AWS Environment After Approval

## Status

Accepted

## Context

The project should prove AWS architecture and infrastructure-as-code ability without creating surprise spend. The hosted environment needs to stay within a very small monthly cost boundary unless higher-traffic usage is explicitly approved.

## Decision

Use Terraform to deploy a low-idle-cost AWS shape: private S3 and CloudFront for the static frontend, a FastAPI Lambda zip behind HTTP API Gateway, Cognito for hosted identity, DynamoDB for durable state and cache entries, least-privilege IAM, Bedrock invoke permission for the approved model, Cost Explorer read access for manager/admin cost summaries, CloudWatch logs with short retention, S3 encryption and lifecycle cleanup, S3 remote Terraform state, and an AWS Budget guardrail.

Keep destructive cloud actions approval-only. Only approved low-sensitivity prompts can call Bedrock, and quota policy limits role/team usage.

## Consequences

- Reviewers can inspect real deployed AWS resource choices, IAM boundaries, logging, and cost guardrails.
- The hosted deployment avoids EKS, NAT gateways, RDS, and always-on compute until there is a stronger reason to pay for them.
- Remote Terraform state contains deployment metadata and generated persona seed material, so access to the state bucket must stay restricted.
- Enterprise federation, managed secrets, immutable audit storage, and stronger tenant isolation remain future hardening work.
