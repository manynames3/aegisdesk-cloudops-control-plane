# AegisDesk Knowledge Base

This directory contains the trusted internal knowledge sources used by the AegisDesk control plane.

The documents are intentionally small but structured like enterprise operational content:

- [Checkout timeout triage runbook](checkout-timeout-triage-runbook.md)
- [Production access control policy](production-access-control-policy.md)
- [AI and cloud cost governance policy](ai-cloud-cost-governance-policy.md)

The API retrieves these files by request intent and returns them in `knowledge_citations` and `answer_sources` so reviewers can distinguish grounded internal evidence from model-generated text.
