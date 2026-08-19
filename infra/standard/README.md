# AKS Standard lab environment

This is the reusable Days 2-5 environment. Supporting services use Azure Verified Modules; the network and Azure Monitor workspace use direct current resource types so their Day-0 design remains visible.

## Lab-specific trade-offs

- One system node is the default to control spend. Production should use at least two and align zones/counts to the SLO.
- A public API endpoint supports learners outside a private network. Set `apiServerAuthorizedIpRanges`; production should evaluate a private cluster.
- Basic ACR and RBAC-protected public Key Vault data-plane access reduce lab cost and network complexity. The lab Key Vault firewall explicitly allows traffic; production should evaluate Premium ACR, private endpoints, and default-deny network ACLs.
- Key Vault purge protection remains enabled. After final deletion, reuse a different prefix until the deleted vault's retention expires.
- The interactive learner receives AKS RBAC Cluster Admin and Key Vault Secrets Officer only on the dedicated lab resources. Production must replace these with group-based least privilege.
- Stable egress uses one AKS-managed Standard Load Balancer outbound IP rather than a charged NAT Gateway, Firewall, or subscription-gated custom public IP.
- Managed Grafana and Defender for Containers are optional paid extensions.

## Preview and deploy

Use the repository scripts rather than running the template directly:

```powershell
./scripts/deploy-lab.ps1 -Environment standard -WhatIf
./scripts/deploy-lab.ps1 -Environment standard
```

The post-deployment phase enables the AKS application-routing Gateway API implementation and managed Prometheus because the current stable ARM/AVM surface does not expose all corresponding CLI settings.

## Spot exercise

`spot-pool.bicep` is intentionally separate. Deploy it only during Day 4 and remove the pool immediately afterward.
