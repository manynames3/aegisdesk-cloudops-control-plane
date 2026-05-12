# API Service

Backend: FastAPI + Pydantic.

Responsibilities:

- Validate chat and action requests
- Detect PII and secrets
- Evaluate OPA policies
- Route to local fallback or Amazon Bedrock
- Gate MCP tool calls
- Create audit events
- Emit OpenTelemetry traces

Implemented endpoints:

- `POST /auth/demo-token`
- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `POST /chat`
- `GET /events`
- `GET /approvals`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/deny`
- `GET /metrics/summary`
- `POST /demo/reset`
- `POST /demo/seed`

## Local Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Direct local runs default to `AEGISDESK_POLICY_MODE=auto`, which uses OPA when `OPA_URL` is set and falls back to the mirrored Python policy evaluator when OPA is not configured. Docker Compose sets `AEGISDESK_POLICY_MODE=opa`.

Local runs default to SQLite storage, HMAC demo tokens, and deterministic model fallback. The hosted Terraform path sets DynamoDB storage, JWKS token verification, and Bedrock Nova Lite routing.

## Lambda Package

The hosted portfolio API uses `app/lambda_handler.py` with Mangum to adapt FastAPI to AWS Lambda.

From the repository root:

```bash
scripts/build-lambda-package.sh
```

Terraform reads the generated `build/aegisdesk-api-lambda.zip`.

## Tests

```bash
.venv/bin/pytest tests
```

## Local Persistence

By default, the API writes demo audit events, approvals, and model routes to SQLite at `data/aegisdesk.db` relative to the process working directory. Override with:

```bash
AEGISDESK_DB_PATH=:memory:
```

## Current Boundary

The API uses deterministic mock tools. It does not call paid model providers or modify real cloud resources through chat actions.

The `/auth/demo-token` endpoint is a portfolio demo issuer. In hosted mode it issues RS256 tokens verified through `/.well-known/jwks.json`. Production identity should use OIDC/JWT verification from a real identity provider such as Cognito, Entra ID, or Okta.
