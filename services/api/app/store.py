from __future__ import annotations

import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .models import (
    Actor,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    MetricsSummary,
    ModelRoute,
    Role,
)


class DemoStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("AEGISDESK_DB_PATH", "data/aegisdesk.db")
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_routes (
                    route_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    @property
    def events(self) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT payload FROM audit_events ORDER BY timestamp ASC, event_id ASC"
        ).fetchall()
        return [AuditEvent.model_validate_json(row["payload"]) for row in rows]

    @property
    def approvals(self) -> list[ApprovalRequest]:
        rows = self._conn.execute("SELECT payload FROM approvals ORDER BY created_at ASC").fetchall()
        return [ApprovalRequest.model_validate_json(row["payload"]) for row in rows]

    @property
    def model_routes(self) -> list[ModelRoute]:
        rows = self._conn.execute("SELECT payload FROM model_routes ORDER BY rowid ASC").fetchall()
        return [ModelRoute.model_validate_json(row["payload"]) for row in rows]

    def add_event(self, event: AuditEvent) -> None:
        payload = event.model_dump_json()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO audit_events (event_id, request_id, event_type, timestamp, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event.event_id, event.request_id, event.event_type, event.timestamp.isoformat(), payload),
            )

    def add_route(self, route: ModelRoute) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO model_routes (route_id, provider, payload)
                VALUES (?, ?, ?)
                """,
                (f"route-{uuid4().hex[:10]}", route.provider, route.model_dump_json()),
            )

    def add_approval(self, approval: ApprovalRequest) -> None:
        self._save_approval(approval)

    def _save_approval(self, approval: ApprovalRequest) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO approvals (approval_id, status, created_at, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    approval.approval_id,
                    approval.status.value,
                    approval.created_at.isoformat(),
                    approval.model_dump_json(),
                ),
            )

    def decide_approval(self, approval_id: str, actor_id: str, role: Role, approved: bool) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if role not in {Role.manager, Role.admin}:
            raise PermissionError("approval_decision_requires_manager_or_admin")

        approval.status = ApprovalStatus.approved if approved else ApprovalStatus.denied
        approval.decided_by = actor_id
        approval.decided_at = datetime.now(UTC)
        self._save_approval(approval)
        return approval

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        for approval in self.approvals:
            if approval.approval_id == approval_id:
                return approval
        raise KeyError(approval_id)

    def metrics(self) -> MetricsSummary:
        local_model_requests = sum(1 for route in self.model_routes if route.provider == "local")
        cloud_model_requests = sum(1 for route in self.model_routes if route.provider == "simulated-cloud")
        redactions_total = sum(1 for event in self.events if event.event_type in {"pii.detected", "secret.detected"})
        denied_actions = sum(1 for event in self.events if event.event_type in {"policy.denied", "tool.blocked"})
        tool_calls_total = sum(1 for event in self.events if event.event_type == "tool.called")
        approvals_pending = sum(1 for approval in self.approvals if approval.status == ApprovalStatus.pending)

        return MetricsSummary(
            requests_total=sum(1 for event in self.events if event.event_type == "request.received"),
            estimated_spend_usd=round(sum(route.estimated_cost_usd for route in self.model_routes), 4),
            local_model_requests=local_model_requests,
            cloud_model_requests=cloud_model_requests,
            redactions_total=redactions_total,
            denied_actions=denied_actions,
            approvals_pending=approvals_pending,
            tool_calls_total=tool_calls_total,
        )

    def reset(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM audit_events")
            self._conn.execute("DELETE FROM approvals")
            self._conn.execute("DELETE FROM model_routes")


def actor_from(user_id: str, role: Role, team: str) -> Actor:
    return Actor(user_id=user_id, role=role, team=team)
