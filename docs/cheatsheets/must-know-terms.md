# Must-know Kubernetes and AKS terms

## Workload objects

| Term | Meaning | Do not confuse with |
| --- | --- | --- |
| Image | Immutable application filesystem and metadata | A running container |
| Container | Running process isolated by the container runtime | A VM |
| Pod | Smallest Kubernetes scheduling/lifecycle unit | A durable server |
| ReplicaSet | Maintains a count of matching pods | A release workflow |
| Deployment | Owns ReplicaSets and rolling updates | A pod |
| Service | Stable virtual address and discovery for selected pods | The application process |
| EndpointSlice | Actual ready backend addresses for a Service | A public endpoint |
| ConfigMap | Non-secret configuration | Secret storage |
| Secret | Kubernetes API object for sensitive bytes | A full secret-management system |
| PVC | Request for persistent storage | The physical disk itself |
| StorageClass | Dynamic provisioning policy | A backup policy |
| Job | Run-to-completion work | A continuously reconciled service |

## Reconciliation mental model

```text
manifest (desired state)
        |
        v
API server -> controller -> scheduler -> node/kubelet -> pod
        ^                                           |
        +------------ observed status --------------+
```

- **Desired state:** what the spec says should exist.
- **Observed state:** current status reported by controllers/nodes.
- **Controller:** loop that moves observed state toward desired state.
- **Declarative change:** update source/spec and let reconciliation act.
- **Drift:** live state differs from the approved source.

## Cluster terms

| Term | Meaning |
| --- | --- |
| Control plane | API server, scheduler, controllers, and cluster state managed by AKS |
| Node | VM that runs pods |
| Node pool | Nodes with shared VM/OS/scheduling configuration |
| System pool | Hosts critical AKS/Kubernetes components |
| User pool | Hosts application workloads |
| Namespace | Logical API scope, not a hard security boundary by itself |
| Taint | Repels pods unless they tolerate it |
| Toleration | Permits scheduling onto a matching tainted node |
| Affinity | Attracts/requires placement near labels or other pods |
| Topology spread | Distributes replicas across hosts/zones |
| PDB | Limits voluntary simultaneous pod eviction |

## AKS responsibility

| Area | AKS manages | You still own |
| --- | --- | --- |
| Control plane | Availability and lifecycle of managed components | Access, versions/channels, safe workload change |
| Nodes | Provisioning integration | Pool design, sizing, capacity, disruptions |
| Networking | Azure integration | CIDRs, ingress/egress, policies, DNS dependencies |
| Security | Managed features | Identity/RBAC, supply chain, policy, workload hardening |
| Observability | Integrations | Signals, queries, alerts, retention, response |
| Data | CSI integrations | Data service design, consistency, backup, restore, DR |

## Automatic versus Standard

- **Automatic:** recommended first for typical production workloads; curated node management, scaling, upgrades, security, and observability.
- **Standard:** choose when a concrete requirement needs explicit networking, pools, authorization, or upgrade control. More control means more operator responsibility.

References: [What is AKS?](https://learn.microsoft.com/azure/aks/what-is-aks), [AKS Automatic](https://learn.microsoft.com/azure/aks/intro-aks-automatic), [Kubernetes concepts](https://kubernetes.io/docs/concepts/).
