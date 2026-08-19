# Day 3 security evidence

## Persona authorization matrix

| Persona | Scope | Allowed action/result | Denied action/result | Real sign-in or simulation |
| --- | --- | --- | --- | --- |
| Platform operator | | | | |
| Application operator | | | | |

## Workload Identity flow

Fill each boundary:

```text
namespace/service account:
pod label:
OIDC issuer:
federated audience:
federated subject:
managed identity:
Key Vault role/scope:
SecretProviderClass/object:
application proof:
```

Never include the secret value.

## Connectivity matrix

| Source | Destination/port | Expected | Observed evidence |
| --- | --- | --- | --- |
| Gateway proxy | storefront:8080 | allow | |
| storefront | orders-api:8080 | allow | |
| orders pod | kube-dns:53 | allow | |
| unrelated probe | orders-api:8080 | deny | |
| unrelated probe | arbitrary egress | deny | |

## GitOps

- Public source/branch:
- Ready condition:
- Drift introduced:
- Reconciliation proof:
- Object pruned:
- Ownership boundary:
