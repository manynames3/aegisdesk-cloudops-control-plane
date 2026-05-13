#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_DIR="$ROOT_DIR/services/mcp-tools"
PYTHON="$MCP_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$MCP_DIR/.venv" >&2
  "$PYTHON" -m pip install --upgrade pip >&2
  "$PYTHON" -m pip install -r "$MCP_DIR/requirements.txt" >&2
fi

exec "$PYTHON" "$ROOT_DIR/scripts/smoke-mcp-tools.py"
