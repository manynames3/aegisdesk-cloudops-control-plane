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

The role switcher is a portfolio persona selector. The frontend requests a short-lived bearer token for the selected role; protected API routes still derive identity from token claims instead of trusting role fields in request bodies. In the hosted AWS deployment, those tokens are Cognito ID tokens verified through Cognito JWKS.

For the hosted reviewer flow, the sidebar `Identity` panel can prepare a Cognito Hosted UI login for `employee`, `manager`, or `admin`. The API creates or updates a disposable Cognito reviewer persona and returns the generated username and password, which the UI displays before redirecting to Hosted UI. The `Reviewer shortcut` panel is intentionally labeled for fast demos that do not need to show the Cognito redirect.

## Static Export

The hosted AWS deployment builds the web app as a static export and serves it from private S3 through CloudFront.

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com npm run build
```

The exported files are written to `apps/web/out` and should be synced to the Terraform-managed frontend bucket.
