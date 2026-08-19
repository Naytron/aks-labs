# Day 1 reference solution

## Local objects

The reference overlay is `platform/environments/kind`. Important properties to compare with learner work:

- Stable labels are shared by Deployment selectors and Services.
- `startupProbe`, `readinessProbe`, and `livenessProbe` answer different lifecycle questions.
- Requests are smaller than limits and exist on every container.
- Containers use UID/GID 10001, `RuntimeDefault` seccomp, read-only root filesystems, and drop all capabilities.
- The API's writable state is an explicit volume, not its container layer.

Create and validate:

```powershell
./scripts/new-kind-lab.ps1 -Recreate
./scripts/validate-lab.ps1 -Environment kind -Check Workload
```

## Configuration rollout

```powershell
kubectl patch configmap orders-config -n orders --type merge --patch '{"data":{"APP_MESSAGE":"day-1-release"}}'
kubectl rollout restart deployment/orders-api -n orders
kubectl rollout status deployment/orders-api -n orders
Invoke-RestMethod http://localhost:8080/api/config
```

A ConfigMap mounted as environment variables is read only at process start, so a rollout is required. A volume-mounted ConfigMap has different update behavior.

## Failure evidence

### Image pull

Expected evidence:

- Deployment creates a new ReplicaSet.
- Pod status progresses to `ErrImagePull`/`ImagePullBackOff`.
- Events name the invalid registry or manifest.
- There are no application logs because the process never started.

### Readiness

Expected evidence:

- Process and liveness remain healthy.
- Readiness fails with HTTP 503.
- Service EndpointSlice marks the endpoint not ready.
- Storefront may return 502 because its only API endpoint is withdrawn.

Restore with `./scripts/inject-failure.ps1 -Scenario readiness -Environment kind -Restore`, then prove rollout and endpoint health.

## Automatic comparison

```powershell
./scripts/deploy-lab.ps1 -Environment automatic
./scripts/build-images.ps1 -Target acr -Environment automatic
./scripts/deploy-workload.ps1 -Target azure -Environment automatic -Stage day2
./scripts/validate-lab.ps1 -Environment automatic -Check All
```

| Concern | AKS Automatic | AKS Standard |
| --- | --- | --- |
| System nodes | Service managed | Operator sizes/isolates |
| Node provisioning | NAP managed | Pools/autoscaler/NAP selected |
| HPA/KEDA/VPA | Preconfigured | Explicit enablement |
| Upgrades | Safe managed defaults | Channel/windows/governance selected |
| Observability | Built in | Workspace and collection configured |
| Security safeguards | Curated baseline | Operator configures controls |
| Networking | Opinionated supported model | Explicit CNI, CIDRs, egress |

Automatic remains the production recommendation for typical workloads. Standard is not "more production"; it is more control and more operator responsibility.
