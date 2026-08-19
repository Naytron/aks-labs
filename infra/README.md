# Infrastructure

| Path | Purpose | Default lifecycle |
| --- | --- | --- |
| `automatic` | Compare managed production defaults | Delete on Day 1 |
| `standard` | Deep platform engineering labs | Stop nightly; delete Day 5 |
| `standard/spot-pool.bicep` | Interruptible workload exercise | Remove immediately |

All paid deployments require an explicit script invocation. Pull-request CI runs Bicep build only. Every template sets course and expiration tags, uses Entra identity, disables local AKS accounts and ACR admin credentials, and enables Key Vault purge protection.
