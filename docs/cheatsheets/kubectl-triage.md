# kubectl and incident triage

## Safety first

```powershell
kubectl config current-context
kubectl config get-contexts
kubectl get namespace
```

Always state **context + namespace + impact** before a destructive command.

## Evidence ladder

```text
user symptom
  -> Gateway/route
  -> Service/EndpointSlice
  -> pod readiness
  -> container state/logs
  -> scheduling/storage/network/identity
  -> node
  -> AKS/Azure control plane
```

## Core commands

| Question | Command |
| --- | --- |
| What exists? | `kubectl get <type> -n <ns> -o wide` |
| Why is it in this state? | `kubectl describe <type>/<name> -n <ns>` |
| What changed recently? | `kubectl get events -n <ns> --sort-by=.lastTimestamp` |
| What is the process saying? | `kubectl logs -n <ns> <pod> -c <container>` |
| Why did it crash before restart? | `kubectl logs -n <ns> <pod> --previous` |
| Does the Service have backends? | `kubectl get endpointslice -n <ns>` |
| What revision is live? | `kubectl rollout history deployment/<name> -n <ns>` |
| Is rollout progressing? | `kubectl rollout status deployment/<name> -n <ns>` |
| What would apply change? | `kubectl diff -k <path>` |
| May this identity act? | `kubectl auth can-i <verb> <resource> -n <ns>` |
| What fields are valid? | `kubectl explain <resource.path>` |

## Symptom to first evidence

| Symptom | First evidence | Frequent cause |
| --- | --- | --- |
| `Pending` | pod events | resources, taint, affinity, PVC, quota |
| `ImagePullBackOff` | pod events | image/tag, ACR auth, DNS |
| `CrashLoopBackOff` | current + previous logs | config, startup, liveness |
| `OOMKilled` | `lastState.terminated` | low limit or leak |
| Not ready | probe event + EndpointSlice | dependency/readiness path |
| Service failure | selectors + EndpointSlice | zero/wrong backends |
| Gateway failure | Gateway/HTTPRoute conditions | listener/reference/controller |
| CSI mount failure | pod events + provider logs | issuer/subject/RBAC/object |
| No scale | HPA/KEDA conditions | requests/metrics/trigger |
| Drain blocked | eviction response + PDB | insufficient replicas/capacity |

## JSONPath examples

```powershell
kubectl get pod -n orders -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.phase}{"`n"}{end}'
kubectl get pod <pod> -n orders -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'
kubectl get gateway orders -n orders -o jsonpath='{.status.conditions[*]}'
```

## Incident discipline

1. Preserve evidence before restart.
2. Form at least two plausible hypotheses.
3. Run the smallest test that distinguishes them.
4. Change one variable.
5. Prove recovery from the user path and controller state.
6. Separate recovery, root cause, and prevention.

Reference: [kubectl reference](https://kubernetes.io/docs/reference/kubectl/), [AKS troubleshooting](https://learn.microsoft.com/troubleshoot/azure/azure-kubernetes/welcome-azure-kubernetes).
