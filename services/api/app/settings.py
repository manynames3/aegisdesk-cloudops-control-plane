from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo_mode: bool
    auth_secret: str
    policy_mode: str
    opa_url: str | None
    opa_timeout_seconds: float
    service_name: str
    otlp_endpoint: str | None


def get_settings() -> Settings:
    demo_mode = _env_bool("DEMO_MODE", True)
    return Settings(
        demo_mode=demo_mode,
        auth_secret=os.getenv("AEGISDESK_AUTH_SECRET", "local-demo-secret-change-me"),
        policy_mode=os.getenv("AEGISDESK_POLICY_MODE", "auto").lower(),
        opa_url=os.getenv("OPA_URL"),
        opa_timeout_seconds=float(os.getenv("AEGISDESK_OPA_TIMEOUT_SECONDS", "0.75")),
        service_name=os.getenv("OTEL_SERVICE_NAME", "aegisdesk-api"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
    )
