---
layout: page
title: AKS Interview Questions - Level 300
permalink: /interview-questions/level-300/
---

1. How would you turn the AKS secure baseline into enforceable cluster, identity, network, and workload controls? (Tests: secure baseline implementation)
2. How would you design private connectivity from workloads to Azure PaaS services without public exposure? (Tests: private endpoints and name resolution)
3. How would you combine maintenance windows, upgrade channels, maxSurge, PodDisruptionBudgets (PDBs), and topology spread constraints? (Tests: controlled maintenance and availability)
4. What tests, health gates, and abort boundaries would you define for an AKS upgrade? (Tests: evidence-based upgrade safety)
5. How would you implement multi-tenancy across namespaces, identities, networks, quotas, nodes, and policy boundaries? (Tests: multi-tenant cluster design)
6. How would you trace a Workload Identity failure across service accounts, federated credentials, tokens, and Azure authorization? (Tests: Workload Identity deep troubleshooting)
7. How would you design Key Vault CSI secret rotation, and how should workloads behave during a Key Vault outage? (Tests: secret rotation and dependency resilience)
8. How would you diagnose an unexpected traffic denial across Cilium policy, eBPF datapath, DNS, and Azure networking? (Tests: Cilium network troubleshooting)
9. How would you derive AKS alerts and dashboards from service-level objectives instead of infrastructure thresholds alone? (Tests: SLO-based observability)
10. How would you isolate latency caused by application code, throttling, cgroups, CNI, storage, DNS, or an Azure dependency? (Tests: cross-layer performance analysis)
11. How would you prevent unstable interactions among HPA, VPA, KEDA, Cluster Autoscaler, requests, and quotas? (Tests: autoscaling systems design)
12. How would you design a stateful AKS workload across availability zones while respecting disk topology and failover limits? (Tests: zonal stateful architecture)
13. How would you implement auditable GitOps promotion and rollback when the same manifests serve several environments? (Tests: production GitOps controls)
14. How would you combine Defender for Containers, Azure Policy, Deployment Safeguards, image signing, and admission controls? (Tests: software supply-chain governance)
15. How do you structure incident command, evidence collection, mitigation, recovery, and learning during a severe AKS incident? (Tests: production incident method)

## Production situations

16. **What would you do if** a Cilium policy rollout isolated only some replicas and standard Kubernetes events showed no error? (Tests: eBPF datapath incident response)
17. **What would you do if** a zonal failure coincided with an upgrade and protected stateful Pods could not reschedule? (Tests: compound availability incident)
18. **What would you do if** a signed image passed admission but runtime behavior suggested the build pipeline was compromised? (Tests: supply-chain incident containment)

<a href="{{ '/interview-questions/level-200/' | relative_url }}">Previous: Level 200</a> | <a href="{{ '/interview-questions/' | relative_url }}">Question bank</a> | <a href="{{ '/interview-questions/level-400/' | relative_url }}">Next: Level 400</a>
