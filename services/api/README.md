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

## Current Boundary

The API uses in-memory demo state and deterministic mock tools. It does not call paid model providers or modify real cloud resources.
