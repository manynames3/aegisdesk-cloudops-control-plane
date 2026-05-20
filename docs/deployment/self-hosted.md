# Self-Hosted Deployment

## Option 1: Docker Compose

Docker Compose starts the web UI, API, OPA, Jaeger, and persistent API data volume.

```bash
cp .env.example .env
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

Start from `.env.example`; it includes the local evaluation defaults and the production-mode switches.

Core:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_AEGISDESK_MODE=evaluation
NEXT_PUBLIC_SHOW_EVALUATION_TOOLS=true
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

Ticketing and audit controls:

```bash
AEGISDESK_TICKET_ADAPTER=local
AEGISDESK_JIRA_BASE_URL=
AEGISDESK_JIRA_EMAIL=
AEGISDESK_JIRA_API_TOKEN=
AEGISDESK_JIRA_PROJECT_KEY=
AEGISDESK_JIRA_ISSUE_TYPE=Task
AEGISDESK_SERVICENOW_INSTANCE_URL=
AEGISDESK_SERVICENOW_USERNAME=
AEGISDESK_SERVICENOW_PASSWORD=
AEGISDESK_SERVICENOW_ASSIGNMENT_GROUP=
AEGISDESK_SERVICENOW_TABLE=incident
AEGISDESK_INCIDENT_CONTEXT_ADAPTER=local_fixture
AEGISDESK_CLOUDWATCH_LOG_GROUP=
AEGISDESK_CLOUDWATCH_LOGS_REGION=us-east-1
AEGISDESK_CLOUDWATCH_QUERY_LOOKBACK_MINUTES=60
AEGISDESK_CLOUDWATCH_QUERY_LIMIT=20
AEGISDESK_AUDIT_RETENTION_DAYS=30
AEGISDESK_AUDIT_EXPORT_MAX_EVENTS=500
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
5. Set the web app to production mode so users see the SSO entry point instead of evaluation personas.

```bash
NEXT_PUBLIC_AEGISDESK_MODE=production
NEXT_PUBLIC_SHOW_EVALUATION_TOOLS=false
AEGISDESK_PERSONA_ISSUER_ENABLED=false
AEGISDESK_PERSONA_AUTH_ENABLED=false
```

## Connect Ticketing

Use the local adapter for evaluation or enable Jira for a real pilot workflow:

```bash
AEGISDESK_TICKET_ADAPTER=jira
AEGISDESK_JIRA_BASE_URL=https://your-domain.atlassian.net
AEGISDESK_JIRA_EMAIL=cloudops-bot@example.com
AEGISDESK_JIRA_API_TOKEN=replace-with-secret
AEGISDESK_JIRA_PROJECT_KEY=OPS
```

The Jira adapter creates an issue through Jira REST API v3 and returns the external ticket ID, status, team, severity, adapter, source system, and ticket URL.

For ServiceNow:

```bash
AEGISDESK_TICKET_ADAPTER=servicenow
AEGISDESK_SERVICENOW_INSTANCE_URL=https://your-instance.service-now.com
AEGISDESK_SERVICENOW_USERNAME=aegisdesk.integration
AEGISDESK_SERVICENOW_PASSWORD=replace-with-secret
AEGISDESK_SERVICENOW_ASSIGNMENT_GROUP=
AEGISDESK_SERVICENOW_TABLE=incident
```

The ServiceNow adapter creates a record through the Table API and returns the ticket number, sys_id, status, adapter, source system, and record URL. If Jira or ServiceNow is selected but missing configuration, or if the external API fails at runtime, AegisDesk does not fabricate success; the tool result is blocked and the failure is preserved in the audit trail.

## Connect Incident Context

Use the local fixture source for evaluation, or connect CloudWatch Logs for a real incident workflow:

```bash
AEGISDESK_INCIDENT_CONTEXT_ADAPTER=cloudwatch
AEGISDESK_CLOUDWATCH_LOG_GROUP=/aws/lambda/your-service
AEGISDESK_CLOUDWATCH_LOGS_REGION=us-east-1
AEGISDESK_CLOUDWATCH_QUERY_LOOKBACK_MINUTES=60
AEGISDESK_CLOUDWATCH_QUERY_LIMIT=20
```

The deployed role needs read-only Logs Insights permissions:

- `logs:StartQuery`
- `logs:GetQueryResults`
- `logs:StopQuery`

Scope the IAM resource to the customer log group ARN when possible. The adapter uses strict lookback and result limits. If CloudWatch is selected without a log group or a query fails, AegisDesk does not fabricate fixture evidence; it records the unavailable context in the audit trail.

Supported incident adapters:

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
