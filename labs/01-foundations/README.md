# Day 1 - Kubernetes and AKS foundations

**Level:** 100 | **Hands-on:** approximately 6 hours

## Before you begin

- Prework gate passed; the full `kind` lab is running.
- Open [must-know terms](../../docs/cheatsheets/must-know-terms.md) and [kubectl triage](../../docs/cheatsheets/kubectl-triage.md).
- Confirm state, then reset to the incomplete Day 1 starter:

```powershell
./scripts/show-lab.ps1 -Environment kind
./scripts/new-kind-lab.ps1 -Recreate -Starter
```

## Outcome

You can deploy, observe, update, and recover a containerized workload on Kubernetes; publish images to ACR; and explain which responsibilities AKS Automatic manages.

## Must-know facts

- Pods are scheduling and lifecycle units, not durable identities. Deployments own stateless pods.
- Services select pods by labels and publish stable discovery. EndpointSlices reveal the actual backends.
- ConfigMaps hold non-secret configuration. Kubernetes Secrets are transport/storage objects, not a complete secret-management strategy.
- Startup probes protect slow initialization; readiness controls traffic; liveness requests restart.
- Requests drive scheduling and utilization-based HPA math. Limits constrain runtime.
- `describe`, events, current logs, and previous logs answer different questions.
- A declarative rollout is observable and reversible; `latest` is not a release.
- AKS Automatic is the recommended production starting point for typical workloads. Standard is for explicit control and specialized architecture.

## Challenge

### 1. Reconstruct the local workload

Copy the valid but intentionally incomplete starter to your ignored working directory:

```powershell
New-Item -ItemType Directory .aks-labs/day1 -Force | Out-Null
Copy-Item labs/01-foundations/starter/* .aks-labs/day1/
code .aks-labs/day1/orders-api.yaml
```

Add startup/readiness/liveness probes, CPU/memory requests and limits, a non-root pod/container security context, a read-only root filesystem, and explicit writable `/tmp` storage. Apply after each coherent change:

```powershell
kubectl diff -k .aks-labs/day1
kubectl apply -k .aks-labs/day1
kubectl rollout status deployment/orders-api -n orders
```

Practice:

```powershell
kubectl explain deployment.spec.strategy
kubectl get pods,services,endpointslices -n orders
kubectl describe deployment orders-api -n orders
kubectl logs -n orders deployment/orders-api
kubectl rollout history deployment/storefront -n orders
```

After your API meets the criteria, compare it with `platform/base`, then deploy the complete local workload:

```powershell
./scripts/deploy-workload.ps1 -Target kind
./scripts/validate-lab.ps1 -Environment kind -Check Workload
```

### 2. Build a release

```powershell
./scripts/build-images.ps1 -Target kind
docker image inspect aks-labs/orders-api:dev --format '{{.Config.User}} {{json .Config.Healthcheck}}'
docker image inspect aks-labs/storefront:dev --format '{{.Config.User}} {{json .Config.Healthcheck}}'
```

Build both images, inspect their effective user and health checks, and explain why dependency-free Python services do not need a multi-stage build. Prove the Kubernetes containers cannot write outside `/tmp` or their explicit volume.

### 3. Compare AKS Automatic

1. Preview and deploy `infra/automatic`.
2. Build the release in its ACR.
3. Inspect cluster SKU, managed add-ons, upgrade profile, node provisioning, security profile, observability, and GatewayClass.
4. Deploy the workload with concrete ACR image names.
5. Record an Automatic-versus-Standard responsibility table.

```powershell
./scripts/deploy-lab.ps1 -Environment automatic -WhatIf
./scripts/deploy-lab.ps1 -Environment automatic
./scripts/build-images.ps1 -Target acr -Environment automatic
./scripts/deploy-workload.ps1 -Target azure -Environment automatic -Stage day2
./scripts/show-lab.ps1 -Environment automatic
./scripts/validate-lab.ps1 -Environment automatic -Check All
```

**Tip:** Cluster provisioning is the longest wait and can take 20-45 minutes. Draft the responsibility table while Azure reconciles; do not launch a duplicate deployment.

**Instructor fallback:** If AKS Automatic remains in `Creating` beyond the delivery hard-stop or the subscription disallows the SKU, cancel/delete it, retain the `what-if` evidence, and complete the responsibility comparison from the official Automatic documentation. Do not block the entire bootcamp or leave a stuck cluster accruing cost.

### 4. Operate and repair

Perform a ConfigMap rollout, scale storefront, view EndpointSlice changes, and roll back. Then diagnose one injected fault at a time:

```powershell
./scripts/inject-failure.ps1 -Scenario imagepull -Environment kind
./scripts/collect-evidence.ps1 -Incident day1-imagepull -Environment kind
./scripts/inject-failure.ps1 -Scenario imagepull -Environment kind -Restore

./scripts/inject-failure.ps1 -Scenario readiness -Environment kind
./scripts/collect-evidence.ps1 -Incident day1-readiness -Environment kind
./scripts/inject-failure.ps1 -Scenario readiness -Environment kind -Restore
```

Never overlap the two faults during Day 1.

## Checkpoints

- Your starter API becomes ready only after you add correct probes and writable storage.
- The full local workload creates and lists an order.
- Both images report UID/GID 10001 and a health check.
- Automatic reports the expected SKU, managed scaling, upgrade, security, observability, and Gateway API defaults.
- Both incidents have separate evidence and pass validation after restore.

## Acceptance criteria

- Workload manifests use explicit images, selectors, requests, limits, and all three probe types.
- Both containers run non-root with no added Linux capabilities.
- A ConfigMap change reaches new pods through a controlled rollout.
- A failed release is diagnosed from events/logs and rolled back.
- Images are stored in ACR with ACR admin credentials disabled.
- Live AKS Automatic evidence, or the instructor-approved no-write fallback, covers Entra/Azure RBAC, Workload Identity/OIDC, managed scaling, upgrade, observability, and Gateway API.
- The responsibility table has at least five meaningful differences.
- The Automatic resource group is deleted and verified before Day 2.

## Break/fix

Use the guarded injector for `imagepull`, then `readiness`. For each:

1. Write the user-visible symptom.
2. Capture the first Kubernetes evidence that identifies the fault domain.
3. State one plausible alternative hypothesis.
4. Run one check that eliminates it.
5. Restore only after recording evidence.

## Hints

1. If no pod starts, events are usually more valuable than logs.
2. If a pod runs but receives no traffic, compare readiness and EndpointSlices.
3. `kubectl rollout undo` restores a Deployment revision, but declarative state must also be corrected.

## Tips and production notes

- **Tip:** Use `kubectl explain` before copying schema from the web.
- **Why it matters:** readiness removes traffic; liveness restarts a process. Swapping them can amplify an outage.
- **Lab shortcut:** ACR builds avoid depending on the learner laptop for Azure images.
- **Production default:** Deploy immutable digests and preserve the source change that matches any rollback.

## Cleanup

```powershell
./scripts/cleanup-lab.ps1 -Mode Automatic -Wait
```

Verify the Automatic resource group is absent. Keep only the local `kind` cluster.

**Next state:** Automatic is deleted; full `kind` remains available for reference.

## Daily gate

Run:

```powershell
./scripts/validate-lab.ps1 -Gate Day1
```

Attach both incident evidence files and submit the Automatic-versus-Standard responsibility table. See the [Day 1 reference solution](../../solutions/day-1.md) only after all hints.
