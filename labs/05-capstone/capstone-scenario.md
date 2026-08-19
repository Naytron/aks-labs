# Capstone scenario - Northwind Orders

Northwind launches a public ordering experience with two internal product teams. Initial traffic is modest but marketing can create 10x bursts. The service objective is 99.9 percent successful storefront requests each 30 days. Order loss must be under five minutes and regional recovery must complete within four hours.

Constraints:

- One platform team operates clusters; application teams own namespace workloads.
- Human access uses Entra and must be auditable.
- Pods must not contain static Azure credentials.
- Only the storefront is publicly reachable.
- East-west traffic is denied unless required.
- Deployments originate from Git reconciliation.
- Production design supports a zone failure and documents a regional failure strategy.
- Default lab implementation must remain under the agreed course budget.
- The platform must support safe Kubernetes/node upgrades and a tested restore.

Choose AKS Automatic or Standard for the production recommendation. The live lab may remain on Standard; explain any difference between demonstration and recommendation.
