# Course map

## Delivery rhythm

Each day uses two 90-minute challenge blocks before lunch and two after lunch. Reserve the final 45 minutes for the daily gate, cost checkpoint, and debrief. Recommended timing is 09:00-17:00 with 90 minutes of breaks.

The intended attendee has Azure fundamentals and basic CLI, networking, and container knowledge, but no Kubernetes experience. Prework and Day 1 are guided; each later day intentionally removes implementation detail.

| Day | Block 1 | Block 2 | Block 3 | Block 4 | Gate |
| --- | --- | --- | --- | --- | --- |
| Prework | Tools | Azure access and budget | Local container | Local `kind` | Preflight |
| 1 | Core objects | Configuration and health | ACR and Automatic | Break/fix | Workload recovery |
| 2 | IaC and cluster anatomy | CNI and traffic | Scheduling and routing | Storage | Design defense |
| 3 | Human access | Workload identity | Guardrails | GitOps | Least privilege |
| 4 | Telemetry | Scaling | Disruption and upgrades | DR and cost | SLO exercise |
| 5 | Incident gauntlet | Incident review | Capstone build | Architecture defense | Rubric |

## Competency progression

| Competency | Day 1 | Day 2 | Day 3 | Day 4 | Day 5 |
| --- | --- | --- | --- | --- | --- |
| Application delivery | Guided | Declarative | GitOps | Safe rollout | Independent |
| Platform engineering | Observe | Build | Govern | Evolve | Defend |
| Security | Pod basics | Network boundaries | Identity and policy | Runtime evidence | Threat-aware design |
| Operations | Basic diagnostics | Traffic and storage | Reconciliation | SLO and incidents | Unknown failure |
| Cost | Teardown | Right-sized topology | Shared controls | Optimize | Explain trade-offs |

## Required modules

- [Prework](../labs/00-prework/README.md)
- [Day 1 - Foundations](../labs/01-foundations/README.md)
- [Day 2 - Architecture](../labs/02-architecture/README.md)
- [Day 3 - Security and delivery](../labs/03-security-delivery/README.md)
- [Day 4 - Operations](../labs/04-operations/README.md)
- [Day 5 - Capstone](../labs/05-capstone/README.md)

## Optional extension modules

After the capstone: Windows node pools, service mesh, GPU/KAITO workloads, Fleet at scale, regulated baseline, and operator development. These are intentionally excluded from the core five days.
