# ARC runner operations

## Topology and ownership

```text
manual GitHub dispatch
  -> ARC demand and ephemeral runner resources
  -> runner pod in arc-runners
  -> Kubernetes scheduler
  -> AKS cluster autoscaler
  -> dedicated tainted runner node
  -> one job
  -> runner deletion
  -> later AKS node scale-down
```

| Layer | Owns | Does not own |
| --- | --- | --- |
| GitHub | workflow, queue, assignment | Kubernetes scheduling |
| ARC | runner registration and ephemeral runner pods | AKS nodes |
| Scheduler | pod placement and `FailedScheduling` events | node creation |
| AKS cluster autoscaler | bounded node scale-up/down | job demand |

`arc-systems` is for the controller and listener. `arc-runners` is for the runner scale set, authentication Secret, and ephemeral runner workloads.

## Safe defaults

- Private sandbox repository only; never public `naytron/aks-labs`.
- GitHub App installed on only the selected repository.
- One-job ephemeral runners, `minRunners: 0`, bounded `maxRunners`.
- Dedicated tainted min-zero autoscaling node pool.
- `workflow_dispatch`, `permissions: {}`, bounded shell jobs, timeout.
- No kubeconfig, cluster token, Docker socket, host path, or privileged DinD.
- Pinned chart and runner image versions.
- Separate runner cluster for production.

## Read-only triage

```powershell
kubectl get pods -n arc-systems -o wide
kubectl get pods -n arc-runners -o wide
kubectl get events -n arc-runners --sort-by=.metadata.creationTimestamp
kubectl get nodes -L agentpool
kubectl api-resources | Select-String 'actions.github.com'
kubectl get podmonitor -n arc-systems
kubectl logs -n arc-systems deployment/arc-gha-rs-controller --tail=100
kubectl logs -n arc-systems -l app.kubernetes.io/component=runner-scale-set-listener --tail=100
./scripts/query-prometheus.ps1 -Query 'sum(gha_registered_runners)'
helm3 list -n arc-systems
helm3 list -n arc-runners
./scripts/validate-arc.ps1 -Check Install
```

Triage order:

1. Did the job target the intended scale set?
2. Did ARC create an ephemeral runner and pod?
3. If `Pending`, what exact scheduler event occurred?
4. Do pod placement constraints match pool labels and taints?
5. Is the node pool at zero, scaling, at maximum, or blocked by quota?
6. Did the runner register, accept one job, and terminate?

Do not treat `Pending` as a root cause. Do not fix placement by removing the taint.

## Egress checkpoints

ARC and runners require outbound TCP 443 to `github.com`, `api.github.com`, and `*.actions.githubusercontent.com`. Pulling the pinned controller and runner images also needs `ghcr.io` and `pkg-containers.githubusercontent.com`.

Checkout, artifacts, releases, packages, and other workflow features can require additional GitHub-published domains such as `codeload.github.com`, `results-receiver.actions.githubusercontent.com`, `*.blob.core.windows.net`, `objects.githubusercontent.com`, and `release-assets.githubusercontent.com`. Some names use CNAME chains.

Standard Kubernetes NetworkPolicy cannot match DNS names. Production FQDN controls require a supported Cilium or egress-firewall design plus testing against GitHub's current [domain list](https://docs.github.com/actions/reference/runners/self-hosted-runners#accessible-domains-by-function).

## Lifecycle commands

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Deploy
Get-Help ./scripts/deploy-arc.ps1 -Full
./scripts/validate-arc.ps1 -Check Install
./scripts/validate-arc.ps1 -Check Security
./scripts/inject-arc-failure.ps1 -Scenario Scheduling
./scripts/inject-arc-failure.ps1 -Scenario Scheduling -Restore
./scripts/validate-arc.ps1 -Check ScaleToZero
./scripts/cleanup-arc.ps1 -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
./scripts/manage-arc-runner-pool.ps1 -Action Delete
./scripts/validate-arc.ps1 -Check Cleanup -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
```

Use `Get-Help ./scripts/<name>.ps1 -Full` before class. Never pass key contents through Helm `--set` or a process argument.

## Evidence without secrets

Capture UTC timestamps, conditions, events, chart/image versions, pod placement, runner/node counts, and GitHub job states.

Never capture:

- Secret YAML or decoded data;
- App key, token, kubeconfig, private repository identity;
- App, installation, subscription, or tenant IDs;
- unredacted Helm values or diagnostic bundles.

## Safety stops

Stop on public/uncertain repository visibility, broad App installation, unexpected queued jobs, wrong cluster context, unknown node maximum, credential exposure, or proposed privileged/cluster-admin access.

Cleanup is complete only when jobs, ARC releases, both namespaces, authentication material, runner pool, App installation/key, and local key file are absent.

See [the learner module](../../labs/06-arc-runners/README.md) for the full exercise.

References: [ARC overview](https://docs.github.com/actions/hosting-your-own-runners/managing-self-hosted-runners-with-actions-runner-controller/about-actions-runner-controller), [GitHub App authentication](https://docs.github.com/actions/how-tos/manage-runners/use-actions-runner-controller/authenticate-to-the-api), [runner scale set deployment](https://docs.github.com/actions/how-tos/manage-runners/use-actions-runner-controller/deploy-runner-scale-sets), and [AKS cluster autoscaler](https://learn.microsoft.com/azure/aks/cluster-autoscaler).
