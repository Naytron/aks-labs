# Identity, RBAC, secrets, and network security

## Identity and authorization layers

| Layer | Question | Course mechanism |
| --- | --- | --- |
| Human authentication | Who is calling? | Microsoft Entra |
| Azure management authorization | May they manage AKS/Azure resources? | Azure RBAC |
| Kubernetes authorization | May they act on cluster objects? | Azure RBAC for Kubernetes |
| Pod identity | Which Azure identity may this workload use? | Workload Identity |
| Secret data access | May that identity read this object? | Key Vault data-plane RBAC |

Do not treat subscription Owner as Entra directory administration.

## Workload Identity flow

```text
service account annotation + pod label
        -> projected signed token
        -> AKS OIDC issuer
        -> federated credential checks issuer/audience/subject
        -> short-lived Entra token
        -> Key Vault RBAC
        -> CSI provider mounts secret
```

The subject must exactly match:

```text
system:serviceaccount:<namespace>:<service-account>
```

## Secret rules

- Never commit a secret, kubeconfig, private key, or rendered secret value.
- Do not use a client secret in a pod when Workload Identity is available.
- Kubernetes Secret is not equivalent to Key Vault.
- Mount only required objects, read-only, into the required pod.
- Prove mount state without printing secret content.
- Key Vault purge protection stays enabled.

## Defense-in-depth controls

| Control | Protects against | Does not replace |
| --- | --- | --- |
| Pod Security Admission | Privileged/unsafe pod configuration | Image scanning or network policy |
| ResourceQuota/LimitRange | Namespace resource abuse/defaults | Node capacity planning |
| NetworkPolicy | Unauthorized pod traffic | Identity or TLS |
| Azure Policy | Admission/governance consistency | Runtime detection |
| Image digest/signature | Supply-chain tampering | Vulnerability patching |
| Entra/RBAC | Unauthorized actions | Network isolation |

## Default-deny traffic checklist

1. Deny ingress and egress by default.
2. Allow DNS to kube-dns.
3. Allow Gateway listener traffic.
4. Allow Gateway -> storefront.
5. Allow storefront -> orders-api in both ingress and egress directions.
6. Allow managed Prometheus -> metrics ports.
7. Test an allowed source and an unrelated denied source.

## Human-access test

Use real instructor-prepared groups/accounts for authentication tests. `kubectl auth can-i --as` is an authorization simulation and must be labeled as such.

References: [AKS security concepts](https://learn.microsoft.com/azure/aks/concepts-security), [Workload Identity](https://learn.microsoft.com/azure/aks/workload-identity-overview), [Key Vault CSI identity](https://learn.microsoft.com/azure/aks/csi-secrets-store-identity-access), [NetworkPolicy](https://learn.microsoft.com/azure/aks/use-network-policies).
