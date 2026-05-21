# Architecture Tradeoffs

## Why Lambda

Lambda keeps the hosted control plane low idle cost and simple to operate for a small pilot. The tradeoff is cold starts and less control over long-lived connections. If customers need high sustained throughput, ECS/Fargate or EKS would be the next runtime.

## Why DynamoDB

DynamoDB is a good fit for append-heavy audit events, approval records, route decisions, quotas, and short-lived caches. It also supports TTL for bounded retention. The tradeoff is that ad hoc analytics are weaker than in Postgres or a data warehouse, so long-term compliance export should go to S3/SIEM.

## Why OPA/Rego

OPA keeps authorization and routing rules outside the model and outside frontend code. This makes decisions reviewable and testable. The tradeoff is operational complexity: OPA must be healthy, tested, and versioned.

## Why Cognito

Cognito gives a low-cost AWS-native OIDC boundary with Hosted UI and JWKS verification. It also supports federation to Okta and Entra. The tradeoff is less polished enterprise identity UX than a dedicated IdP product.

## Why Local Fallback

Local fallback keeps the product useful when Bedrock is disabled, unavailable, too expensive, or blocked by customer data-boundary policy. The tradeoff is less fluent generation for open-ended help. The fallback is intentionally conservative.

## Why Adapter Interfaces

Adapters keep Jira, ServiceNow, CloudWatch, Cost Explorer, and future tools behind bounded contracts. This avoids hardcoding one customer's stack into policy, audit, or UI logic. The tradeoff is that each adapter still needs customer-specific field mapping and sandbox validation.
