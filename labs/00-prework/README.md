# Prework - Ready the workstation and subscription

**Timebox:** 3-4 hours before Day 1

## Before you begin

- Read [setup options](../../docs/setup.md) and the [attendee guide](../../docs/attendee-guide.md).
- Confirm the course audience prerequisites match your background.
- Keep the [must-know terms](../../docs/cheatsheets/must-know-terms.md) open.
- Work from the repository root in the Dev Container PowerShell terminal.
- No paid Azure course resource should exist yet.

## Outcome

You can build and run the workload locally, create a disposable Kubernetes cluster, validate Azure access and quota, preview Bicep safely, and explain exactly which subscription and cost boundary you will use.

## Must-know facts

- A container image is immutable application packaging; a container is one running instance.
- Kubernetes continuously reconciles declared desired state. Editing a running container is not a deployment strategy.
- `kubectl` acts on the current context. Check it before every destructive command.
- Bicep `what-if` predicts control-plane changes; it does not prove workload behavior.
- AKS control-plane management and node compute have separate responsibilities and costs.
- Owner access is assumed only in a dedicated lab scope. Production teams should separate platform, security, networking, and workload duties.
- A stopped AKS cluster can still incur ACR, disk, IP, and telemetry charges.

## Challenge

### 1. Configure the local lab

```powershell
Copy-Item .env.example .env
code .env
./scripts/preflight.ps1 -LocalOnly
```

Replace the prefix and expiration placeholders. Use a unique 3-8 character lowercase prefix. Leave the region placeholder until after subscription selection.

### 2. Select the Azure subscription

```powershell
az login
az account list --query "[].{Name:name,Default:isDefault}" --output table
az account set --subscription "<subscription-name>"
az account show --query "{Name:name,State:state}" --output table
./scripts/find-lab-region.ps1 -FixProvider
code .env
./scripts/preflight.ps1 -FixProviders
```

Set `AZURE_LOCATION` and `AKS_NODE_VM_SIZE` to the recommended `Ready` pair. Use the subscription **name** in shared evidence, not its identifier.

### 3. Test the application locally

```powershell
./scripts/test-static.ps1
docker compose -f app/compose.yaml up --build --detach --wait
Invoke-RestMethod http://localhost:8080/healthz
Invoke-RestMethod http://localhost:8080/api/orders `
  -Method Post `
  -ContentType application/json `
  -Body '{"item":"prework-book","quantity":1}'
docker compose -f app/compose.yaml down --volumes
```

### 4. Create the full local Kubernetes lab

```powershell
./scripts/new-kind-lab.ps1
./scripts/show-lab.ps1 -Environment kind
Invoke-RestMethod http://localhost:8080/api/orders
```

### 5. Preview Azure without deploying

```powershell
./scripts/deploy-lab.ps1 -Environment standard -WhatIf
```

Complete [the baseline assessment](baseline-assessment.md).

## Checkpoints

- Local preflight reports every pinned tool and Docker as available.
- Full preflight writes `evidence/preflight.json` with no failures.
- Compose creates and returns an order.
- `kind` has one control-plane node and one worker, and the full workload is ready.
- The subscription deployment preview completes without creating a course resource group.

## Acceptance criteria

- `evidence/preflight.json` contains no failed checks.
- Both application test suites pass.
- `kubectl get nodes` shows the `aks-labs` control plane and worker.
- The storefront creates and lists an order.
- Bicep `what-if` completes without changing Azure.
- You can state the active subscription name, resource-group naming convention, expiration, and maximum budget without exposing identifiers.
- Baseline assessment score is at least 70 percent or a remediation plan is recorded.

## Break/fix

Clear the current context, observe the safe failure, then recover without deleting kubeconfig:

```powershell
$originalContext = kubectl config current-context
kubectl config unset current-context
kubectl get nodes
kubectl config use-context $originalContext
```

Explain why context verification is an operational control rather than a convenience.

## Hints

1. Start with `kubectl config get-contexts`.
2. The current context has an asterisk in tabular output.
3. `kubectl config use-context kind-aks-labs` restores the local context.

## Tips and production notes

- **Tip:** Run `show-lab.ps1` whenever you return after a break.
- **Stop and check:** Do not continue if the subscription name, VM SKU, quota, or provider checks fail.
- **Lab shortcut:** `kind` replaces paid AKS only for the Kubernetes fundamentals.
- **Production default:** Validate IaC and policy in a nonproduction subscription before production.

## Cleanup

Keep the local `kind` cluster for Day 1, or remove it with:

```powershell
kind delete cluster --name aks-labs
```

No paid Azure resource should exist from prework.

**Next state:** keep the full `kind` cluster running. Day 1 deliberately recreates it with the starter workload.

## Daily gate

Run:

```powershell
./scripts/validate-lab.ps1 -Gate Prework
```

Save the validation JSON and your assessment remediation notes. After submitting your first attempt, compare with the [prework reference](../../solutions/prework.md).
