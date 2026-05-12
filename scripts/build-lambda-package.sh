#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build/lambda"
PACKAGE="$ROOT_DIR/build/aegisdesk-api-lambda.zip"

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

(
  cd "$BUILD_DIR"
  zip -qr "$PACKAGE" .
)

printf '%s\n' "$PACKAGE"
