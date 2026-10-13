# AegisDesk Kubernetes Evaluation (Helm + Kind)

**Scope: reproducible local cluster work sample. Not a hosted Kubernetes deployment or production HA claim.**

The [Helm chart](aegisdesk/) deploys the existing **FastAPI API and OPA policy engine** as two Kubernetes deployments behind internal ClusterIP services. It deliberately does *not* replace the existing production-style serverless AWS Terraform deployment. Next.js, Jaeger, and MCP service remain outside this first Kubernetes slice.

## Why these services

The product already runs as API + OPA in Compose; the API depends on live OPA policy decisions. The Helm deployment reuses that real integration instead of creating a synthetic hello-world app.

This exercise demonstrates Kubernetes deployment mechanics, startup/readiness/liveness probes, ConfigMap policy injection, secret references, resource requests/limits, non-root security contexts, a SQLite PersistentVolumeClaim, rollout checks, and Helm reconciliation.

## Local prerequisites

- Docker Engine / Docker Desktop available and running
- Kind, kubectl, Helm 3 installed
- Approximately 3 GB spare memory; registry access for pinned OPA image
- The existing AegisDesk repository checked out locally

No AWS account, Bedrock API credits or hosted Kubernetes cluster is required.

## Reproducible local cluster

From the repository root:

~~~sh
kind create cluster --name aegisdesk-lab

docker build -t aegisdesk-api:kind services/api
kind load docker-image aegisdesk-api:kind --name aegisdesk-lab

kubectl create secret generic aegisdesk-auth \
  --from-literal=AEGISDESK_AUTH_SECRET=replace-with-unique-local-evaluation-secret
kubectl create configmap aegisdesk-policies --from-file=policies/

helm lint infra/helm/aegisdesk
helm upgrade --install aegisdesk infra/helm/aegisdesk \
  --set api.image.tag=kind \
  --set api.image.pullPolicy=Never \
  --wait --timeout 5m

kubectl rollout status deployment/aegisdesk-opa --timeout=180s
kubectl rollout status deployment/aegisdesk-api --timeout=180s
kubectl get pods,svc,pvc
~~~

For this local test the Secret is intentionally created out of band; **do not commit real secrets to GitHub**. The image is loaded into Kind and intentionally never pushed to a registry. The Kubernetes API service is ClusterIP, not exposed publicly.

## Confirm OPA-backed application readiness

~~~sh
kubectl port-forward service/aegisdesk-api 18000:8000
~~~

In another terminal:

~~~sh
curl -fsS http://localhost:18000/health/live
curl -fsS http://localhost:18000/health/ready
kubectl describe pod -l app.kubernetes.io/component=api
kubectl logs deployment/aegisdesk-api --tail=100
kubectl logs deployment/aegisdesk-opa --tail=100
~~~

A healthy ready response means the application sees its local SQLite store and can reach an actual OPA server. It does **not** prove live IAM/Jira/ServiceNow/Bedrock integrations. The chart disables cloud model calls.

## Troubleshooting and operational exercises

- **Readiness fails but liveness works:** inspect API logs, verify OPA pod/service, and review policy ConfigMap. The chart intentionally uses a real readiness dependency instead of always returning healthy.
- **Pod Pending:** inspect storage class and PVC binding in Kind. The API requires local writable storage.
- **CrashLoopBackOff:** inspect /app/data permissions and read-only root filesystem requirements; note that the API pod uses an fsGroup and an explicit writable /tmp.
- **Policy update:** change Rego source, replace ConfigMap, and restart the OPA deployment so mounted policy data is applied. Ensure policy tests pass.
- **Rollout/reconcile:** make a Helm values-only adjustment within bounds and run helm upgrade --install. Inspect rollout history and application readiness. Do not increase API replicas above 1.

**The chart deliberately refuses two API replicas** because SQLite on a local PersistentVolumeClaim is not a distributed database. A scalable implementation should switch the API to a multi-instance-safe store, implement migrations and concurrency tests, and then reconsider deployment topology. The current chart offers no ingress/TLS, full monitoring, strict NetworkPolicy egress, multi-zone resilience, backups, or formal disruption budgets. Do not describe it as production-ready Kubernetes.

## Inspect, rollback, and clean up

~~~sh
helm history aegisdesk
helm rollback aegisdesk 1 --wait
kubectl rollout status deployment/aegisdesk-api

# Destroys disposable work sample resources including evaluation data.
helm uninstall aegisdesk
kubectl delete secret aegisdesk-auth
kubectl delete configmap aegisdesk-policies
kubectl delete pvc aegisdesk-api-data
kind delete cluster --name aegisdesk-lab
~~~

The rollback command requires a previous revision to exist and be available; run a successful upgrade first if demonstrating rollback. **PVC data may persist after Helm uninstall**, so the explicit PVC delete is intended for this disposable lab only.

## GitHub evidence

- [Kubernetes Local Evidence workflow](https://github.com/manynames3/aegisdesk-cloudops-control-plane/actions/workflows/kubernetes-evidence.yml) executes chart validation, a Docker image build, ephemeral Kind cluster deployment, live OPA-backed readiness, PVC binding and Helm upgrade.
- [Evidence ledger](../../docs/evidence/kubernetes-local.md) tracks which checks were actually verified and what remains unproven.
- The existing [Compose path](../../compose.yaml) remains supported and independent.

**Resume-safe wording after passing Kind CI and independently reviewing the logs:** Built and verified a Helm chart for a containerized FastAPI + OPA policy service in a disposable Kind Kubernetes cluster, including health probes, resource policies, non-root workloads, PVC and automated deployment smoke tests.
