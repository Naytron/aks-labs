# Platform configuration

- `base`: portable workload resources with restricted pod security.
- `environments/kind`: local NodePort overlay for Day 1.
- `environments/azure-day2`: base workload plus Gateway API.
- `environments/azure-day3`: Day 2 plus namespace governance, NetworkPolicy, Workload Identity, and Key Vault CSI.
- `environments/azure-day4`: Day 3 plus Azure managed Prometheus objects.
- `environments/azure` and `azure-identity`: compatibility aliases for Day 2 and Day 3.
- `components/identity`: opt-in Workload Identity and Key Vault CSI integration; replace placeholders before use.
- `components/scaling`: mutually exclusive HPA/KEDA examples plus VPA recommendation mode.
- `gitops`: Flux reconciliation entry point.

Azure stage manifests keep environment-specific non-secret values as `${...}` placeholders. Direct deployment resolves them from ignored deployment outputs; managed Flux resolves them from the cluster-local `flux-system/course-values` ConfigMap created by `bootstrap-gitops.ps1`. Do not commit tenant, subscription, or generated deployment identifiers.

Render before applying:

```powershell
kubectl kustomize platform/environments/kind
kubectl kustomize platform/environments/azure-day2
kubectl kustomize platform/environments/azure-day3
kubectl kustomize platform/environments/azure-day4
```

Do not apply both the HPA and KEDA `ScaledObject` to the same target. KEDA creates an HPA and the controllers would compete.
