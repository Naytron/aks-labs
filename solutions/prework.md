# Prework assessment reference

1. An image is immutable packaging; a container is a running instance.
2. Controllers replace pods, so identity/state must live outside an individual pod.
3. A Deployment owns ReplicaSets that maintain replicas and rolling updates.
4. A Service and its EndpointSlices provide stable discovery to changing pods.
5. The Service still resolves but has no ready backend, so requests fail.
6. Readiness controls traffic; liveness requests restart; startup delays the other probes.
7. Requests drive scheduling and utilization math; limits constrain runtime.
8. CIDR prefix length defines how many leading bits identify the network.
9. Overlap makes routing ambiguous and can require cluster/network recreation.
10. Entra proves identity; RBAC decides allowed actions.
11. Workload Identity uses federated, short-lived tokens instead of stored credentials.
12. A mutable tag can point to different bytes after approval.
13. Azure deployment reconciles Azure resources; Kubernetes apply reconciles cluster API objects.
14. A screenshot does not prove reproducibility, current state, or machine-checkable acceptance.
15. ACR, disks, public IP/NAT resources, and telemetry can still accrue charges.

Review [must-know terms](../docs/cheatsheets/must-know-terms.md), [Day-0 decisions](../docs/cheatsheets/aks-day0-decisions.md), and [identity/security](../docs/cheatsheets/identity-security-networking.md) for missed topics.
