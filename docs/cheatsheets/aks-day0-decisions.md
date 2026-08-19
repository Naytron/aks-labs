# AKS architecture and Day-0 decisions

## Choose the operating model

| Requirement | Start with |
| --- | --- |
| Typical application hosting, lower platform burden | AKS Automatic |
| Explicit CNI/CIDRs, pools, upgrade cadence, specialized compliance | AKS Standard |
| "We want more control" without a concrete requirement | Re-evaluate; control has operating cost |

## Hard-to-change decisions

| Decision | Course lab choice | Production question |
| --- | --- | --- |
| API access | Public + Entra + optional source CIDRs | Private endpoint/VNet integration required? |
| Pod IP model | Azure CNI Overlay | Must VNet/on-prem directly address pods? |
| Data plane/policy | Cilium | Required policy/observability capability? |
| Address plan | Separate VNet/node/API/service/pod ranges | What future peers/on-prem ranges exist? |
| Egress | Standard LB + one AKS-managed outbound IP | Static gateway, custom prefix, NAT Gateway, or Firewall? |
| Ingress | Managed Gateway API | WAF, internal-only, TLS, multi-cluster routing? |

## Course address plan

```text
VNet              10.40.0.0/16
  node subnet     10.40.0.0/22
  API subnet      10.40.4.0/28
service CIDR      10.0.0.0/16
DNS service IP    10.0.0.10
pod overlay CIDR  10.244.0.0/16
```

No range may overlap with a cluster, VNet peer, VPN/ExpressRoute, or on-premises range.

## Traffic path

```text
client
  -> public/internal load balancer
  -> Gateway proxy
  -> HTTPRoute
  -> storefront Service
  -> storefront pod
  -> orders-api Service
  -> orders-api EndpointSlice/pod
  -> stable egress IP for outbound calls
```

At each arrow, verify address, route/reference, selector, endpoint, DNS, port, and policy.

## Pool and availability decisions

- Dedicated tainted system pool; application pods use user pools.
- Production system pool normally has at least two nodes.
- Replicas protect only when spread across independent failure domains.
- Zones handle datacenter failure; regions handle regional failure.
- PDB limits voluntary eviction; it does not help an unexpected node loss.
- Ephemeral OS disks improve node replacement, not application data durability.

## Lab shortcuts

- One system node reduces spend.
- Public ACR/Key Vault data planes reduce private-network complexity.
- One SQLite API replica demonstrates PVC persistence only.
- HTTP Gateway is for routing mechanics; production public traffic requires TLS.

References: [AKS design and operations](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks-start-here), [AKS baseline](https://learn.microsoft.com/azure/architecture/reference-architectures/containers/aks/baseline-aks), [Azure CNI Overlay](https://learn.microsoft.com/azure/aks/azure-cni-overlay).
