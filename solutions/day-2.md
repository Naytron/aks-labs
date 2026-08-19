# Day 2 reference solution

## Address plan

- VNet `10.40.0.0/16`
- Node subnet `10.40.0.0/22`
- API-server integration subnet `10.40.4.0/28`
- Service CIDR `10.0.0.0/16`
- DNS service IP `10.0.0.10`
- Pod overlay CIDR `10.244.0.0/16`

Only nodes and the API-server integration consume these VNet subnet addresses. Overlay pod addresses remain internal to the cluster data plane. Effective workload capacity is constrained by `maxPods * node count`, overlay size, compute quota, and schedulable resources; calculate all four.

## Provisioning

```powershell
./scripts/deploy-lab.ps1 -Environment standard -WhatIf
./scripts/deploy-lab.ps1 -Environment standard
./scripts/build-images.ps1 -Target acr
./scripts/deploy-workload.ps1 -Target azure -Environment standard -Stage day2
```

The post-deploy step enables managed Gateway API application routing and managed Prometheus because current stable Bicep/AVM does not expose all corresponding CLI flags.

## Architecture choices

| Decision | Lab choice | Production discussion |
| --- | --- | --- |
| Mode | Standard | Automatic first unless explicit control is needed |
| CNI | Azure CNI Overlay + Cilium | Direct pod routing requires VNet-routable CNI |
| API | Public, Entra, optional authorized IPs | Evaluate private endpoint/VNet access |
| Egress | Standard LB with one AKS-managed outbound IP | Static egress gateway or Firewall for stricter control |
| Pools | Tainted system + autoscaling user | At least two system nodes, SLO-aligned zones |
| ACR/Key Vault | Public data plane for lab | Premium/private endpoints for sensitive production |

## Traffic trace

1. Client resolves the Gateway address and reaches its listener.
2. The managed `approuting-istio` proxy evaluates `HTTPRoute`.
3. `backendRefs` selects the storefront Service, which resolves to ready EndpointSlices.
4. Storefront resolves `orders-api.orders.svc`, reaches its ClusterIP, then one ready API endpoint.
5. Outbound traffic leaves through the AKS-managed Standard Load Balancer public IP.

Check status:

```powershell
kubectl get gateway,httproute -n orders -o yaml
kubectl get service,endpointslice -n orders
kubectl get pods -n orders -o wide
```

## Persistence caveat

The lab uses one API replica, `Recreate`, a ReadWriteOnce claim, and SQLite. This demonstrates Kubernetes persistence, not a production multi-writer database. Production should use an external managed data service or a datastore designed and operated for distributed concurrency and recovery.
