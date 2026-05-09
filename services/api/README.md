# API Service Placeholder

Planned backend: FastAPI + Pydantic.

Responsibilities:

- Validate chat and action requests
- Detect PII and secrets
- Evaluate OPA policies
- Route to local or cloud models
- Gate MCP tool calls
- Create audit events
- Emit OpenTelemetry traces

Planned endpoints:

- `POST /chat`
- `GET /events`
- `GET /approvals`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/deny`
- `GET /metrics/summary`

