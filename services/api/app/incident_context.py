from __future__ import annotations

from .models import IncidentContext, IncidentLogEntry


INCIDENT_LOGS: dict[str, list[IncidentLogEntry]] = {
    "INC-1042": [
        IncidentLogEntry(
            timestamp="2026-05-12T21:14:02Z",
            level="WARN",
            service="checkout-api",
            message="p95 latency breached 2.8s threshold for POST /checkout.",
        ),
        IncidentLogEntry(
            timestamp="2026-05-12T21:15:31Z",
            level="ERROR",
            service="checkout-api",
            message="database connection pool exhausted while reserving inventory.",
        ),
        IncidentLogEntry(
            timestamp="2026-05-12T21:16:08Z",
            level="WARN",
            service="payments-worker",
            message="upstream payment authorization latency increased to 1.9s.",
        ),
        IncidentLogEntry(
            timestamp="2026-05-12T21:18:47Z",
            level="INFO",
            service="deploy-controller",
            message="release checkout-api 2026.05.12.3 completed 12 minutes before alert.",
        ),
    ]
}


def lookup_incident_context(incident_id: str | None, query: str) -> IncidentContext:
    resolved_incident_id = incident_id or "INC-1042"
    entries = INCIDENT_LOGS.get(resolved_incident_id, INCIDENT_LOGS["INC-1042"])
    cloudwatch_query = (
        "fields @timestamp, @message, service, level "
        f"| filter incident_id = '{resolved_incident_id}' "
        "| sort @timestamp desc | limit 20"
    )
    return IncidentContext(
        incident_id=resolved_incident_id,
        source="seeded_cloudwatch_logs",
        log_group="/aws/lambda/aegisdesk/checkout",
        query=cloudwatch_query,
        entries=entries,
        suspected_cause=_suspected_cause(entries, query),
    )


def _suspected_cause(entries: list[IncidentLogEntry], query: str) -> str:
    text = " ".join([query, *[entry.message for entry in entries]]).lower()
    if "connection pool" in text:
        return "Database connection pool saturation is the strongest signal."
    if "payment" in text or "upstream" in text:
        return "Upstream payment latency is likely contributing to checkout timeouts."
    if "release" in text or "deploy" in text:
        return "Recent deployment timing should be checked before deeper debugging."
    return "Recent log patterns should be compared with deployment and dependency health."
