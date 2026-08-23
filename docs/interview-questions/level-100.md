---
layout: page
title: AKS Interview Questions - Level 100
permalink: /interview-questions/level-100/
---

1. Which responsibilities belong to the AKS-managed control plane, and which belong to customer-managed node pools? (Tests: AKS shared-responsibility architecture)
2. How do Pods, Deployments, ReplicaSets, and StatefulSets differ? (Tests: core Kubernetes workload objects)
3. When should configuration live in a ConfigMap versus a Secret, and when should a Pod consume it through environment variables versus mounted files? (Tests: configuration source and delivery fundamentals)
4. What basic inputs would you choose when creating an AKS cluster and its first node pool? (Tests: cluster creation fundamentals)
5. How do kubeconfig, kubectl, and the Kubernetes API work together when accessing an AKS cluster? (Tests: cluster access basics)
6. How do ClusterIP, NodePort, and LoadBalancer Services expose a workload differently? (Tests: Kubernetes Service types)
7. What role does an Ingress controller play between an Ingress resource and a Service? (Tests: basic HTTP routing)
8. At a high level, how does Azure CNI provide Pod networking in AKS? (Tests: Azure CNI fundamentals)
9. How do a PersistentVolume, PersistentVolumeClaim, and StorageClass work together? (Tests: persistent storage basics)
10. What is the difference between Microsoft Entra authentication and Kubernetes RBAC authorization? (Tests: identity and access boundaries)
11. How would you limit access to Kubernetes Secrets for a team? (Tests: secret access control)
12. When does the Horizontal Pod Autoscaler (HPA) add Pods, and when does the Cluster Autoscaler add nodes? (Tests: workload and infrastructure scaling)
13. A new Deployment has zero ready replicas; which Kubernetes objects and events would you inspect first? (Tests: first-response workload troubleshooting)
14. A Pod remains Pending after deployment; what basic scheduling and capacity checks would you perform? (Tests: Pod scheduling diagnosis)
15. A LoadBalancer Service has an external IP but the application is unreachable; what would you check first? (Tests: basic service connectivity troubleshooting)

## Production situations

16. **What would you do if** a production Pod repeatedly enters CrashLoopBackOff immediately after a release? (Tests: safe first response to application failure)
17. **What would you do if** kubectl suddenly returned authorization errors for an engineer who previously had access? (Tests: access troubleshooting)
18. **What would you do if** traffic increased rapidly while Pods and nodes were both near capacity? (Tests: basic scaling response)

<a href="{{ '/' | relative_url }}">Previous: Course home</a> | <a href="{{ '/interview-questions/' | relative_url }}">Question bank</a> | <a href="{{ '/interview-questions/level-200/' | relative_url }}">Next: Level 200</a>
