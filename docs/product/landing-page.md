# Landing Page Explanation

The AegisDesk landing page is the public product explanation for the self-hosted CloudOps AI control plane.

Live page: [https://d27myiy7bbj1rz.cloudfront.net/marketing](https://d27myiy7bbj1rz.cloudfront.net/marketing)

## Purpose

The landing page is designed for a buyer or technical reviewer who needs to understand the product before opening the control plane. It explains the business problem, shows the working UI, and connects the product value to identity, policy, redaction, model routing, approval workflows, integrations, and audit trails.

The page is intentionally separate from the app UI. The app is where operators submit CloudOps requests and reviewers inspect governance evidence. The landing page is where stakeholders quickly understand why the product exists and what kind of control plane it provides.

## Target Audience

- **Platform leaders** evaluating AI enablement for CloudOps teams.
- **Security and governance reviewers** checking whether AI requests are controlled before models or tools run.
- **FinOps stakeholders** looking for cost-aware model routing and cloud spend controls.
- **ITSM owners** evaluating how AI requests can connect to ticketing and approval systems.
- **Technical reviewers** validating that the product has a coherent architecture rather than a standalone chatbot.

## Message

The core message is:

> Give employees AI help for incidents, tickets, access requests, and cloud cost questions while enforcing identity, policy, redaction, approval, model routing, and audit trails.

This keeps the page focused on the control layer around employee-facing AI. The product is not positioned as a generic assistant. It is positioned as a governed CloudOps entry point that lets employees move faster while platform, security, and FinOps teams keep evidence and control.

## Page Structure

| Section | Purpose |
| --- | --- |
| Hero | States the product category and primary promise in plain English. |
| Product screenshot | Shows the actual control plane above the fold so the page is product-led. |
| Capability pills | Highlights the four credibility anchors: Cognito identity, OPA/Rego policy, Bedrock routing, and DynamoDB audit. |
| Problem | Explains why unmanaged AI is risky in CloudOps workflows. |
| Product surfaces | Shows chat, governance, and approval views. |
| Use cases | Covers incident triage, production access, and cloud cost review. |
| Architecture | Explains the request path from identity through audit storage. |
| Security posture | Summarizes identity, redaction, model controls, and request replay. |
| Integrations | Lists systems the control plane can connect to through adapters or implemented paths. |
| Final CTA | Directs reviewers into the working control plane. |

## Visual Direction

The visual style is intentionally quiet and enterprise-oriented:

- White or near-white background.
- Large, confident headline.
- Minimal top navigation.
- Generous spacing.
- Product screenshots instead of abstract illustrations.
- Subtle borders and soft shadows.
- Restrained teal and warm neutral accents.
- Plain-English section labels.

This direction supports the product story. A CloudOps control plane should feel clear, trustworthy, and operational rather than decorative or campaign-heavy.

## Product Evidence

The hero screenshot is captured from the hosted control plane and shows:

- Self-hosted control plane labeling.
- Policy-aware chat workflow.
- Decision trail.
- Trusted source score.
- Answer sources.
- Local control and OPA/Rego policy evidence.
- Incident context and runbook citations.

Additional screenshots live in [Product Evidence](../evidence/README.md).

## Implementation

The route is implemented in:

- `apps/web/app/marketing/page.tsx`
- `apps/web/app/globals.css`
- `apps/web/public/screenshots/`

The page is statically exported by the Next.js build and served through the same S3 and CloudFront frontend deployment as the control plane.

## Maintenance Checklist

Before publishing landing page changes:

1. Keep claims aligned with implemented or explicitly documented capabilities.
2. Refresh screenshots when product labels, workflows, or UI states change.
3. Verify desktop and mobile screenshots.
4. Run `npm run build:web`.
5. Run `git diff --check`.
6. Publish static assets to S3.
7. Copy `apps/web/out/marketing.html` to the extensionless `/marketing` object.
8. Invalidate CloudFront.

## Review Path

A concise reviewer path is:

1. Open the [landing page](https://d27myiy7bbj1rz.cloudfront.net/marketing).
2. Confirm the value proposition and architecture sections.
3. Click `Open control plane`.
4. Use `Identity shortcut` or Cognito Hosted UI.
5. Run the incident, secret, access, and cost prompts.
6. Open `Governance` and inspect request replay.
7. Open `Approvals` as manager to review scoped access flow.

