# Kubernetes Local Evaluation Evidence

**Date:** October 13, 2026

**Status:** Kubernetes chart and disposable cluster CI implemented on a feature branch. The linked workflow run must be inspected before upgrading verification status. No hosted production cluster is claimed.

## Reproducible sources

| Evidence item | Source | What it proves if the CI step is green |
| --- | --- | --- |
| Helm chart with API + OPA manifests | [Chart files](../../infra/helm/aegisdesk/) | Kubernetes deployment intent and chart templates |
| Chart sanity + singleton failure guard | [Kubernetes workflow](../../.github/workflows/kubernetes-evidence.yml) | Chart renders and refuses unsafe SQLite scale-out |
| Container build | Same workflow | Existing API Dockerfile builds a runnable image |
| Local Kind deployment | Same workflow | Kubernetes API/OPA pods are scheduled and Helm install completes |
| Application health with real OPA | Same workflow | API live/readiness endpoints pass with live policy server |
| PVC binding and Helm reconciliation | Same workflow | Evaluation storage is bound and Helm upgrade completes |
| Runbook and limits | [Helm operator guide](../../infra/helm/README.md) | Clear reproduction, rollback, teardown and known limitations |

## CI artifact location

[**GitHub Actions: Kubernetes Local Evidence**](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/kubernetes-evidence.yml)

To review: select the commit and verify the steps that check Kind deployment, readiness, SQLite PVC Bound state and second Helm upgrade. Record the exact successful run URL and commit SHA in this ledger after confirming actual status. Failing/skipped checks do not count.

| Date | Commit SHA | Run URL | Result | Notes |
| --- | --- | --- | --- | --- |
| Not yet recorded | Pending review | Pending | Unverified at authoring | No manual claim made |


## Real failure discovered during first Kind rollout

[Initial GitHub Actions run (October 13, 2026)](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38370732478) built the image, passed Helm lint/negative-replica checks, started Kind, and loaded the image, but **failed** on Helm install readiness.

**Observed evidence:** API liveness returned HTTP 200 repeatedly, while readiness returned HTTP 503. OPA emitted rego_type_error messages for duplicate default rules in model_routing, quota, tool_authorization and approval_rules.

**Root cause:** the OPA container was passed the entire mounted /policies directory. Kubernetes ConfigMap volumes use ..data symlink generations; OPA's recursive loader walked both visible files and symlink targets, producing duplicate policy definitions.

**Fix:** pass the five explicit Rego policy filenames to OPA, rather than recursively walking the projected ConfigMap root. This does not relax AegisDesk readiness or bypass policy enforcement.

**Verification:** this change requires a new completed Kind run proving both API and OPA are ready. Do not mark it resolved from a source diff alone. The first failed run stays linked as negative evidence for the troubleshooting record.

## What remains outside verified scope

- There is **no managed Kubernetes deployment** (EKS/GKE/AKS), real production traffic, or cloud ingress in this exercise.
- It does not run the Next.js web app, Jaeger, or the MCP tools inside the chart.
- The API currently uses a single SQLite PVC. Scaling the pod count is rejected, not supported.
- Autoscaling, full TLS/Ingress, supply-chain attestations, network isolation, multizone availability and backup/restore testing remain outstanding.
- Local Kind smoke tests do not substitute for sustained load, chaos/recovery testing, or operational experience.

## Resume boundary

After the real Kind workflow completes successfully: Docker, Kubernetes fundamentals, Helm, deployments/services, health probes, ConfigMaps, secrets references, PVCs, rollout validation and CI smoke testing can be described as a **hands-on work sample**.

Do **not** equate local Kind with production EKS or senior Kubernetes administration. Advanced claims would require multi-replica-safe architecture, production-like networking, observability, an incident/recovery exercise and audited rollout history.
