# Docker Runtime

Planned local services in the root `compose.yaml`:

- Web frontend
- FastAPI gateway
- OPA
- Jaeger

Goal:

Run the full app locally without required cloud spend.

Current note:

Docker is not required for the direct local development path. Use Docker Compose when Docker is available:

```bash
docker compose up --build
```

The current FastAPI implementation uses local control behavior and does not require a paid model provider.
