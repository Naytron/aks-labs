---
layout: page
title: AKS Interview Questions - Level 200
permalink: /interview-questions/level-200/
---

<a href="{{ '/interview-questions/quiz/?level=200' | relative_url }}">Start the interactive Level 200 quiz</a>

1. How would you select a supported Kubernetes version and region features before creating an AKS cluster? (Tests: AKS version support and creation planning)
2. How would you plan a safe control-plane, node-pool, and node image upgrade sequence? (Tests: upgrade and node image operations)
3. How would you use multiple node pools, taints, tolerations, labels, and affinity to place workloads? (Tests: workload scheduling design)
4. How do Azure CNI Overlay, flat Azure CNI, and legacy kubenet differ in IP use, routing, and migration concerns? (Tests: AKS network model selection)
5. How would you enforce and validate NetworkPolicy when using Azure CNI Overlay with Cilium? (Tests: network segmentation)
6. How would you choose among Gateway API implementations, legacy Ingress, and LoadBalancer Services, and migrate from retiring ingress-nginx-based routing? (Tests: current application routing and migration)
7. How would you design VNet integration, private cluster DNS, and controlled egress for a private AKS cluster? (Tests: private networking and egress)
8. How do Azure Disk CSI and Azure Files CSI differ in access modes and workload fit? (Tests: AKS storage selection)
9. When would you use Azure RBAC for Kubernetes Authorization instead of native Kubernetes RBAC? (Tests: authorization model tradeoffs)
10. How would you migrate an existing workload from retired Azure AD Pod Identity to Microsoft Entra Workload Identity, and which federation changes would you validate? (Tests: workload identity modernization)
11. How do HPA, VPA, KEDA, and Cluster Autoscaler differ, and where can their decisions conflict? (Tests: autoscaling tool selection)
12. How would you combine Container Insights, managed Prometheus, and Azure Managed Grafana for cluster operations? (Tests: monitoring platform design)
13. How would you structure promotion and rollback with Flux or Argo CD across environments? (Tests: GitOps delivery)
14. What controls would you add to an Azure DevOps or GitHub Actions pipeline deploying to AKS? (Tests: secure continuous delivery)
15. Which utilization, purchase, and architecture signals would you use to reduce AKS cost without hiding reliability risk? (Tests: cost optimization)

## Production situations

16. **What would you do if** an AKS upgrade stalled while workloads were protected by strict PodDisruptionBudgets? (Tests: upgrade disruption troubleshooting)
17. **What would you do if** Pods in a private cluster could resolve internal names but could not reach an approved external API? (Tests: DNS and egress diagnosis)
18. **What would you do if** KEDA added Pods but the Cluster Autoscaler did not provide enough schedulable nodes? (Tests: multi-layer autoscaling troubleshooting)
{: start="16" }

<a href="{{ '/interview-questions/level-100/' | relative_url }}">Previous: Level 100</a> | <a href="{{ '/interview-questions/' | relative_url }}">Question bank</a> | <a href="{{ '/interview-questions/level-300/' | relative_url }}">Next: Level 300</a>
