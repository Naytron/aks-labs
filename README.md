# AKS Level 400 Bootcamp

A five-day, challenge-driven path from first Kubernetes workload to production AKS platform operations. The course is approximately 80 percent hands-on: each topic has a one-page mental model, a realistic challenge, automated acceptance checks, an intentional failure, progressive hints, and a reference solution.

## What level 400 means here

Completion means you can:

- Choose and defend AKS Automatic or AKS Standard for a workload.
- Reproduce a secure cluster with Bicep and explain its Day-0 networking decisions.
- Deliver workloads through GitOps with Entra-based access and Workload Identity.
- Operate observability, scaling, reliability, upgrade, backup, and cost controls.
- Diagnose an unfamiliar production incident from evidence rather than a runbook answer.

It does not mean memorizing every `az` or `kubectl` flag.

## Five-day path

| Day | Level | Focus | Daily gate |
| --- | ---: | --- | --- |
| Prework | 0 | Workstation, subscription, budget, local `kind` | Preflight passes |
| 1 | 100 | Kubernetes mental model, ACR, AKS Automatic | Deploy and repair the workload |
| 2 | 200 | AKS Standard, CNI, Cilium, scheduling, routing, storage | Recreate and defend the platform |
| 3 | 300 | Entra/RBAC, Workload Identity, Key Vault, policy, Flux | Prove least privilege and reconciliation |
| 4 | 300-400 | Metrics, logs, scale, disruption, upgrades, DR, cost | Meet availability and cost objectives |
| 5 | 400 | Incident gauntlet and production capstone | Pass the rubric and architecture defense |

See [the complete course map](docs/course-map.md).

Attendees should read the [attendee guide](docs/attendee-guide.md) before prework and keep the [cheat-sheet index](docs/cheatsheets/README.md) open during class.

Review the course through [GitHub Pages](https://naytron.github.io/aks-labs/) and use the [interactive Level 100-400 AKS quiz](https://naytron.github.io/aks-labs/interview-questions/quiz/) for progressive self-assessment, answer guides, and Microsoft Learn resources.

After the required capstone, an [optional Level 400 ARC module](labs/06-arc-runners/README.md) covers private GitHub Actions runner scale sets, GitHub App authentication, dedicated scale-to-zero runner capacity, two-layer autoscaling, security, break/fix, and complete cleanup. It requires an instructor-prepared private sandbox repository and does not run on the public course repository.

## Recommended setup

1. Use a dedicated lab subscription where you are **Owner**. The default Bicep path creates its own tagged resource groups and role assignments.
2. On Windows, enable WSL 2, install Docker Desktop and VS Code, then open this repository in its Dev Container.
3. Copy `.env.example` to `.env`; set a unique prefix and future expiration.
4. Sign in, select the lab subscription, and find an eligible region:

   ```powershell
   az login
   az account set --subscription "<subscription-name>"
   ./scripts/find-lab-region.ps1 -FixProvider
   ```

5. Set `AZURE_LOCATION`, run `./scripts/preflight.ps1 -FixProviders`, then start [prework](labs/00-prework/README.md).

Azure Cloud Shell is the fallback if the Dev Container is unavailable. Local `kind` covers early exercises at no Azure compute cost.

See [setup options and prerequisites](docs/setup.md) for the Windows and Cloud Shell paths.

Course owners can review the latest [end-to-end QA report](docs/qa-report.md) and [release-readiness checklist](docs/release-readiness.md).

Run the repeatable safe E2E from the repository root:

```powershell
./scripts/test-e2e.ps1
```

Use `-LocalOnly` without Azure, or review the guarded live syntax in [the attendee rehearsal guide](docs/e2e-attendee-rehearsal.md). Paid resources are never the default.

## Cost boundary

The default learner path targets roughly **USD 50-100**, not a guaranteed bill. Region, quota, VM prices, telemetry volume, and learner timing vary. The course therefore:

- Deletes the AKS Automatic comparison cluster on Day 1.
- Reuses one lab-sized AKS Standard cluster on Days 2-5.
- Stops the cluster outside lab hours.
- Makes premium observability, firewall, and multi-region deployments optional.
- Keeps the ARC runner pool at zero when idle and removes it after the optional extension.
- Uses Bicep `what-if` for expensive architecture exercises.
- Validates cleanup and unexpected resources every day.

Read [cost controls](docs/cost-controls.md) before deployment.

## Repository map

- `app/`: deliberately small orders workload used by every day.
- `infra/`: cost-controlled Bicep for AKS Automatic and Standard.
- `platform/`: Kustomize, policy, scaling, observability, and Flux assets.
- `labs/`: learner challenges and daily gates.
- `solutions/`: reference answers; avoid until hints are exhausted.
- `scripts/`: preflight, deployment, validation, failure injection, and cleanup.
- `tests/`: local and CI-safe validation.
- `docs/`: course map, troubleshooting, cost, assessment, and instruction.
- `docs/cheatsheets/`: concise, printable just-in-time references.

## Safety

Never commit credentials, kubeconfigs, generated secrets, or tenant/subscription identifiers. CI performs static validation only and never deploys paid Azure resources. See [SECURITY.md](SECURITY.md).

## Source guidance

The course tracks current Microsoft guidance:

- [Plan AKS design and operations](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks-start-here)
- [AKS baseline architecture](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks/baseline-aks)
- [Advanced AKS concepts](https://learn.microsoft.com/azure/aks/advanced-aks-concepts)
- [AKS day-2 operations](https://learn.microsoft.com/azure/architecture/operator-guides/aks/day-2-operations-guide)
