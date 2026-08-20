# Setup options and prerequisites

## Recommended: Windows Dev Container

Use this path for the complete course, including local containers and `kind`.

1. Enable WSL 2 and install an Ubuntu distribution.
2. Install Docker Desktop, use the WSL 2 engine, and enable integration for that distribution.
3. Install Visual Studio Code and the Dev Containers extension.
4. Clone/open this repository from the WSL filesystem for better container and file performance.
5. Run **Dev Containers: Reopen in Container**.
6. Confirm the automatic local preflight passes.

The image pins Azure CLI, Bicep, PowerShell, Kubernetes CLI, Helm 4 for the core course, Helm 3 for the optional ARC module, GitHub CLI, kind, Flux, kubelogin, Kustomize, and kubeconform. Docker runs inside the development container so the lab does not depend on host socket permissions.

Recommended host capacity: 4 CPU cores, 12 GB available RAM, and 30 GB free disk. Allocate at least 6 GB RAM to Docker for the two-node `kind` lab.

## Fallback: Azure Cloud Shell PowerShell

Cloud Shell can run Bicep, Azure CLI, `kubectl`, and learner PowerShell scripts. It cannot provide the intended local Docker/`kind` experience.

Use this adaptation:

1. Run `./scripts/preflight.ps1 -CloudOnly` and complete the mental-model and manifest-rendering parts of prework.
2. Use ACR Tasks through `build-images.ps1 -Target acr` instead of local Docker builds.
3. Begin live workload deployment on the short-lived AKS Automatic environment.
4. Do not store kubeconfig, secret material, or generated evidence in persistent Cloud Shell storage after class.

The optional ARC module requires the supported Dev Container path because it relies on pinned Helm 3, GitHub CLI private-repository verification, and temporary key-file handling.

This fallback uses more Azure time and might exceed the lower end of the budget target.

## Azure prerequisites

- A dedicated lab subscription is required by the default path.
- Owner on that subscription is assumed so the course can create tagged resource groups, budgets, scoped RBAC, identities, and policy resources.
- A current four-vCPU-or-larger D-series SKU reported by `find-lab-region.ps1`, plus 12 vCPU scale-out headroom.
- Availability Zones and AKS support in the selected region.
- Permission to register the providers checked by `preflight.ps1`.
- No Azure Policy that silently mutates the lab design; review deny effects before class.
- A public GitHub copy/branch is required before Day 3 managed Flux.
- Instructor-prepared Entra test personas are required for real human authentication tests.

Do not paste subscription or tenant IDs into repository files. Azure CLI resolves the active context.

## First commands after setup

```powershell
Copy-Item .env.example .env
code .env
./scripts/preflight.ps1 -LocalOnly
```

Then continue with [prework](../labs/00-prework/README.md).
