# Cost Strategy

AegisDesk is designed to demonstrate cost-conscious enterprise architecture.

## MVP Cost Goal

Target:

- Local development: $0
- Demo operation: $0 to low single digits
- Optional hosted demo: free tier or shut down after recording

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

### Plan-Only AWS IaC

Terraform models a low-idle-cost AWS path but CI only runs `fmt`, `init -backend=false`, and `validate`.

Why:

- Proves AWS architecture choices without creating resources
- Avoids NAT gateways, EKS, RDS, and always-on compute before there is a real need
- Keeps the deployment decision separate from the implementation review
- Adds an AWS Budget guardrail if the plan is ever applied

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

> I built the MVP local-first so the system can be reviewed without ongoing cloud spend. The AWS path is modeled in Terraform and validated in CI, but I intentionally stop before apply so architecture review is separate from spending money.
