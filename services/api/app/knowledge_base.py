from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .models import KnowledgeCitation


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    source_path: str
    section: str
    owner: str
    last_reviewed: str
    keywords: tuple[str, ...]


DOCUMENTS = {
    "checkout_runbook": KnowledgeDocument(
        doc_id="KB-CLOUDOPS-001",
        title="Checkout Timeout Triage Runbook",
        source_path="docs/knowledge/checkout-timeout-triage-runbook.md",
        section="Initial Triage Sequence",
        owner="CloudOps Platform Team",
        last_reviewed="2026-05-01",
        keywords=("checkout", "timeout", "timing out", "latency", "connection pool", "incident", "error", "log"),
    ),
    "production_access_policy": KnowledgeDocument(
        doc_id="POL-SEC-014",
        title="Production Access Control Policy",
        source_path="docs/knowledge/production-access-control-policy.md",
        section="Approved Access Pattern",
        owner="Security Engineering",
        last_reviewed="2026-04-20",
        keywords=("admin access", "production", "prod", "database", "read-only", "approval", "access"),
    ),
    "cost_governance_policy": KnowledgeDocument(
        doc_id="GOV-FINOPS-007",
        title="AI And Cloud Cost Governance Policy",
        source_path="docs/knowledge/ai-cloud-cost-governance-policy.md",
        section="Cost Governance Principles",
        owner="FinOps And Platform Engineering",
        last_reviewed="2026-05-05",
        keywords=("cost", "spend", "spike", "budget", "bedrock", "cache", "quota", "finops"),
    ),
}


INTENT_DOCUMENTS = {
    "incident_triage": ("checkout_runbook",),
    "create_ticket": ("checkout_runbook",),
    "production_admin_access": ("production_access_policy",),
    "temporary_read_only_access": ("production_access_policy",),
    "cost_investigation": ("cost_governance_policy",),
    "support_guidance": ("cost_governance_policy", "production_access_policy"),
}


def retrieve_knowledge(intent: str, query: str, limit: int = 2) -> list[KnowledgeCitation]:
    selected_keys = list(INTENT_DOCUMENTS.get(intent, ()))
    query_lower = query.lower()

    for key, document in DOCUMENTS.items():
        if key not in selected_keys and any(keyword in query_lower for keyword in document.keywords):
            selected_keys.append(key)

    return [_citation_for(DOCUMENTS[key]) for key in selected_keys[:limit]]


def format_knowledge_context(citations: list[KnowledgeCitation]) -> str | None:
    if not citations:
        return None
    return "\n\n".join(
        (
            f"Source: {citation.title} ({citation.doc_id})\n"
            f"Path: {citation.source_path}\n"
            f"Section: {citation.section}\n"
            f"Excerpt: {citation.excerpt}"
        )
        for citation in citations
    )


def summarize_knowledge_guidance(intent: str, citations: list[KnowledgeCitation]) -> str:
    if not citations:
        return ""

    if intent == "incident_triage":
        return (
            " Runbook guidance: confirm user impact, compare the alert against the last checkout deployment, "
            "check database pool saturation, then verify upstream payment latency before recommending rollback or scaling."
        )

    if intent == "production_admin_access":
        return (
            " Access policy source: production admin access is not self-service; use a temporary read-only request "
            "with manager approval, scoped permission, expiration, and audit evidence."
        )

    if intent == "cost_investigation":
        return (
            " Cost governance source: attribute spend by team and route, check cache status, identify the largest driver, "
            "and apply model routing, quota, or caching controls before raising limits."
        )

    if intent == "create_ticket":
        return " Runbook handoff: include incident ID, service, suspected owner, customer impact, and evidence in the ticket."

    return " Knowledge source attached: use trusted internal policy and runbook guidance before taking action."


def _citation_for(document: KnowledgeDocument) -> KnowledgeCitation:
    content = _read_document(document.source_path)
    return KnowledgeCitation(
        doc_id=document.doc_id,
        title=document.title,
        source_path=document.source_path,
        section=document.section,
        owner=document.owner,
        last_reviewed=document.last_reviewed,
        excerpt=_extract_section(content, document.section),
    )


@lru_cache(maxsize=8)
def _read_document(source_path: str) -> str:
    for root in _knowledge_roots():
        candidate = root / Path(source_path).name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    return ""


def _knowledge_roots() -> list[Path]:
    file_path = Path(__file__).resolve()
    return [
        Path.cwd() / "docs" / "knowledge",
        Path.cwd().parent.parent / "docs" / "knowledge",
        file_path.parents[1] / "knowledge",
        file_path.parents[2] / "docs" / "knowledge",
    ]


def _extract_section(content: str, section: str) -> str:
    if not content:
        return "Knowledge document was registered but the Markdown file was not available at runtime."

    heading = f"## {section}"
    start = content.find(heading)
    if start == -1:
        return _compact(content)

    body = content[start + len(heading) :].strip()
    next_heading = body.find("\n## ")
    if next_heading != -1:
        body = body[:next_heading].strip()
    return _compact(body)


def _compact(value: str, limit: int = 420) -> str:
    text = " ".join(line.strip() for line in value.splitlines() if line.strip())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."
