# Troubleshooting map

Start with the symptom, gather evidence, form one hypothesis, run the smallest discriminating test, and record the result. Do not restart or redeploy before collecting evidence.

Keep the printable [kubectl triage sheet](cheatsheets/kubectl-triage.md) open during timed incidents.

| Symptom | First evidence | Common causes | Discriminating check |
| --- | --- | --- | --- |
| `Pending` | Pod events | quota, affinity, taint, PVC, resources | `kubectl describe pod` |
| `ImagePullBackOff` | Pod events | image/tag, ACR auth, DNS | `kubectl get events --sort-by=.lastTimestamp` |
| `CrashLoopBackOff` | Current and previous logs | bad config, startup failure, probe | `kubectl logs <pod> --previous` |
| `OOMKilled` | Container last state | memory leak or low limit | `kubectl get pod -o jsonpath=...` |
| Not ready | EndpointSlice and probe events | readiness path, dependency | `kubectl get endpointslices` |
| Service unreachable | Service, EndpointSlice, policy | selector, port, DNS, NetworkPolicy | ephemeral debug pod plus `nslookup` |
| External route fails | Gateway/HTTPRoute status | listener, hostname, backend | `kubectl describe gateway,httproute` |
| Secret mount fails | CSI pod events | federated identity, role, object name | CSI driver logs and federated credential |
| Flux drift | Flux conditions | source auth, path, invalid manifest | `flux get all -A` |
| No scale-out | HPA/KEDA conditions | metrics, requests, trigger auth | `kubectl describe hpa,scaledobject` |
| Drain blocked | Eviction response | PDB, local storage, singleton | `kubectl get pdb` |
| Azure operation fails | Activity Log and operation status | RBAC, policy, quota, regional support | `az monitor activity-log list` |

Use `./scripts/collect-evidence.ps1 -Incident <name> -Environment <kind|automatic|standard>` during an incident. The script verifies context and redacts common identifiers, but review output before sharing it.
