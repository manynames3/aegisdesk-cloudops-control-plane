# Cost Strategy

AegisDesk is designed to demonstrate cost-conscious enterprise architecture.

## MVP Cost Goal

Target:

- Local development: $0
- Local operation: $0 to low single digits
- Hosted portfolio deployment: low single digits for light traffic, guarded by a $1 AWS Budget

## Cost-Conscious Choices

### Local-First Runtime

Use Docker Compose and Ollama for the primary local path.

Why:

- No required cloud spend
- Easy to reproduce
- No surprise bills
- Demonstrates local/private model option

### Mock Destructive Cloud Tools

Use mock tools for access grants and infrastructure changes.

Why:

- Avoids real cloud risk
- Keeps the portfolio environment safe
- Shows control pattern without requiring paid cloud resources

### Governed Bedrock Route

Amazon Bedrock Nova Lite is enabled in the hosted deployment only for approved low-sensitivity prompts. Local development and tests use deterministic fallback unless Bedrock is explicitly enabled.

Why:

- Project works without paid API keys
- Shows a real AWS model invocation path
- Cost exposure is explicit
- Sensitive, denied, or quota-blocked requests do not call Bedrock

### Governed Cost Explorer Path

Manager/admin cost investigations call AWS Cost Explorer when enabled. Results are cached in DynamoDB for six hours so repeated walkthroughs do not repeatedly call the Cost Explorer API.

Why:

- Proves a real AWS cost-governance integration
- Keeps cost visibility behind role and policy checks
- Avoids repeated billing API calls during reviewer walkthroughs
- Shows honest behavior when tagged spend is zero or tags are not yet active

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

Terraform deploys a low-idle-cost AWS path for the portfolio deployment.

Why:

- Proves AWS architecture choices with real deployed resources
- Avoids NAT gateways, EKS, RDS, and always-on compute before there is a real need
- Uses a private S3 static site behind CloudFront
- Runs the API only on request through Lambda and HTTP API Gateway
- Uses DynamoDB on-demand capacity for small durable state
- Adds an AWS Budget guardrail at the portfolio threshold
- Enforces per-role/team quota policy before Bedrock or tool execution

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

> After validating the architecture locally, I deployed the portfolio version on a static/serverless AWS footprint: Cognito, S3, CloudFront, Lambda, HTTP API Gateway, DynamoDB, Bedrock Nova Lite, Cost Explorer, CloudWatch, IAM, and an AWS Budget guardrail. I avoided EKS, NAT gateways, RDS, and always-on compute because they would add cost without improving the architecture signal.
