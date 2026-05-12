from __future__ import annotations

import os
import sqlite3
import threading
from decimal import Decimal
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key

from .models import (
    Actor,
    ApprovalRequest,
    ApprovalStatus,
    AuditEvent,
    MetricsSummary,
    ModelRoute,
    Role,
)
from .settings import get_settings


def _quota_window() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _quota_key(actor: Actor) -> str:
    return f"{actor.role.value}#{actor.team}#{_quota_window()}"


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
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quota_counters (
                    quota_key TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    team TEXT NOT NULL,
                    window TEXT NOT NULL,
                    count INTEGER NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL,
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
        if approval.status != ApprovalStatus.pending:
            raise ValueError("approval_already_decided")

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
        cloud_model_requests = sum(1 for route in self.model_routes if route.provider in {"simulated-cloud", "bedrock"})
        redactions_total = sum(1 for event in self.events if event.event_type in {"pii.detected", "secret.detected"})
        denied_actions = sum(1 for event in self.events if event.event_type in {"policy.denied", "tool.blocked"})
        tool_calls_total = sum(1 for event in self.events if event.event_type == "tool.called")
        approvals_pending = sum(1 for approval in self.approvals if approval.status == ApprovalStatus.pending)

        return MetricsSummary(
            requests_total=sum(1 for event in self.events if event.event_type == "request.received"),
            estimated_spend_usd=round(sum(route.estimated_cost_usd for route in self.model_routes), 6),
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
            self._conn.execute("DELETE FROM quota_counters")
            self._conn.execute("DELETE FROM cache_entries")

    def ready(self) -> bool:
        try:
            self._conn.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    def quota_count(self, actor: Actor) -> int:
        row = self._conn.execute("SELECT count FROM quota_counters WHERE quota_key = ?", (_quota_key(actor),)).fetchone()
        return int(row["count"]) if row else 0

    def increment_quota(self, actor: Actor) -> int:
        key = _quota_key(actor)
        window = _quota_window()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO quota_counters (quota_key, role, team, window, count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(quota_key) DO UPDATE SET count = count + 1
                """,
                (key, actor.role.value, actor.team, window),
            )
            row = self._conn.execute("SELECT count FROM quota_counters WHERE quota_key = ?", (key,)).fetchone()
        return int(row["count"])

    def get_cache(self, key: str) -> str | None:
        now = int(datetime.now(UTC).timestamp())
        row = self._conn.execute(
            "SELECT payload, expires_at FROM cache_entries WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if not row or int(row["expires_at"]) < now:
            return None
        return str(row["payload"])

    def set_cache(self, key: str, payload: str, ttl_seconds: int) -> None:
        expires_at = int(datetime.now(UTC).timestamp()) + ttl_seconds
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries (cache_key, expires_at, payload)
                VALUES (?, ?, ?)
                """,
                (key, expires_at, payload),
            )


class DynamoStore:
    def __init__(self, table_name: str | None = None) -> None:
        settings = get_settings()
        self.table_name = table_name or settings.dynamodb_table
        if not self.table_name:
            raise ValueError("dynamodb_table_required")
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(self.table_name)

    def _query_payloads(self, pk: str) -> list[str]:
        response = self._table.query(KeyConditionExpression=Key("pk").eq(pk), ScanIndexForward=True)
        return [item["payload"] for item in response.get("Items", [])]

    @property
    def events(self) -> list[AuditEvent]:
        return [AuditEvent.model_validate_json(payload) for payload in self._query_payloads("AUDIT")]

    @property
    def approvals(self) -> list[ApprovalRequest]:
        return [ApprovalRequest.model_validate_json(payload) for payload in self._query_payloads("APPROVAL")]

    @property
    def model_routes(self) -> list[ModelRoute]:
        return [ModelRoute.model_validate_json(payload) for payload in self._query_payloads("ROUTE")]

    def add_event(self, event: AuditEvent) -> None:
        self._table.put_item(
            Item={
                "pk": "AUDIT",
                "sk": f"{event.timestamp.isoformat()}#{event.event_id}",
                "entity": "audit_event",
                "request_id": event.request_id,
                "event_type": event.event_type,
                "payload": event.model_dump_json(),
            }
        )

    def add_route(self, route: ModelRoute) -> None:
        self._table.put_item(
            Item={
                "pk": "ROUTE",
                "sk": f"{datetime.now(UTC).isoformat()}#route-{uuid4().hex[:10]}",
                "entity": "model_route",
                "provider": route.provider,
                "payload": route.model_dump_json(),
            }
        )

    def add_approval(self, approval: ApprovalRequest) -> None:
        self._save_approval(approval)

    def _save_approval(self, approval: ApprovalRequest) -> None:
        self._table.put_item(
            Item={
                "pk": "APPROVAL",
                "sk": f"{approval.created_at.isoformat()}#{approval.approval_id}",
                "approval_id": approval.approval_id,
                "entity": "approval",
                "status": approval.status.value,
                "payload": approval.model_dump_json(),
            }
        )

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        for approval in self.approvals:
            if approval.approval_id == approval_id:
                return approval
        raise KeyError(approval_id)

    def decide_approval(self, approval_id: str, actor_id: str, role: Role, approved: bool) -> ApprovalRequest:
        approval = self.get_approval(approval_id)
        if role not in {Role.manager, Role.admin}:
            raise PermissionError("approval_decision_requires_manager_or_admin")
        if approval.status != ApprovalStatus.pending:
            raise ValueError("approval_already_decided")

        approval.status = ApprovalStatus.approved if approved else ApprovalStatus.denied
        approval.decided_by = actor_id
        approval.decided_at = datetime.now(UTC)
        self._save_approval(approval)
        return approval

    def metrics(self) -> MetricsSummary:
        local_model_requests = sum(1 for route in self.model_routes if route.provider == "local")
        cloud_model_requests = sum(1 for route in self.model_routes if route.provider in {"simulated-cloud", "bedrock"})
        redactions_total = sum(1 for event in self.events if event.event_type in {"pii.detected", "secret.detected"})
        denied_actions = sum(1 for event in self.events if event.event_type in {"policy.denied", "tool.blocked", "quota.denied"})
        tool_calls_total = sum(1 for event in self.events if event.event_type == "tool.called")
        approvals_pending = sum(1 for approval in self.approvals if approval.status == ApprovalStatus.pending)

        return MetricsSummary(
            requests_total=sum(1 for event in self.events if event.event_type == "request.received"),
            estimated_spend_usd=round(sum(route.estimated_cost_usd for route in self.model_routes), 6),
            local_model_requests=local_model_requests,
            cloud_model_requests=cloud_model_requests,
            redactions_total=redactions_total,
            denied_actions=denied_actions,
            approvals_pending=approvals_pending,
            tool_calls_total=tool_calls_total,
        )

    def reset(self) -> None:
        for pk in ("AUDIT", "APPROVAL", "ROUTE", "QUOTA", "CACHE"):
            items = self._table.query(KeyConditionExpression=Key("pk").eq(pk), ProjectionExpression="pk, sk").get("Items", [])
            with self._table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    def ready(self) -> bool:
        try:
            self._table.table_status
        except Exception:
            return False
        return True

    def quota_count(self, actor: Actor) -> int:
        response = self._table.get_item(Key={"pk": "QUOTA", "sk": _quota_key(actor)})
        item = response.get("Item")
        return int(item["count"]) if item else 0

    def increment_quota(self, actor: Actor) -> int:
        response = self._table.update_item(
            Key={"pk": "QUOTA", "sk": _quota_key(actor)},
            UpdateExpression=(
                "SET #role = :role, team = :team, #window = :window "
                "ADD #count :one"
            ),
            ExpressionAttributeNames={
                "#role": "role",
                "#window": "window",
                "#count": "count",
            },
            ExpressionAttributeValues={
                ":role": actor.role.value,
                ":team": actor.team,
                ":window": _quota_window(),
                ":one": Decimal(1),
            },
            ReturnValues="UPDATED_NEW",
        )
        return int(response["Attributes"]["count"])

    def get_cache(self, key: str) -> str | None:
        response = self._table.get_item(Key={"pk": "CACHE", "sk": key})
        item = response.get("Item")
        now = int(datetime.now(UTC).timestamp())
        if not item or int(item.get("expires_at", 0)) < now:
            return None
        return str(item["payload"])

    def set_cache(self, key: str, payload: str, ttl_seconds: int) -> None:
        expires_at = int(datetime.now(UTC).timestamp()) + ttl_seconds
        self._table.put_item(
            Item={
                "pk": "CACHE",
                "sk": key,
                "entity": "cache_entry",
                "expires_at": Decimal(expires_at),
                "payload": payload,
            }
        )


def create_store():
    settings = get_settings()
    if settings.store_backend == "dynamodb":
        return DynamoStore(settings.dynamodb_table)
    return DemoStore()


def actor_from(user_id: str, role: Role, team: str) -> Actor:
    return Actor(user_id=user_id, role=role, team=team)
