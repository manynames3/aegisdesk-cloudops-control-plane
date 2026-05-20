# Buyer README

## What Is AegisDesk?

AegisDesk is a self-hosted CloudOps AI control plane. It gives employees an approved place to ask operational questions while giving platform, security, and FinOps teams control over policy, data, tools, models, cost, and audit records.

## Who Uses It?

- Employees and engineers ask for help
- Managers approve scoped access requests
- Platform teams configure integrations and policies
- Security teams review audit evidence
- FinOps teams monitor cloud and AI spend

## What Does It Connect To?

- Identity: Cognito, Okta, Entra-compatible OIDC/JWKS
- Models: Amazon Bedrock and local control fallback
- Cost: AWS Cost Explorer
- Logs: CloudWatch or Datadog through adapters
- Tickets: Jira or ServiceNow through adapters
- Access: Okta groups or IAM Identity Center through adapters
- Agents: MCP clients such as Codex

## What Makes It Different?

AegisDesk is not a general AI chat surface. It is a governed workflow system for CloudOps. It shows the policy decision, redaction result, model route, sources, tool calls, approvals, spend signal, and audit trail behind each answer.

## How Would We Start?

1. Run Docker Compose locally or deploy the AWS Terraform path.
2. Connect SSO or Cognito Hosted UI.
3. Configure OPA policies for roles, teams, data classes, and model routes.
4. Connect one operational workflow first: ticketing, incident context, access approval, or cost review.
5. Enable Bedrock only for approved low-risk requests.
6. Review audit replay with security and platform stakeholders.

## Recommended Paid Pilot

A focused pilot should prove one workflow, not every possible integration.

- **Duration:** 30-60 days
- **Best first workflow:** incident triage with Jira ticketing or CloudWatch-backed incident context
- **Success criteria:** users can ask for help, sensitive values are redacted, policy decisions are visible, approved requests can use Bedrock, and every answer has a replayable audit packet
- **Commercial shape:** paid implementation pilot followed by a self-hosted annual license and integration support
- **What to avoid early:** broad multi-cloud rollout, destructive production actions, and custom automation before the governance workflow is trusted
