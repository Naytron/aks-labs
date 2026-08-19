# Scaling, reliability, upgrades, and cost

## Scaling controllers

| Mechanism | Scales | Signal | Key caution |
| --- | --- | --- | --- |
| HPA | pod replicas | CPU/memory/custom metric | Requires requests; stabilization matters |
| VPA | requests/limits | observed use | Updates can evict pods; use recommendation first |
| KEDA | pod replicas | event/external scaler | Creates an HPA; do not add a competing HPA |
| Cluster autoscaler | nodes in known pools | unschedulable pods | Does not react directly to CPU percent |
| NAP | node shape/count | pending workload requirements | Changes pool-management model |

```text
traffic -> HPA/KEDA -> more pods -> pods become Pending -> CAS/NAP -> more nodes
```

## Reliability controls

| Control | Handles | Does not handle |
| --- | --- | --- |
| Readiness | remove unhealthy backend from traffic | restart process |
| Liveness | restart stuck process | dependency outage design |
| Startup probe | protect slow initialization | ongoing health |
| Replicas | pod/process loss | shared dependency/data loss |
| Topology spread | distribute replicas | create capacity |
| PDB | voluntary eviction budget | sudden node/zone loss |
| Availability Zones | datacenter failure | regional failure |
| Backup | recover lost/corrupt state | live availability |
| Multi-region | regional failure | automatic data consistency |

## Upgrade checklist

1. Check supported versions, deprecated APIs, add-on compatibility, and quota.
2. Confirm SLO, replicas, PDBs, probes, and spare capacity.
3. Preview/test in lower environment.
4. Define maintenance window, `maxSurge`, drain timeout, and abort criteria.
5. Upgrade control plane/nodes in supported order.
6. Watch user signals, controller status, and node/pod placement.
7. Validate workload and data; rollback only where the platform supports it.

## Spot

- Only restartable, checkpointed, interruption-tolerant work.
- Use label + taint + toleration.
- Never place critical singleton/system state there.
- Remove short-lived course Spot capacity after the exercise.

## Cost levers

| Driver | Control |
| --- | --- |
| Nodes | requests, bin packing, autoscaling, stop dev cluster, Spot for safe work |
| Logs/metrics | collect actionable signals, daily cap, retention, cardinality |
| Network | avoid unnecessary NAT/Firewall/egress volume |
| Storage | size/class/retention/snapshots |
| Control plane/add-ons | choose tier/features from requirements |

Course hard stops:

- Check context and tagged resource group before action.
- Stop Standard after class.
- Delete Automatic on Day 1.
- Delete Spot immediately.
- Delete Standard after Day 5 and verify zero resources.
- Budget alerts are delayed notifications, not an automatic shutoff.

References: [AKS scaling](https://learn.microsoft.com/azure/aks/concepts-scale), [AKS reliability](https://learn.microsoft.com/azure/aks/operator-best-practices-multi-region), [AKS upgrades](https://learn.microsoft.com/azure/aks/upgrade-cluster), [AKS cost optimization](https://learn.microsoft.com/azure/aks/best-practices-cost).
