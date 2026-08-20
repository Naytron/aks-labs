# Course automation

| Script | Purpose |
| --- | --- |
| `preflight.ps1` | Validate tools, Azure context, providers, region, and VM SKU |
| `find-lab-region.ps1` | Find a zone-enabled region with SKU and quota headroom |
| `new-kind-lab.ps1` | Create the local cluster, build images, and deploy |
| `deploy-lab.ps1` | Mandatory `what-if`, Bicep deployment, and post-deploy add-ons |
| `build-images.ps1` | Build locally or with ACR Tasks |
| `deploy-workload.ps1` | Render and apply the explicit Day 2/3/4 workload stage |
| `start-lab.ps1` | Safely start/select a stopped AKS lab |
| `show-lab.ps1` | Show context, power, Gateway, workload, and resource state |
| `bootstrap-gitops.ps1` | Configure managed Flux from a public GitHub branch |
| `configure-personas.ps1` | Assign/remove prepared Entra groups for Day 3 |
| `validate-lab.ps1` | Run machine-readable day-aligned gates |
| `inject-failure.ps1` | Apply and restore guarded incident faults for an explicit environment |
| `collect-evidence.ps1` | Capture a redacted incident evidence bundle |
| `set-user-pool-minimum.ps1` | Add/remove drain-test spare user capacity |
| `manage-spot.ps1` | Preview, deploy, or delete the short-lived Spot pool |
| `manage-arc-runner-pool.ps1` | Preview, deploy, or delete optional tainted runner capacity |
| `deploy-arc.ps1` | Guarded GitHub App Secret creation and pinned ARC installation |
| `validate-arc.ps1` | Validate ARC install, security, scale-to-zero, and cleanup gates |
| `test-arc-scale.ps1` | Dispatch the private scale test and capture runner/node timing |
| `inject-arc-failure.ps1` | Inject or restore one deterministic ARC failure |
| `cleanup-arc.ps1` | Remove ARC and its runner pool in GitHub-safe order |
| `backup-orders.ps1` | Create and verify an isolated SQLite restore |
| `query-prometheus.ps1` | Run an authenticated PromQL instant query without exposing a token |
| `cleanup-lab.ps1` | Stop or delete only tagged course resources |
| `test-static.ps1` | CI-safe application, Bicep, manifest, and secret checks |
| `test-e2e.ps1` | Safe-by-default full E2E with optional guarded live Azure phases |

E2E phase helpers live under `scripts/e2e/`; call the top-level harness rather than invoking them directly.

```powershell
# Full local E2E, no Azure
./scripts/test-e2e.ps1 -LocalOnly

# Local plus Azure validate/what-if, no paid resources
./scripts/test-e2e.ps1

# Instructor-only paid path
./scripts/test-e2e.ps1 -LiveAzure -AcknowledgeAzureCharges -MaxBudgetUsd 50

# Instructor-only ARC pilot, run inside the Dev Container
./scripts/test-e2e.ps1 `
  -LiveAzure `
  -AcknowledgeAzureCharges `
  -MaxBudgetUsd 50 `
  -ArcExtension `
  -ArcRepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>" `
  -ArcGitHubAppId "<github-app-id>" `
  -ArcGitHubAppInstallationId "<github-app-installation-id>" `
  -ArcGitHubAppPrivateKeyPath "/tmp/arc-github-app.pem"
```

The E2E harness requires `.aks-labs` to be absent before it starts, so its temporary ARC key must use an external or container-temporary path. Delete that file after the run.

Scripts never request or print credentials. Resource deletion requires exact course tags.
