# Governance Model

AegisDesk enforces controls before AI responses and tool actions.

## Control Points

### 1. Input Inspection

Before routing to a model:

- Detect secrets
- Detect PII
- Detect privileged action intent
- Classify request sensitivity

Possible outcomes:

- Allow as-is
- Redact then continue
- Route to local model
- Require approval
- Block

### 2. Model Routing Policy

Example routing rules:

- Public documentation requests can use cloud model.
- Internal operational context can use local model.
- Requests containing secrets are blocked or redacted before model use.
- High-cost models require budget availability or admin override.

### 3. Tool Authorization

Before any MCP tool call:

- Validate user role
- Validate action
- Validate resource
- Validate request context
- Check whether approval is required

Example:

| User Role | Action | Result |
| --- | --- | --- |
| Employee | Create support ticket | Allow |
| Employee | Request production admin access | Deny |
| Employee | Request temporary read-only access | Approval required |
| Manager | Approve scoped access | Allow |
| Admin | View audit dashboard | Allow |

### 4. Approval Workflow

Some actions are neither fully allowed nor fully denied. They require manager approval.

Examples:

- Temporary read-only production access
- High-cost model use
- External escalation
- Access to sensitive incident details

### 5. Audit Trail

Every important decision should produce an audit event:

- user_id
- role
- request_id
- action
- resource
- policy_result
- policy_reason
- model_route
- redaction_findings
- tool_name
- approval_status
- estimated_cost
- trace_id

## Governance Principle

The AI should never become a shortcut around existing enterprise controls.

Natural language is an interface. Policy remains the authority.

