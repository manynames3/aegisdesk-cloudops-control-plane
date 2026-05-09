# API Service

Backend: FastAPI + Pydantic.

Responsibilities:

- Validate chat and action requests
- Detect PII and secrets
- Evaluate OPA policies
- Route to local or cloud models
- Gate MCP tool calls
- Create audit events
- Emit OpenTelemetry traces

Implemented endpoints:

- `GET /health`
- `POST /chat`
- `GET /events`
- `GET /approvals`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/deny`
- `GET /metrics/summary`
- `POST /demo/reset`

## Local Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

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

The API uses deterministic mock tools. It does not call paid model providers or modify real cloud resources.
