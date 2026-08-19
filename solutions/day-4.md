# Day 4 reference solution

## Observability

Deploy the Day 4 stage only after the managed Prometheus CRDs exist:

```powershell
./scripts/deploy-workload.ps1 -Target azure -Environment standard -Stage day4
kubectl get podmonitor -n orders
```

Useful signals:

- `rate(storefront_requests_total[5m])`
- `rate(orders_api_errors_total[5m])`
- `histogram_quantile` only if a histogram is instrumented; the sample app does not fake one.
- Kubernetes readiness/restart metrics, container CPU/memory, pending pods, and node conditions.

The app exposes no latency histogram, so use load-generator measurements or add proper instrumentation rather than relabeling another metric as p95.

## Scaling sequence

```powershell
kubectl set env deployment/storefront -n orders CPU_BURN_MS=25
kubectl apply -f platform/components/scaling/hpa.yaml
python app/loadgen/load.py <gateway-url> --requests 2000 --concurrency 50
kubectl describe hpa storefront -n orders
kubectl get hpa,pods -n orders --watch
```

For VPA recommendations:

```powershell
kubectl apply -f platform/components/scaling/vpa-recommendation.yaml
kubectl describe vpa orders-api -n orders
```

Before KEDA:

```powershell
kubectl delete hpa storefront -n orders
kubectl apply -f platform/components/scaling/keda-alternative.yaml
kubectl get scaledobject,hpa -n orders
```

KEDA owns the generated HPA. Applying the hand-authored HPA simultaneously creates competing controllers.

Use `labs/04-operations/manifests/scale-pressure.yaml` to create deterministic pending pods for cluster-autoscaler evidence. Delete it before disruption testing.

## Disruption

Continuously request `/healthz` and `/api/orders` while draining one user node. If a single-replica API or its RWO volume is on that node, expect a recovery interval; do not claim zero downtime. The exercise is to measure and then redesign based on the SLO.

Raise the user-pool minimum to two before drain and return it to one afterward:

```powershell
./scripts/set-user-pool-minimum.ps1 -Minimum 2
# run drain and recovery measurement
./scripts/set-user-pool-minimum.ps1 -Minimum 1
```

A correct production improvement usually moves durable order state to a managed service, runs multiple stateless API replicas, and spreads them. Simply scaling SQLite writers is not a sound fix.

## Failure signatures

- OOM: `lastState.terminated.reason=OOMKilled`, exit 137, restarts, and a 16 MiB limit.
- Bad rollout: new ReplicaSet exists, readiness fails, old replicas may remain because `maxUnavailable=0`, and rollout status times out.

## Recovery and cost

Back up both desired state and data, then test restore into an isolated namespace or cluster. Zone redundancy is not regional DR; backup is not HA. Record RTO/RPO, data replication, traffic failover, identity/config dependencies, and operator steps.

```powershell
./scripts/backup-orders.ps1 -Mode Backup
./scripts/backup-orders.ps1 -Mode RestoreTest
```
