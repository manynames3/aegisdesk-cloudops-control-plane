# Evaluations

Control-plane evaluations live in:

- `control_cases.json`
- `run_evals.py`

Current coverage:

- Secret and PII redaction
- Local routing for sensitive requests
- Production admin access denial
- Temporary read-only approval creation
- Ticket tool authorization
- Cost summary role gating

Run from the repository root after installing API dependencies:

```bash
services/api/.venv/bin/python evals/run_evals.py
```

Promptfoo or similar red-team evaluations can be added after the control suite stays stable.
