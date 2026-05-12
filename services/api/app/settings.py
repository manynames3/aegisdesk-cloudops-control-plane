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
    auth_mode: str
    jwks_private_key_pem: str | None
    jwks_public_key_pem: str | None
    jwks_key_id: str
    jwt_issuer: str
    jwt_audience: str | None
    policy_mode: str
    opa_url: str | None
    opa_timeout_seconds: float
    service_name: str
    otlp_endpoint: str | None
    store_backend: str
    dynamodb_table: str | None
    aws_region: str
    enable_bedrock: bool
    bedrock_model_id: str
    bedrock_max_tokens: int
    bedrock_timeout_seconds: float
    bedrock_input_price_per_1m_tokens: float
    bedrock_output_price_per_1m_tokens: float
    quota_window_seconds: int
    cors_origins: list[str]


def get_settings() -> Settings:
    demo_mode = _env_bool("DEMO_MODE", True)
    return Settings(
        demo_mode=demo_mode,
        auth_secret=os.getenv("AEGISDESK_AUTH_SECRET", "local-demo-secret-change-me"),
        auth_mode=os.getenv("AEGISDESK_AUTH_MODE", "hmac").lower(),
        jwks_private_key_pem=os.getenv("AEGISDESK_JWKS_PRIVATE_KEY_PEM"),
        jwks_public_key_pem=os.getenv("AEGISDESK_JWKS_PUBLIC_KEY_PEM"),
        jwks_key_id=os.getenv("AEGISDESK_JWKS_KEY_ID", "aegisdesk-demo-rs256"),
        jwt_issuer=os.getenv("AEGISDESK_JWT_ISSUER", "aegisdesk-local-demo"),
        jwt_audience=os.getenv("AEGISDESK_JWT_AUDIENCE"),
        policy_mode=os.getenv("AEGISDESK_POLICY_MODE", "auto").lower(),
        opa_url=os.getenv("OPA_URL"),
        opa_timeout_seconds=float(os.getenv("AEGISDESK_OPA_TIMEOUT_SECONDS", "0.75")),
        service_name=os.getenv("OTEL_SERVICE_NAME", "aegisdesk-api"),
        otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        store_backend=os.getenv("AEGISDESK_STORE_BACKEND", "sqlite").lower(),
        dynamodb_table=os.getenv("AEGISDESK_DYNAMODB_TABLE"),
        aws_region=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        enable_bedrock=_env_bool("AEGISDESK_ENABLE_BEDROCK", False),
        bedrock_model_id=os.getenv("AEGISDESK_BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
        bedrock_max_tokens=int(os.getenv("AEGISDESK_BEDROCK_MAX_TOKENS", "180")),
        bedrock_timeout_seconds=float(os.getenv("AEGISDESK_BEDROCK_TIMEOUT_SECONDS", "8")),
        bedrock_input_price_per_1m_tokens=float(os.getenv("AEGISDESK_BEDROCK_INPUT_PRICE_PER_1M_TOKENS", "0.06")),
        bedrock_output_price_per_1m_tokens=float(os.getenv("AEGISDESK_BEDROCK_OUTPUT_PRICE_PER_1M_TOKENS", "0.24")),
        quota_window_seconds=int(os.getenv("AEGISDESK_QUOTA_WINDOW_SECONDS", "86400")),
        cors_origins=[
            origin.strip()
            for origin in os.getenv(
                "AEGISDESK_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    )
