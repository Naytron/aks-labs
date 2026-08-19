# Day 3 reference solution

## Workload Identity flow

1. The `orders-api` service account has the user-assigned identity client ID annotation.
2. The pod has `azure.workload.identity/use: "true"`.
3. The webhook projects a signed service-account token.
4. Entra trusts the AKS OIDC issuer, audience, and exact service-account subject.
5. The identity has `Key Vault Secrets User` at the vault.
6. The CSI provider retrieves and mounts `course-api-key`.

Create a disposable secret without committing it:

```powershell
$outputs = Get-Content .aks-labs/standard-outputs.json -Raw | ConvertFrom-Json
New-Item -ItemType Directory .aks-labs -Force | Out-Null
[guid]::NewGuid().ToString() | Set-Content .aks-labs/course-api-key.txt -NoNewline
az keyvault secret set `
  --vault-name $outputs.keyVaultName `
  --name course-api-key `
  --file .aks-labs/course-api-key.txt `
  --output none
Remove-Item .aks-labs/course-api-key.txt
./scripts/deploy-workload.ps1 -Target azure -Environment standard -Stage day3
```

The app reports only a digest prefix:

```powershell
kubectl port-forward -n orders service/storefront 8080:80
Invoke-RestMethod http://localhost:8080/api/config
```

## Authorization test shape

Use Entra groups and Azure Kubernetes Service RBAC roles for durable assignments. For an in-cluster namespace exercise, a Role/RoleBinding may grant application operators verbs on Deployments, ConfigMaps, Services, and pods/log without secrets, RBAC, nodes, or other namespaces.

Evidence must include:

```powershell
kubectl auth can-i update deployments -n orders --as <persona>
kubectl auth can-i get secrets -n orders --as <persona>
kubectl auth can-i update deployments -n kube-system --as <persona>
```

Do not use `cluster-admin` as the test solution.

## Policy matrix

| Source | Destination | Result |
| --- | --- | --- |
| Managed Gateway namespace | storefront:8080 | Allow |
| storefront | orders-api:8080 | Allow |
| orders pods | kube-dns:53 | Allow |
| unrelated orders pod | orders-api:8080 | Deny |
| orders pods | all other egress | Deny |

If Key Vault CSI mounting succeeds with default-deny, remember the provider runs as a node component; the application pod does not directly open the Key Vault connection for the mount.

## Flux

Point reconciliation to `platform/environments/azure-day3` after identity is configured. `prune: true` is safe only when the Kustomization path and ownership boundary are explicit.

```powershell
$repoUrl = "https://github.com/naytron/aks-labs"
./scripts/bootstrap-gitops.ps1 -RepositoryUrl $repoUrl -Branch main -Stage day3
flux get sources git -A
flux get kustomizations -A
flux reconcile kustomization orders-workload --with-source
```

CI validates source. Flux pulls from Git, so the workflow needs no kubeconfig or Azure credential.
