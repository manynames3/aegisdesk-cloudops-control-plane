#!/usr/bin/env bash
set -euo pipefail

python3 scripts/secret-scan.py

if [ -d apps/web/node_modules ]; then
  npm --prefix apps/web audit --audit-level=critical
else
  echo "Skipping npm audit: apps/web/node_modules is not installed."
fi

if [ -x services/api/.venv/bin/python ]; then
  services/api/.venv/bin/python -m pip check
else
  echo "Skipping API pip check: services/api/.venv is not installed."
fi

if [ -x services/mcp-tools/.venv/bin/python ]; then
  services/mcp-tools/.venv/bin/python -m pip check
else
  echo "Skipping MCP pip check: services/mcp-tools/.venv is not installed."
fi
