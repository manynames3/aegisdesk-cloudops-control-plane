# Buyer Personas

## VP Engineering

**Pain:** Engineering teams are using AI unevenly, incident work is expensive, and leadership needs evidence that AI adoption is controlled.

**AegisDesk value:** Standardizes AI-assisted CloudOps workflows with identity, policy, audit, and cost controls.

**Proof points to show:** Request replay, approval workflow, cost controls, CI/CD, Terraform deployment, and dashboard metrics.

## Director of Platform Engineering

**Pain:** Platform teams are expected to support AI enablement, internal tooling, operational guardrails, and self-service without creating new risk.

**AegisDesk value:** Provides a reusable gateway and adapter pattern for model routing, OPA policy, internal tools, and traceable operational decisions.

**Proof points to show:** OPA/Rego policy files, adapter interfaces, MCP server, Docker Compose, Terraform, and OpenTelemetry instrumentation.

## Security Engineering Manager

**Pain:** Employees may paste secrets, PII, logs, or production details into external AI systems without clear review or auditability.

**AegisDesk value:** Redacts sensitive values, verifies identity, blocks unsafe actions, supports external model disablement, and preserves audit evidence.

**Proof points to show:** Redaction event, denied production admin request, JWKS verification, data-handling docs, and request replay.

## FinOps Lead

**Pain:** AI usage and cloud spend can grow quickly without team-level visibility, routing policy, caching, or approval thresholds.

**AegisDesk value:** Combines AWS Cost Explorer, model route evidence, per-role quotas, cached summaries, and spend-oriented policy decisions.

**Proof points to show:** Cost Explorer path, role-based cost access, quota policy, cloud-model kill switch, and ROI calculator.

## Service Owner / SRE Manager

**Pain:** Operators need fast triage help, but answers must be grounded in internal runbooks and incident context.

**AegisDesk value:** Pulls trusted runbooks, read-only log context, and policy guidance into the answer while preserving traceability.

**Proof points to show:** Incident prompt, cited runbook, incident context source, answer source score, and audit trail.

## Procurement / Risk Reviewer

**Pain:** New AI tooling must answer basic due diligence questions about data retention, self-hosting, SSO, audit export, and external model usage.

**AegisDesk value:** Provides a clear self-hosted deployment model and a security packet that answers common review questions.

**Proof points to show:** Security overview, data-handling doc, self-hosted install guide, integrations matrix, and compliance packet.
