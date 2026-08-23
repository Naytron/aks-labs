---
layout: page
title: AKS Interview Questions - Level 400
permalink: /interview-questions/level-400/
---

1. How would you decide between AKS Automatic and AKS Standard for an enterprise workload portfolio? (Tests: managed platform operating-model selection)
2. How would you design an AKS landing zone and platform architecture that separates central governance from application-team autonomy? (Tests: enterprise platform architecture)
3. Which capabilities would you centralize with Azure Kubernetes Fleet Manager, and which would remain cluster-local? (Tests: multi-cluster fleet design)
4. How would you choose between multi-region active-active and active-passive designs for a critical AKS service? (Tests: multi-region architecture tradeoffs)
5. How would you design private AKS connectivity across hub-spoke or Virtual WAN, including DNS and deterministic egress? (Tests: enterprise private network architecture)
6. How would you assign SLO and error-budget ownership across platform and application teams? (Tests: reliability operating model)
7. How would business RTO and RPO requirements shape data replication, application-consistent backup, Azure Backup or Velero selection, restore validation, cluster configuration, and regional recovery? (Tests: disaster recovery strategy)
8. How would you govern Kubernetes and node-image upgrades across a large fleet while preserving explicit stop conditions? (Tests: fleet-wide upgrade governance)
9. How would you allocate shared AKS costs, expose unit economics, and create FinOps incentives without encouraging unsafe utilization? (Tests: enterprise AKS FinOps)
10. How would you build private deployment paths from GitHub Actions or Azure DevOps through self-hosted runners or Actions Runner Controller (ARC) scale sets? (Tests: private continuous delivery architecture)
11. How would you threat-model a compromised CI/CD workflow that can deploy to production AKS clusters? (Tests: deployment credential and supply-chain security)
12. How would you migrate a live estate from legacy kubenet to Azure CNI Overlay with Cilium while controlling workload risk? (Tests: network modernization strategy)
13. What does zero trust require for users, workloads, networks, artifacts, secrets, and administrative access in AKS? (Tests: end-to-end zero-trust design)
14. How would you provide useful logs, metrics, traces, and SLO views across hundreds of clusters without uncontrolled cost or cardinality? (Tests: fleet-scale observability)
15. Describe a production AKS decision you owned, the evidence behind it, the failure modes encountered, and the measurable outcome. (Tests: proof of production ownership)

## Production situations

16. **What would you do if** a fleet-wide policy or GitOps change began degrading clusters in several regions at different rates? (Tests: fleet incident containment)
17. **What would you do if** a region failed after replication lag had already exceeded the approved RPO? (Tests: executive disaster-recovery judgment)
18. **What would you do if** evidence showed a privileged deployment workflow had been compromised across the enterprise platform? (Tests: enterprise credential compromise response)

<a href="{{ '/interview-questions/level-300/' | relative_url }}">Previous: Level 300</a> | <a href="{{ '/interview-questions/' | relative_url }}">Question bank</a> | <a href="{{ '/' | relative_url }}">Next: Course home</a>
