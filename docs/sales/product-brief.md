# One-Page Product Brief

## AegisDesk CloudOps Control Plane

AegisDesk is a self-hosted AI control plane for CloudOps teams. It lets employees ask for help with incidents, tickets, access requests, and cloud cost questions while enforcing identity, policy, redaction, approvals, model routing, and audit trails.

## The Problem

Employees want to use AI during operational work, but companies need answers to governance questions:

- Who asked?
- What sensitive data was removed?
- Which policy allowed or denied the action?
- Which model answered?
- What tool was called?
- What did it cost?
- Where is the audit evidence?

## The Product

AegisDesk places a controlled gateway between employees, models, policies, tools, and audit storage.

Core capabilities:

- SSO-compatible identity and role/team claims
- OPA/Rego policy enforcement
- Secret and PII redaction
- Bedrock model routing with external model disablement
- AWS Cost Explorer with cache
- Ticket, incident, and access adapter interfaces
- MCP server for agent clients
- DynamoDB audit trail and request replay

## Target Buyers

- VP Engineering
- Director of Platform Engineering
- Security Engineering Manager
- FinOps Lead
- SRE or CloudOps Manager

## Why It Matters

AegisDesk helps companies adopt AI in CloudOps while preserving the evidence, controls, and operational boundaries expected in production environments.
