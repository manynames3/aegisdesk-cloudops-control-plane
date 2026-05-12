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

The role switcher is a demo persona selector. The frontend requests a signed local demo token for the selected role; protected API routes still derive identity from the token instead of trusting role fields in request bodies.

## Static Export

The hosted AWS demo builds the web app as a static export and serves it from private S3 through CloudFront.

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com npm run build
```

The exported files are written to `apps/web/out` and should be synced to the Terraform-managed frontend bucket.
