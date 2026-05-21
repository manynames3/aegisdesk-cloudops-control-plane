from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    persona_issuer_enabled: bool
    auth_secret: str
    auth_mode: str
    jwks_private_key_pem: str | None
    jwks_public_key_pem: str | None
    jwks_key_id: str
    jwt_issuer: str
    jwt_audience: str | None
    cognito_user_pool_id: str | None
    cognito_client_id: str | None
    cognito_hosted_ui_domain: str | None
    cognito_region: str
    persona_auth_enabled: bool
    persona_password_seed: str
    policy_mode: str
    opa_url: str | None
    opa_executable_path: str
    opa_policy_path: str
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
    max_request_chars: int
    cloud_model_kill_switch: bool
    api_throttling_rate_limit: float
    api_throttling_burst_limit: int
    enable_cost_explorer: bool
    cost_cache_ttl_seconds: int
    cost_explorer_scope: str
    cost_explorer_tag_key: str
    cost_explorer_tag_value: str
    ticket_adapter: str
    jira_base_url: str | None
    jira_email: str | None
    jira_api_token: str | None
    jira_project_key: str | None
    jira_issue_type: str
    jira_timeout_seconds: float
    servicenow_instance_url: str | None
    servicenow_username: str | None
    servicenow_password: str | None
    servicenow_assignment_group: str | None
    servicenow_table: str
    servicenow_timeout_seconds: float
    incident_context_adapter: str
    cloudwatch_log_group: str | None
    cloudwatch_logs_region: str
    cloudwatch_query_lookback_minutes: int
    cloudwatch_query_limit: int
    cloudwatch_query_poll_attempts: int
    cloudwatch_query_poll_interval_seconds: float
    audit_retention_days: int
    audit_export_max_events: int
    data_boundary_mode: str
    cors_origins: list[str]


def get_settings() -> Settings:
    persona_issuer_enabled = _env_bool("AEGISDESK_PERSONA_ISSUER_ENABLED", _env_bool("DEMO_MODE", True))
    return Settings(
        persona_issuer_enabled=persona_issuer_enabled,
        auth_secret=os.getenv("AEGISDESK_AUTH_SECRET", "local-control-plane-secret-change-me"),
        auth_mode=os.getenv("AEGISDESK_AUTH_MODE", "hmac").lower(),
        jwks_private_key_pem=os.getenv("AEGISDESK_JWKS_PRIVATE_KEY_PEM"),
        jwks_public_key_pem=os.getenv("AEGISDESK_JWKS_PUBLIC_KEY_PEM"),
        jwks_key_id=os.getenv("AEGISDESK_JWKS_KEY_ID", "aegisdesk-local-rs256"),
        jwt_issuer=os.getenv("AEGISDESK_JWT_ISSUER", "aegisdesk-local"),
        jwt_audience=os.getenv("AEGISDESK_JWT_AUDIENCE"),
        cognito_user_pool_id=os.getenv("AEGISDESK_COGNITO_USER_POOL_ID"),
        cognito_client_id=os.getenv("AEGISDESK_COGNITO_CLIENT_ID"),
        cognito_hosted_ui_domain=os.getenv("AEGISDESK_COGNITO_HOSTED_UI_DOMAIN"),
        cognito_region=os.getenv("AEGISDESK_COGNITO_REGION", os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))),
        persona_auth_enabled=_env_bool("AEGISDESK_PERSONA_AUTH_ENABLED", True),
        persona_password_seed=os.getenv("AEGISDESK_PERSONA_PASSWORD_SEED", "local-persona-seed-change-me"),
        policy_mode=os.getenv("AEGISDESK_POLICY_MODE", "auto").lower(),
        opa_url=os.getenv("OPA_URL"),
        opa_executable_path=os.getenv("AEGISDESK_OPA_EXECUTABLE", str(Path.cwd() / "bin" / "opa")),
        opa_policy_path=os.getenv("AEGISDESK_OPA_POLICY_PATH", str(Path.cwd() / "policies")),
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
        max_request_chars=int(os.getenv("AEGISDESK_MAX_REQUEST_CHARS", "2000")),
        cloud_model_kill_switch=_env_bool("AEGISDESK_CLOUD_MODEL_KILL_SWITCH", False),
        api_throttling_rate_limit=float(os.getenv("AEGISDESK_API_THROTTLE_RATE_LIMIT", "5")),
        api_throttling_burst_limit=int(os.getenv("AEGISDESK_API_THROTTLE_BURST_LIMIT", "20")),
        enable_cost_explorer=_env_bool("AEGISDESK_ENABLE_COST_EXPLORER", False),
        cost_cache_ttl_seconds=int(os.getenv("AEGISDESK_COST_CACHE_TTL_SECONDS", "21600")),
        cost_explorer_scope=os.getenv("AEGISDESK_COST_EXPLORER_SCOPE", "tagged").lower(),
        cost_explorer_tag_key=os.getenv("AEGISDESK_COST_EXPLORER_TAG_KEY", "Project"),
        cost_explorer_tag_value=os.getenv("AEGISDESK_COST_EXPLORER_TAG_VALUE", "AegisDesk"),
        ticket_adapter=os.getenv("AEGISDESK_TICKET_ADAPTER", "local").lower(),
        jira_base_url=os.getenv("AEGISDESK_JIRA_BASE_URL"),
        jira_email=os.getenv("AEGISDESK_JIRA_EMAIL"),
        jira_api_token=os.getenv("AEGISDESK_JIRA_API_TOKEN"),
        jira_project_key=os.getenv("AEGISDESK_JIRA_PROJECT_KEY"),
        jira_issue_type=os.getenv("AEGISDESK_JIRA_ISSUE_TYPE", "Task"),
        jira_timeout_seconds=float(os.getenv("AEGISDESK_JIRA_TIMEOUT_SECONDS", "8")),
        servicenow_instance_url=os.getenv("AEGISDESK_SERVICENOW_INSTANCE_URL"),
        servicenow_username=os.getenv("AEGISDESK_SERVICENOW_USERNAME"),
        servicenow_password=os.getenv("AEGISDESK_SERVICENOW_PASSWORD"),
        servicenow_assignment_group=os.getenv("AEGISDESK_SERVICENOW_ASSIGNMENT_GROUP"),
        servicenow_table=os.getenv("AEGISDESK_SERVICENOW_TABLE", "incident"),
        servicenow_timeout_seconds=float(os.getenv("AEGISDESK_SERVICENOW_TIMEOUT_SECONDS", "8")),
        incident_context_adapter=os.getenv("AEGISDESK_INCIDENT_CONTEXT_ADAPTER", "local_fixture").lower(),
        cloudwatch_log_group=os.getenv("AEGISDESK_CLOUDWATCH_LOG_GROUP"),
        cloudwatch_logs_region=os.getenv(
            "AEGISDESK_CLOUDWATCH_LOGS_REGION",
            os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        ),
        cloudwatch_query_lookback_minutes=int(os.getenv("AEGISDESK_CLOUDWATCH_QUERY_LOOKBACK_MINUTES", "60")),
        cloudwatch_query_limit=int(os.getenv("AEGISDESK_CLOUDWATCH_QUERY_LIMIT", "20")),
        cloudwatch_query_poll_attempts=int(os.getenv("AEGISDESK_CLOUDWATCH_QUERY_POLL_ATTEMPTS", "6")),
        cloudwatch_query_poll_interval_seconds=float(os.getenv("AEGISDESK_CLOUDWATCH_QUERY_POLL_INTERVAL_SECONDS", "0.5")),
        audit_retention_days=int(os.getenv("AEGISDESK_AUDIT_RETENTION_DAYS", "30")),
        audit_export_max_events=int(os.getenv("AEGISDESK_AUDIT_EXPORT_MAX_EVENTS", "500")),
        data_boundary_mode=os.getenv("AEGISDESK_DATA_BOUNDARY_MODE", "evaluation").lower(),
        cors_origins=[
            origin.strip()
            for origin in os.getenv(
                "AEGISDESK_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    )
