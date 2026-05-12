# Cost Strategy

AegisDesk is designed to demonstrate cost-conscious enterprise architecture.

## MVP Cost Goal

Target:

- Local development: $0
- Demo operation: $0 to low single digits
- Hosted demo: low single digits for light traffic, guarded by a $1 AWS Budget

## Cost-Conscious Choices

### Local-First Runtime

Use Docker Compose and Ollama for the primary demo path.

Why:

- No required cloud spend
- Easy to reproduce
- No surprise bills
- Demonstrates local/private model option

### Mock Destructive Cloud Tools

Use mock tools for access grants and infrastructure changes.

Why:

- Avoids real cloud risk
- Keeps demo safe
- Shows control pattern without requiring paid cloud resources

### Optional Cloud Model

Cloud model integration should be optional and controlled by environment variables.

Why:

- Project works without paid API keys
- Demo can still show cloud routing logic
- Cost exposure is explicit

### Estimated Cost Display

Dashboard should show estimated AI cost by:

- Request
- User
- Team
- Model
- Route reason

Why:

- Makes FinOps thinking visible
- Shows enterprise value beyond the chat UI

### Low-Cost AWS Deployment

Terraform deploys a low-idle-cost AWS path for the portfolio demo.

Why:

- Proves AWS architecture choices with real deployed resources
- Avoids NAT gateways, EKS, RDS, and always-on compute before there is a real need
- Uses a private S3 static site behind CloudFront
- Runs the API only on request through Lambda and HTTP API Gateway
- Adds an AWS Budget guardrail at the portfolio threshold
- Keeps paid model providers disabled

## Production Cost Considerations

Production costs would come from:

- API hosting
- Frontend hosting
- Managed database
- Observability storage
- Model API usage
- Kubernetes cluster or serverless runtime
- Secrets and audit storage

Optimization options:

- Route low-sensitivity traffic to cheaper models
- Use local/private models for sensitive or high-volume workflows
- Cache repeated support answers
- Set per-team budgets
- Use rate limits
- Shut down non-production environments
- Use reserved or savings plans only after usage stabilizes

## Portfolio Talking Point

Say:

> After validating the architecture locally, I deployed the portfolio version on a static/serverless AWS footprint: S3, CloudFront, Lambda, HTTP API Gateway, CloudWatch, IAM, and an AWS Budget guardrail. I avoided EKS, NAT gateways, RDS, and paid model calls because they would add cost without improving the demo signal.
