# 90-Second Walkthrough Video Script

## Goal

Show AegisDesk as a self-hosted CloudOps AI control plane, not a generic chatbot.

## Script

**0:00-0:10 - Open**

"AegisDesk gives employees AI help for CloudOps while the company keeps control over identity, policy, data, model routing, approvals, cost, and audit trails."

**0:10-0:25 - Identity**

Show Cognito Hosted UI or the identity shortcut. Point out that the backend derives role and team from token claims.

**0:25-0:40 - Incident Triage**

Ask: "INC-1042 checkout is timing out. What should I check first?"

Show runbook citations, incident context, source score, policy allow, and Bedrock or local route.

**0:40-0:55 - Secret Redaction**

Ask a prompt containing a harmless secret-shaped value and an email.

Show redaction badges and explain that sensitive values are removed before routing.

**0:55-1:10 - Production Access**

Ask for production admin access as employee.

Show denial, safer scoped approval path, pending approval, manager approval, and audit event trail.

**1:10-1:25 - Cost Governance**

Switch to manager. Ask why cloud or AI cost spiked.

Show AWS Cost Explorer source/cache, role enforcement, cost recommendation, and route evidence.

**1:25-1:30 - Close**

"Every answer has a trace: prompt, redaction, policy, route, sources, tools, approvals, and audit events. That is the control plane around CloudOps AI."
