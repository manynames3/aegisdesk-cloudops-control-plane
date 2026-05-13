# Self-Hosted Deployment

## Option 1: Docker Compose

Docker Compose starts the web UI, API, OPA, Jaeger, and persistent API data volume.

```bash
docker compose up --build
```

Open:

- Web: `http://localhost:3000`
- API: `http://localhost:8000/health`
- OPA: `http://localhost:8181`
- Jaeger: `http://localhost:16686`

## Option 2: Direct Local Run

```bash
cd services/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

## Option 3: AWS Terraform

The Terraform path provisions:

- S3 private static site bucket
- CloudFront distribution
- Lambda API
- HTTP API Gateway with throttling
- Cognito user pool and Hosted UI
- DynamoDB state table
- IAM permissions for Bedrock and Cost Explorer
- CloudWatch logs
- AWS Budget guardrail

Build the Lambda package first:

```bash
scripts/build-lambda-package.sh
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform plan
```

Apply only after reviewing the plan and cost impact:

```bash
terraform -chdir=infra/terraform apply
```

## Required AWS Permissions

The deployment principal needs permission to manage:

- S3 buckets and bucket policies
- CloudFront distributions and invalidations
- Lambda functions and execution roles
- API Gateway HTTP APIs
- Cognito user pools, clients, and domains
- DynamoDB tables
- IAM roles and policies for the application
- CloudWatch log groups
- AWS Budgets
- Bedrock invoke permissions for the approved model ID
- Cost Explorer read-only access

## Expected Cost

For light usage, the AWS shape is designed to stay low cost because it uses serverless services and no always-on compute. Main cost drivers are:

- CloudFront/S3 traffic
- Lambda/API Gateway requests
- DynamoDB reads/writes
- Bedrock token usage when enabled
- Cost Explorer API usage
- CloudWatch logs

Use the Terraform budget variable to cap spend visibility:

```bash
terraform -chdir=infra/terraform apply -var='monthly_budget_usd=5'
```

For a strict local-only install, keep Bedrock and Cost Explorer disabled.

## Required Environment Variables

Core:

```bash
AEGISDESK_POLICY_MODE=opa
OPA_URL=http://opa:8181
AEGISDESK_AUTH_SECRET=replace-with-strong-secret
AEGISDESK_DB_PATH=/app/data/aegisdesk.db
AEGISDESK_MAX_REQUEST_CHARS=2000
AEGISDESK_QUOTA_WINDOW_SECONDS=86400
```

Cognito/OIDC:

```bash
AEGISDESK_COGNITO_USER_POOL_ID=
AEGISDESK_COGNITO_CLIENT_ID=
AEGISDESK_COGNITO_HOSTED_UI_DOMAIN=
AEGISDESK_COGNITO_REGION=us-east-1
AEGISDESK_AUTH_MODE=jwks
AEGISDESK_JWT_ISSUER=
AEGISDESK_JWT_AUDIENCE=
```

AWS state and models:

```bash
AEGISDESK_STORE_BACKEND=dynamodb
AEGISDESK_DYNAMODB_TABLE=
AEGISDESK_ENABLE_BEDROCK=true
AEGISDESK_BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
AEGISDESK_ENABLE_COST_EXPLORER=true
AEGISDESK_COST_CACHE_TTL_SECONDS=21600
```

Disable external models:

```bash
AEGISDESK_ENABLE_BEDROCK=false
AEGISDESK_CLOUD_MODEL_KILL_SWITCH=true
```

## Connect Auth

Recommended production path:

1. Use Cognito Hosted UI federated to Okta or Microsoft Entra ID.
2. Map IdP groups to role/team claims.
3. Configure JWKS issuer and audience.
4. Disable local persona issuance.

```bash
AEGISDESK_PERSONA_ISSUER_ENABLED=false
AEGISDESK_PERSONA_AUTH_ENABLED=false
```

## Connect Ticketing

Implement the `TicketAdapter` interface:

- `LocalTicketAdapter`
- `JiraTicketAdapter`
- `ServiceNowTicketAdapter`

The adapter should create a ticket and return a `ToolCall` result containing external ticket ID, status, team, severity, and source system.

## Connect Incident Context

Implement the `IncidentContextAdapter` interface:

- `LocalFixtureIncidentAdapter`
- `CloudWatchIncidentAdapter`
- `DatadogIncidentAdapter`

The adapter should load read-only evidence and return incident ID, source, query, log group or index, entries, and suspected cause.

## Connect Access Requests

Implement the `AccessRequestAdapter` interface:

- `LocalApprovalAdapter`
- `OktaGroupRequestAdapter`
- `IAMIdentityCenterAdapter`

The adapter should route requests to the system of record for temporary access, then return approval ID, resource, permission, expiry, and status.
