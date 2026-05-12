# API Service

Backend: FastAPI + Pydantic.

Responsibilities:

- Validate chat and action requests
- Detect PII and secrets
- Evaluate OPA policies
- Route to local fallback or Amazon Bedrock
- Gate MCP tool calls
- Query AWS Cost Explorer for authorized cost investigations
- Create audit events
- Emit OpenTelemetry traces

Implemented endpoints:

- `POST /auth/persona-token`
- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `POST /chat`
- `GET /events`
- `GET /approvals`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/deny`
- `GET /metrics/summary`
- `POST /admin/reset`
- `POST /admin/seed`

## Local Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Direct local runs default to `AEGISDESK_POLICY_MODE=auto`, which uses OPA when `OPA_URL` is set and falls back to the mirrored Python policy evaluator when OPA is not configured. Docker Compose sets `AEGISDESK_POLICY_MODE=opa`.

Local runs default to SQLite storage, local persona tokens, and deterministic model fallback. The hosted Terraform path sets DynamoDB storage, Cognito/JWKS token verification, OPA subprocess policy evaluation, Bedrock Nova Lite routing, and Cost Explorer summaries with DynamoDB caching.

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

By default, the API writes audit events, approvals, and model routes to SQLite at `data/aegisdesk.db` relative to the process working directory. Override with:

```bash
AEGISDESK_DB_PATH=:memory:
```

## Current Boundary

The API uses deterministic ticket/access tools and does not modify real cloud resources through chat actions. The hosted path can call Amazon Bedrock for approved low-sensitivity prompts and AWS Cost Explorer for manager/admin cost summaries.

The `/auth/persona-token` endpoint is a portfolio persona issuer. In hosted mode it uses Cognito Admin APIs to issue Cognito ID tokens verified through Cognito JWKS. Production identity should federate a corporate identity provider such as Entra ID or Okta instead of using reviewer personas.
