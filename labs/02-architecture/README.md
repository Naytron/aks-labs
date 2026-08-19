# Day 2 - AKS architecture and Day-0 decisions

**Level:** 200 | **Hands-on:** approximately 6 hours

## Before you begin

- Day 1 gate passed and the Automatic resource group is deleted.
- Read [AKS Day-0 decisions](../../docs/cheatsheets/aks-day0-decisions.md).
- Confirm Azure context and that no Standard course resource group exists:

```powershell
az account show --query "{Name:name,State:state}" --output table
./scripts/preflight.ps1
```

## Outcome

You can reproduce an AKS Standard platform with Bicep, explain its address spaces and traffic paths, place workloads intentionally, expose an application with Gateway API, and identify which choices are expensive to reverse.

## Must-know facts

- Day-0 choices include API-server access, network plugin/mode, pod address model, and foundational IP ranges.
- Azure CNI Overlay conserves VNet IPs; pod IPs are not directly VNet-routable. Nodes still consume subnet addresses.
- Cilium supplies the eBPF data plane and network-policy enforcement.
- System and user node pools separate platform from workload scheduling. Taints repel; tolerations permit; affinity attracts.
- Gateway API separates infrastructure ownership (`Gateway`) from route ownership (`HTTPRoute`).
- A PVC is a claim; a StorageClass determines dynamic provisioning. Access mode does not guarantee application-level concurrency safety.
- Availability zones, topology spread, replicas, and PDBs solve different failure/disruption problems.
- Public API access with Entra and authorized IPs can be acceptable for a lab; production should evaluate private access.

## Challenge

### 1. Defend the address plan

Complete [the IP worksheet](ip-plan.md). Prove that VNet, node subnet, API-server subnet, service CIDR, pod CIDR, and external/on-prem ranges do not overlap. Estimate node and pod capacity.

Record the resulting choices in the [Day-0 decision record](day0-decision-record.md).

### 2. Provision from source

Review every trade-off in `infra/standard/README.md`, then:

```powershell
./scripts/deploy-lab.ps1 -Environment standard -WhatIf
./scripts/deploy-lab.ps1 -Environment standard
```

**Tip:** Cluster provisioning can take 20-45 minutes. Complete the IP worksheet and map expected Azure resources while it runs; do not launch a duplicate deployment.

Use the deployment outputs, not copied portal values. Map the managed cluster, node resource group, VM scale sets, public egress IP, ACR, Key Vault, Log Analytics, Azure Monitor workspace, and identities.

### 3. Publish and route

Build images in ACR, deploy the Azure overlay, then trace:

```powershell
./scripts/build-images.ps1 -Target acr -Environment standard
./scripts/deploy-workload.ps1 -Target azure -Environment standard -Stage day2
./scripts/show-lab.ps1 -Environment standard
```

1. Client to Gateway listener.
2. Gateway proxy to storefront Service and EndpointSlice.
3. Storefront pod to orders-api DNS, Service, EndpointSlice, and pod.
4. Pod outbound traffic through the stable egress IP.

Verify `Gateway` and `HTTPRoute` conditions rather than waiting only for an IP.

### 4. Schedule and store

- Prove workload pods cannot land on the tainted system pool.
- Add a temporary node label and use required node affinity for one replica.
- Compare required affinity with preferred affinity and topology spread.
- Create an order, restart the API pod, and prove persistence.
- Explain why scaling the SQLite API to several writers is unsafe even if storage permits attachment.

## Checkpoints

- Azure no-write validation and `what-if` succeed before deployment.
- `show-lab.ps1` reports the Standard cluster, expected context, and Gateway address.
- Gateway and HTTPRoute conditions are accepted/programmed.
- Workloads run only on the user pool; system taint remains.
- A created order survives API pod replacement.
- IP worksheet accounts for every overlapping network domain.

## Acceptance criteria

- Bicep build and subscription `what-if` pass.
- The deployed network uses Azure CNI Overlay, Cilium, nonoverlapping ranges, and one stable outbound IP.
- Local AKS accounts and ACR admin credentials are disabled.
- System and user workloads are separated by taint/toleration behavior.
- The Gateway and HTTPRoute report accepted/programmed conditions.
- Orders survive a pod replacement.
- The architecture record identifies at least four Day-0 decisions and their migration costs.
- Cost validation shows only expected resources.

## Break/fix

```powershell
./scripts/inject-failure.ps1 -Scenario scheduling -Environment standard -Stage day2
./scripts/collect-evidence.ps1 -Incident day2-scheduling -Environment standard
./scripts/inject-failure.ps1 -Scenario scheduling -Environment standard -Stage day2 -Restore
```

Then change a Service selector so it matches no pod and use EndpointSlices to locate the failure without restarting anything. Restore with the Day 2 stage.

## Hints

1. `Pending` is a scheduler outcome; inspect scheduling events before container logs.
2. A Service can exist and resolve in DNS while having zero backends.
3. Gateway status conditions identify whether failure is at class, listener, route, reference, or address provisioning.

## Tips and production notes

- **Tip:** Trace one packet path at a time and write each DNS name, virtual IP, endpoint, and policy boundary.
- **Lab shortcut:** Public API, Basic ACR, and public Key Vault data plane reduce lab cost.
- **Production default:** Evaluate private API/data endpoints, TLS, WAF, and at least two system nodes from SLO and threat requirements.
- **Why it matters:** CNI/IP choices are Day-0 decisions; changing them can require cluster migration.

## Cleanup

Remove temporary labels/affinity and restore the baseline. Delete debug pods. Do not stop the cluster until the daily gate passes.

## Daily gate

Submit the IP worksheet, Bicep `what-if` evidence, traffic trace, and Day-0 architecture record. Validate:

```powershell
./scripts/validate-lab.ps1 -Gate Day2
./scripts/cleanup-lab.ps1 -Mode Daily
```

Use the [Day 2 reference](../../solutions/day-2.md) only after exhausting hints.

**Next state:** Standard is stopped. Day 3 begins with `start-lab.ps1`.
