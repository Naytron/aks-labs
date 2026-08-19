# Cost controls

## Before the first deployment

1. Run `find-lab-region.ps1` and select a zone-enabled D-series region/SKU pair with at least 12 vCPU headroom.
2. Create an Azure budget at the subscription or resource-group scope.
3. Set `LAB_BUDGET_USD` and an expiration date in `.env`.
4. Run `./scripts/preflight.ps1`; do not bypass a quota or budget failure.
5. Review the deployment with `./scripts/deploy-lab.ps1 -Environment standard -WhatIf`.

## Default cost profile

- One Basic ACR.
- One small Log Analytics workspace with a 0.5 GB daily cap and short retention.
- One lab AKS Standard cluster using a D-series system pool and an autoscaling user pool.
- No persistent Managed Grafana, Azure Firewall, NAT Gateway, multi-region peer, or duplicate AKS cluster.
- A temporary AKS Automatic cluster exists only during its comparison lab.

The Standard cluster uses reduced nonproduction counts. Production guidance still requires availability-zone and replica decisions based on SLOs.

## Daily controls

```powershell
./scripts/validate-lab.ps1 -Environment standard -Check Cost
./scripts/show-lab.ps1 -Environment standard
./scripts/cleanup-lab.ps1 -Mode Daily
```

Stop the reusable cluster after class:

```powershell
./scripts/cleanup-lab.ps1 -Mode Daily
```

Start it before the next AKS exercise:

```powershell
./scripts/start-lab.ps1 -Environment standard
```

An AKS stop operation does not stop every supporting Azure charge. ACR, disks, public IPs, and telemetry can still accrue cost.

Budget notifications and Cost Management records are delayed; they are not an automatic shutoff. Use elapsed time, resource inventory, and the instructor hard-stop in addition to the budget.

## Hard stop

Run `./scripts/cleanup-lab.ps1 -Mode Final -Wait`, verify the resource group no longer exists, and review Cost Management the following day for delayed usage records.
