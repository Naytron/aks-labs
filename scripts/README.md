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
```

Scripts never request or print credentials. Resource deletion requires exact course tags.
