# Kubernetes Local Evaluation Evidence

**Date:** October 13, 2026

**Status:** Verified in a disposable Kind cluster on October 13, 2026. Both [Kubernetes evaluation CI](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38371577843) and [existing application CI](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38371577807) passed on source revision 6af2ddad989bd24ed802897e291fa45dc51f7359. No managed/hosted Kubernetes or customer production service is claimed.

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
| October 13, 2026 | 6af2ddad989bd24ed802897e291fa45dc51f7359 | [Successful local Kind run](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38371577843) | **Passed** | Helm lint and template, singleton failure gate, API Docker image, Kind install, OPA-backed readiness, Bound PVC, Helm upgrade |
| October 13, 2026 | 15568fe091df9d368dc13e4115c0342942a42843 | [Initial failed run](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38370732478) | **Failed** | OPA ConfigMap symlink duplicate rules blocked readiness; see incident below |


## Real failure discovered during first Kind rollout

[Initial GitHub Actions run (October 13, 2026)](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38370732478) built the image, passed Helm lint/negative-replica checks, started Kind, and loaded the image, but **failed** on Helm install readiness.

**Observed evidence:** API liveness returned HTTP 200 repeatedly, while readiness returned HTTP 503. OPA emitted rego_type_error messages for duplicate default rules in model_routing, quota, tool_authorization and approval_rules.

**Root cause:** the OPA container was passed the entire mounted /policies directory. Kubernetes ConfigMap volumes use ..data symlink generations; OPA's recursive loader walked both visible files and symlink targets, producing duplicate policy definitions.

**Fix:** pass the five explicit Rego policy filenames to OPA, rather than recursively walking the projected ConfigMap root. This does not relax AegisDesk readiness or bypass policy enforcement.

**Verification:** [Run 38371577843](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/runs/38371577843) passed Helm installation, both rollout checks, the OPA-backed API readiness call, liveness, PVC Bound assertion and release reconciliation. The first failed run remains linked as negative evidence.

## What remains outside verified scope

- There is **no managed Kubernetes deployment** (EKS/GKE/AKS), real production traffic, or cloud ingress in this exercise.
- It does not run the Next.js web app, Jaeger, or the MCP tools inside the chart.
- The API currently uses a single SQLite PVC. Scaling the pod count is rejected, not supported.
- Autoscaling, full TLS/Ingress, supply-chain attestations, network isolation, multizone availability and backup/restore testing remain outstanding.
- Local Kind smoke tests do not substitute for sustained load, chaos/recovery testing, or operational experience.

## Resume boundary

After the real Kind workflow completes successfully: Docker, Kubernetes fundamentals, Helm, deployments/services, health probes, ConfigMaps, secrets references, PVCs, rollout validation and CI smoke testing can be described as a **hands-on work sample**.

Do **not** equate local Kind with production EKS or senior Kubernetes administration. Advanced claims would require multi-replica-safe architecture, production-like networking, observability, an incident/recovery exercise and audited rollout history.
