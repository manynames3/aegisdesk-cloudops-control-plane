# Web App

Frontend: Next.js.

Views:

- Employee cloud support chat
- Manager approval queue
- Admin governance dashboard

The frontend should make enterprise controls visible through simple UI elements:

- Model route badge
- Cost estimate
- PII/secret redaction indicators
- Policy allow/deny status
- Tool call status
- Approval status
- Audit timeline

## Local Run

```bash
npm install
npm run dev
```

By default the app expects the API at `http://localhost:8000`. Override with `NEXT_PUBLIC_API_BASE_URL`.
