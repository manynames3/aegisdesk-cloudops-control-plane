# Known Limitations

This page is intentionally explicit so buyers and technical reviewers can tell what is production-style today and what still needs customer hardening.

| Area | Current limitation | Recommended next step |
| --- | --- | --- |
| Identity | Hosted path uses Cognito personas for evaluation | Federate Cognito to the customer's Okta or Entra tenant and disable persona issuance |
| Ticketing | Jira and ServiceNow adapters are implemented with contract tests, but no public sandbox credentials are committed | Run live sandbox validation during customer setup |
| Incident context | CloudWatch adapter is implemented; Datadog remains an interface boundary | Connect one real customer log group for the main pilot |
| Access requests | Local approval workflow is implemented; Okta/IAM Identity Center are adapter boundaries | Connect the customer's access request system after policy review |
| Redaction | Pattern-based redaction can miss unusual secrets or business-sensitive text | Add customer-specific detectors and blocklists |
| Payments | No billing or license enforcement is implemented | Use a paid pilot agreement before building in-app billing |
| Scale | Serverless shape is suitable for pilot and small internal rollout | Add load testing and table/index review before broad enterprise rollout |
| Compliance | Security packet exists but no third-party certification is claimed | Run customer security review and add evidence exports to SIEM/S3 |
