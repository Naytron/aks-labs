# Day 4 - Observability, scale, reliability, upgrades, and cost

**Level:** 300-400 | **Hands-on:** approximately 6 hours

## Before you begin

- Day 3 gate passed and Flux is healthy.
- Read [scaling, reliability, upgrades, and cost](../../docs/cheatsheets/operations-reliability-cost.md).
- Copy [the operations evidence worksheet](operations-evidence.md) to `evidence/day4-operations.md`.
- Start Standard, update Flux/deploy to Day 4, and verify:

```powershell
./scripts/start-lab.ps1 -Environment standard
$repoUrl = "https://github.com/naytron/aks-labs"
./scripts/bootstrap-gitops.ps1 -RepositoryUrl $repoUrl -Branch main -Stage day4
./scripts/show-lab.ps1 -Environment standard
```

## Outcome

You can define workload signals, scale from evidence, maintain availability during controlled disruption, plan safe upgrades and recovery, and explain the cost of each reliability choice.

## Must-know facts

- Metrics show trends, logs explain discrete events, traces connect requests, and Kubernetes events explain control-loop decisions.
- Start with latency, traffic, errors, and saturation; alert on user impact and exhausted error budget.
- HPA needs resource requests. VPA recommendation mode avoids surprise evictions. KEDA is useful for external/event signals and creates an HPA.
- Do not attach two autoscaling controllers to one target.
- Cluster autoscaler reacts to unschedulable pods, not directly to CPU percentage.
- PDBs govern voluntary eviction, not node crashes. A PDB cannot create replicas.
- `maxSurge`, drain timeout, maintenance windows, and node soak time shape upgrade risk and cost.
- Spot nodes are interruptible; tolerate and schedule only restartable work.
- Backup is not high availability. Zones, regions, data replication, and restore testing address different risks.
- Telemetry has ingestion and retention cost; collect signals with a decision or SLO.

## Challenge

### 1. Observe the user journey

Create a dashboard or query set for request rate, error rate, pod readiness, restarts, CPU/memory, pending pods, and node pressure. Record p95 from the bounded load generator; do not pretend a counter is a latency histogram. Add one SLO and a multi-window alert design using [the SLO worksheet](slo-worksheet.md).

Use managed Prometheus PodMonitors for both services and query control-plane logs in Log Analytics. Managed Grafana is optional; screenshots alone do not count as evidence.

Record the query text and returned timestamp/value, not only a portal image.

```powershell
./scripts/query-prometheus.ps1 -Query 'sum(rate(storefront_requests_total[5m]))'
./scripts/query-prometheus.ps1 -Query 'sum(rate(orders_api_errors_total[5m]))'
```

### 2. Scale from a hypothesis

1. Establish a baseline with the bounded load generator.
2. Apply storefront HPA and explain its target math.
3. Generate load and observe HPA conditions and replica changes.
4. Force pods unschedulable and observe cluster autoscaler evidence.
5. Inspect VPA recommendations without automatic updates.
6. Replace HPA with the KEDA alternative; never run both.
7. State when node auto-provisioning would be preferable to fixed pools.

Deterministic HPA setup:

```powershell
kubectl set env deployment/storefront -n orders CPU_BURN_MS=25
kubectl apply -f platform/components/scaling/hpa.yaml
$gateway = kubectl get gateway orders -n orders -o jsonpath='{.status.addresses[0].value}'
python app/loadgen/load.py "http://$gateway" --requests 2000 --concurrency 50
kubectl describe hpa storefront -n orders
```

VPA and KEDA ownership:

```powershell
kubectl apply -f platform/components/scaling/vpa-recommendation.yaml
kubectl describe vpa orders-api -n orders
kubectl delete hpa storefront -n orders
kubectl apply -f platform/components/scaling/keda-alternative.yaml
kubectl get scaledobject,hpa -n orders
```

Cluster-autoscaler pressure:

```powershell
kubectl apply -f labs/04-operations/manifests/scale-pressure.yaml
kubectl get pods,nodes -n orders --watch
kubectl delete -f labs/04-operations/manifests/scale-pressure.yaml
```

### 3. Survive maintenance

- Verify two storefront replicas, topology spread, graceful termination, and PDB.
- Drain one user node and continuously probe the storefront.
- Measure errors rather than claiming zero downtime.
- Correct any PDB or capacity issue.
- Deploy the Spot pool, schedule a disposable workload with matching toleration, and model eviction.
- Remove the pool immediately.

Before draining, raise the user-pool minimum to two and wait for both nodes. Use `manage-spot.ps1` for the Spot pool:

In a second terminal, record one request per second during drain:

```powershell
$gateway = kubectl get gateway orders -n orders -o jsonpath='{.status.addresses[0].value}'
1..120 | ForEach-Object {
  $started = Get-Date
  try { $status = (Invoke-WebRequest "http://$gateway/healthz" -TimeoutSec 3).StatusCode }
  catch { $status = 'error' }
  [pscustomobject]@{ Time = $started.ToUniversalTime(); Status = $status }
  Start-Sleep -Seconds 1
} | Tee-Object evidence/day4-drain.csv
```

In the first terminal:

```powershell
./scripts/set-user-pool-minimum.ps1 -Minimum 2
$node = (kubectl get nodes -l agentpool=user -o name | Select-Object -First 1)
kubectl drain $node --ignore-daemonsets --delete-emptydir-data --timeout=10m
kubectl uncordon $node

./scripts/manage-spot.ps1 -Action Deploy
kubectl apply -f labs/04-operations/manifests/spot-workload.yaml
kubectl get pod -n orders -l purpose=spot -o wide
./scripts/manage-spot.ps1 -Action Delete
./scripts/set-user-pool-minimum.ps1 -Minimum 1
```

### 4. Plan upgrades, recovery, and spend

Review automatic upgrade channels and maintenance windows. Produce:

- A staged control-plane/node/workload upgrade runbook with rollback boundaries.
- A backup/restore test for Kubernetes resources and persistent data.
- A zone-failure response.
- A multi-region active/active or active/passive design using `what-if`/diagram only.
- Current daily cost drivers and three optimizations with reliability impact.

Create an application-consistent SQLite snapshot and verify it in an isolated namespace:

```powershell
./scripts/backup-orders.ps1 -Mode Backup
./scripts/backup-orders.ps1 -Mode RestoreTest
```

## Checkpoints

- Both PodMonitors have active targets and at least one query result is captured.
- HPA changes replica count under bounded load and returns toward minimum after stabilization.
- VPA produces a recommendation without applying it.
- HPA is removed before KEDA owns the target.
- Scale-pressure pods cause documented node scale behavior and are deleted.
- Drain impact is measured with spare capacity present.
- Spot workload lands only on Spot and the pool is removed.
- Backup hash and isolated restore row count are recorded.

## Acceptance criteria

- Both services are scraped through `azmonitoring.coreos.com/v1` PodMonitor objects.
- Queries connect user symptoms to workload and control-plane evidence.
- HPA scales up and down with documented stabilization behavior.
- VPA is recommendation-only and KEDA does not conflict with HPA.
- Cluster autoscaler evidence is tied to an unschedulable pod.
- Continuous probes quantify the node-drain result.
- Only an interruptible workload lands on Spot; the Spot pool is deleted.
- Upgrade and backup runbooks include validation and abort criteria.
- DR design states RTO, RPO, data replication, DNS/traffic failover, and cost.
- Cost validation remains inside the learner guardrail.

## Break/fix

Inject and restore each fault separately:

```powershell
./scripts/inject-failure.ps1 -Scenario oom -Environment standard -Stage day4
./scripts/collect-evidence.ps1 -Incident day4-oom -Environment standard
./scripts/inject-failure.ps1 -Scenario oom -Environment standard -Stage day4 -Restore

./scripts/inject-failure.ps1 -Scenario rollout -Environment standard -Stage day4
./scripts/collect-evidence.ps1 -Incident day4-rollout -Environment standard
./scripts/inject-failure.ps1 -Scenario rollout -Environment standard -Stage day4 -Restore
```

## Hints

1. `lastState.terminated.reason` identifies OOM; average memory graphs may miss a short spike.
2. A PDB can block a drain when desired replicas and available capacity make its requirement impossible.
3. Autoscaling diagnosis starts with controller conditions, metrics availability, requests, and pending reasons.

## Tips and production notes

- **Tip:** Build an autoscaling timeline: load, metric, desired replicas, pending reason, node action.
- **Why it matters:** two controllers on one target create unstable ownership.
- **Lab shortcut:** bounded CPU work makes HPA deterministic; production thresholds come from real service behavior.
- **Production default:** drain/upgrade only with spare capacity, tested PDBs, probes, and abort criteria.
- **Stop and check:** delete scale pressure and Spot before the cost gate.

## Cleanup

Restore both failures, remove HPA/KEDA test objects and load generators, delete the Spot pool, reduce telemetry experiments, run cost validation, and stop AKS.

```powershell
kubectl set env deployment/storefront -n orders CPU_BURN_MS-
kubectl delete -f platform/components/scaling/hpa.yaml --ignore-not-found
kubectl delete -f platform/components/scaling/keda-alternative.yaml --ignore-not-found
kubectl delete -f platform/components/scaling/vpa-recommendation.yaml --ignore-not-found
kubectl delete -f labs/04-operations/manifests/scale-pressure.yaml --ignore-not-found
./scripts/manage-spot.ps1 -Action Delete
./scripts/set-user-pool-minimum.ps1 -Minimum 1
./scripts/validate-lab.ps1 -Gate Day4
./scripts/cleanup-lab.ps1 -Mode Daily
```

**Next state:** Standard is stopped; no Spot/pressure/scaling test object remains.

## Daily gate

Submit the SLO worksheet, autoscaling timeline, drain test, upgrade/backup runbook, DR decision, and cost changes. Use [Day 4 reference material](../../solutions/day-4.md) only after diagnosis.
