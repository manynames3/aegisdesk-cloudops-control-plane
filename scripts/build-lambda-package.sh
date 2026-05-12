#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/lambda"
PACKAGE="$ROOT_DIR/build/aegisdesk-api-lambda.zip"
OPA_VERSION="${OPA_VERSION:-1.16.1}"
OPA_DOWNLOAD_URL="${OPA_DOWNLOAD_URL:-https://openpolicyagent.org/downloads/v${OPA_VERSION}/opa_linux_amd64_static}"

rm -rf "$BUILD_DIR" "$PACKAGE"
mkdir -p "$BUILD_DIR"

python3 -m pip install \
  --requirement "$ROOT_DIR/services/api/requirements-lambda.txt" \
  --target "$BUILD_DIR" \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --upgrade

cp -R "$ROOT_DIR/services/api/app" "$BUILD_DIR/app"
cp -R "$ROOT_DIR/policies" "$BUILD_DIR/policies"
cp -R "$ROOT_DIR/docs/knowledge" "$BUILD_DIR/knowledge"
mkdir -p "$BUILD_DIR/bin"
curl -fsSL -o "$BUILD_DIR/bin/opa" "$OPA_DOWNLOAD_URL"
chmod 755 "$BUILD_DIR/bin/opa"

(
  cd "$BUILD_DIR"
  zip -qr "$PACKAGE" .
)

printf '%s\n' "$PACKAGE"
