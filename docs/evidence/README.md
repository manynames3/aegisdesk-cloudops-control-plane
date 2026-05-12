# Portfolio Evidence

These screenshots are captured from the app and are intended for recruiter and hiring-manager scanning. The hosted deployment is available at [https://d27myiy7bbj1rz.cloudfront.net](https://d27myiy7bbj1rz.cloudfront.net).

## Walkthrough

1. Open the hosted deployment or start the API and web app locally.
2. Switch to the `Admin` role and click `Seed`.
3. Open `Governance` to show audit events, cost estimates, redactions, denied actions, pending approvals, and tool calls.
4. Switch to `Employee`, open `Chat`, and run the access request prompt.
5. Switch to `Manager`, open `Approvals`, and show the pending scoped access decision.

## Screenshots

![Policy-aware chat](screenshots/policy-aware-chat.png)

![Governance dashboard](screenshots/governance-dashboard.png)

![Manager approvals](screenshots/manager-approvals.png)

## Boundary

The app does not modify real cloud resources through chat tools. The hosted portfolio environment uses low-cost AWS resources provisioned by Terraform, calls Bedrock and Cost Explorer only through policy-gated paths, and includes a $1 monthly budget guardrail.
