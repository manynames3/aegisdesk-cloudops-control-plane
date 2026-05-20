#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/services/api"
PYTHON_BIN="${AEGISDESK_API_PYTHON:-python}"

if [[ -x "$API_DIR/.venv/bin/python" && -z "${AEGISDESK_API_PYTHON:-}" ]]; then
  PYTHON_BIN="$API_DIR/.venv/bin/python"
fi

cd "$API_DIR"

export AEGISDESK_DB_PATH="${AEGISDESK_DB_PATH:-:memory:}"
export AEGISDESK_POLICY_MODE="${AEGISDESK_POLICY_MODE:-auto}"
export AEGISDESK_PERSONA_ISSUER_ENABLED="${AEGISDESK_PERSONA_ISSUER_ENABLED:-true}"
export AEGISDESK_ENABLE_BEDROCK="${AEGISDESK_ENABLE_BEDROCK:-false}"
export AEGISDESK_ENABLE_COST_EXPLORER="${AEGISDESK_ENABLE_COST_EXPLORER:-false}"

exec "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port "${AEGISDESK_API_PORT:-8000}"
