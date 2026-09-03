DOMAIN = {
    "key": "security",
    "name": "Security & Identity",
    "weight": "Non-negotiable",
    "blurb": "Entra ID sign-in and the two RBAC models, pulling from ACR the supported way, workload identity with federated credentials, secrets from Key Vault via the CSI driver, and guardrails with Azure Policy and Pod Security Admission. The difference between a demo cluster and one you can defend.",
}

LABS = [
# ---------------------------------------------------------------- 5.1
{
"id": "5.1",
"title": "Choose one RBAC model",
"time": "45 min",
"level": "Advanced",
"objective": "Enable Entra ID sign-in, compare Kubernetes RBAC with Azure RBAC for Kubernetes Authorization, and grant one group namespace-scoped access without local admin credentials.",
"exam": [
 "Entra ID on AKS is <b>authentication</b>; authorization is either <b>Kubernetes RBAC</b> objects or <b>Azure RBAC for Kubernetes Authorization</b> role assignments evaluated by AKS.",
 "Enable the Azure RBAC model with <code>az aks update --enable-aad --enable-azure-rbac</code>; Kubernetes RBAC objects can still exist, which makes mixed-mode audits confusing.",
 "Data-plane roles are <b>Azure Kubernetes Service RBAC Reader</b>, <b>Writer</b>, <b>Admin</b>, and <b>Cluster Admin</b>; assign at cluster scope or append <code>/namespaces/&lt;ns&gt;</code>.",
 "<b>Azure Kubernetes Service Cluster User Role</b> is separate: it only grants <code>listClusterUserCredential</code> so a user can run <code>az aks get-credentials</code>.",
 "<code>kubelogin</code> <code>azurecli</code> mode reuses <code>az login</code>; <code>devicecode</code> mode prints a browser code for constrained shells.",
 "<code>--disable-local-accounts</code> removes the certificate-based <code>--admin</code> backdoor that bypasses Entra sign-in and Conditional Access.",
 "Conditional Access applies during token acquisition for the AKS server app; a blocked user cannot get a kubectl token even with an RBAC grant.",
 "Group claims truncate around <b>200 groups</b> and switch to overage/distributed claims; authorization relying on missing group IDs fails.",
],
"prereq": "Shared cluster <code>aks-lab</code> in <code>rg-aks-labs</code>, <code>kubelogin</code>, and rights to update AKS, assign roles, and create or reuse an Entra group.",
"portal": [
 "##Enable Entra sign-in",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Settings</b> \u2192 <b>Cluster configuration</b> and confirm <b>Microsoft Entra ID authentication</b> is enabled.",
 "Open <b>Access control (IAM)</b> and note that <b>Azure Kubernetes Service Cluster User Role</b> controls kubeconfig download, not pod access.",
 "##Azure RBAC for Kubernetes",
 "Open <b>Access control (IAM)</b> \u2192 <b>+ Add</b> \u2192 <b>Add role assignment</b> \u2192 choose <b>Azure Kubernetes Service RBAC Writer</b>.",
 "For namespace scope, use Cloud Shell with the ARM scope suffix <code>/namespaces/lab51</code>; the portal scope picker normally stops at the cluster resource.",
 "##Kubernetes RBAC contrast",
 "Use Cloud Shell to create <code>lab51</code> and apply a RoleBinding whose subject is the Entra group <code>objectId</code>, not the display name.",
 "##Verify without admin",
 "Use <b>Connect</b> \u2192 <b>Azure CLI</b>. Do not use <code>--admin</code>; this lab validates user credentials plus Entra tokens.",
],
"cli": r"""# Azure CLI (bash) — Entra auth and Azure RBAC for Kubernetes
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab51
GROUP_NAME=aks-lab51-writers-$RANDOM

az aks update -g "$RG" -n "$AKS" --enable-aad --enable-azure-rbac
az aks update -g "$RG" -n "$AKS" --disable-local-accounts
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

ME_ID=$(az ad signed-in-user show --query id -o tsv)
az ad group create --display-name "$GROUP_NAME" --mail-nickname "$GROUP_NAME"
GROUP_ID=$(az ad group show --group "$GROUP_NAME" --query id -o tsv)
az ad group member add --group "$GROUP_ID" --member-id "$ME_ID" || true

AKS_ID=$(az aks show -g "$RG" -n "$AKS" --query id -o tsv)
NS_SCOPE="$AKS_ID/namespaces/$NS"
az role assignment create --assignee-object-id "$GROUP_ID" --assignee-principal-type Group \
  --role "Azure Kubernetes Service RBAC Writer" --scope "$NS_SCOPE"
az role assignment create --assignee-object-id "$GROUP_ID" --assignee-principal-type Group \
  --role "Azure Kubernetes Service Cluster User Role" --scope "$AKS_ID" || true

az role assignment list --scope "$NS_SCOPE" \
  --query "[].{principal:principalName, role:roleDefinitionName, scope:scope}" -o table
kubelogin convert-kubeconfig -l devicecode
kubectl auth can-i create deployments -n "$NS"
""",
"kubectl": r"""# kubectl & YAML — Kubernetes RBAC model using the same Entra group
NS=lab51
GROUP_ID=${GROUP_ID:-00000000-0000-0000-0000-000000000000}

kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: namespace-writer
  namespace: $NS
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log", "services", "configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: entra-group-writer
  namespace: $NS
subjects:
- kind: Group
  name: "$GROUP_ID"
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: namespace-writer
  apiGroup: rbac.authorization.k8s.io
EOF
kubectl auth can-i create deployments -n "$NS"
kubectl auth can-i create clusterroles
kubectl get role,rolebinding -n "$NS"
""",
"traps": [
 "Granting <b>Cluster User Role</b> and expecting pod access fails; it only lets the user download cluster user credentials.",
 "Assigning <b>RBAC Writer</b> at cluster scope grants all namespaces; append <code>/namespaces/lab51</code> for least privilege.",
 "Leaving local accounts enabled means <code>--admin</code> credentials bypass Entra ID, Conditional Access, and group review.",
 "Kubernetes RoleBinding subjects for Entra groups use immutable <b>objectId</b>, not group display name.",
 "Overage at about <b>200 groups</b> can omit group IDs from tokens, so group-based authorization appears to fail.",
],
"cleanup": r"""RG=rg-aks-labs
AKS=aks-lab
NS=lab51
AKS_ID=$(az aks show -g "$RG" -n "$AKS" --query id -o tsv)
NS_SCOPE="$AKS_ID/namespaces/$NS"
kubectl delete ns "$NS" --ignore-not-found
if [ -n "$GROUP_ID" ]; then
  az role assignment delete --assignee "$GROUP_ID" --role "Azure Kubernetes Service RBAC Writer" --scope "$NS_SCOPE" || true
  az role assignment delete --assignee "$GROUP_ID" --role "Azure Kubernetes Service Cluster User Role" --scope "$AKS_ID" || true
fi
if [ -n "$GROUP_NAME" ]; then az ad group delete --group "$GROUP_NAME" || true; fi
""",
},
# ---------------------------------------------------------------- 5.2
{
"id": "5.2",
"title": "Pull images without secrets",
"time": "35 min",
"level": "Foundational",
"objective": "Create an Azure Container Registry, attach it to AKS the supported way, import and build images, and diagnose ImagePullBackOff from events.",
"exam": [
 "<code>az aks update --attach-acr</code> grants <b>AcrPull</b> to the AKS <b>kubelet identity</b>, not the control-plane managed identity.",
 "ACR Basic includes <b>10 GiB</b>, Standard <b>100 GiB</b>, and Premium <b>500 GiB</b> plus private link and geo-replication.",
 "<code>az acr build</code> builds in ACR Tasks and pushes directly to the registry; no local Docker daemon is required.",
 "<code>az acr import</code> copies public images server-side and avoids Docker Hub throttling or node internet pulls.",
 "After attach, pods pull <code>&lt;acr&gt;.azurecr.io/repo:tag</code> with no <code>imagePullSecrets</code> in the manifest.",
 "<code>kubectl describe pod</code> events distinguish <b>401/403</b> auth failures from <b>manifest unknown</b> tag failures.",
 "<code>az aks check-acr</code> validates DNS, network path, registry existence, and AcrPull assignment from the cluster.",
 "Cross-tenant scenarios usually need a <code>docker-registry</code> secret, service principal, or different identity path instead of attach-acr.",
 "The image cleaner add-on <code>--enable-image-cleaner</code> removes stale node images; it does not repair auth or bad tags.",
],
"prereq": "Shared cluster <code>aks-lab</code>, Azure CLI rights to create ACR and assign roles, and namespace <code>lab52</code>.",
"portal": [
 "##Create ACR",
 "Search <b>Container registries</b> \u2192 <b>+ Create</b> \u2192 RG <code>rg-aks-labs</code>, Name <code>acrakslab&lt;unique&gt;</code>, Region <code>East US 2</code>, SKU <b>Basic</b> \u2192 <b>Create</b>.",
 "Open the registry \u2192 <b>Repositories</b>; it stays empty until import or build completes.",
 "##Attach to AKS",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Settings</b> \u2192 <b>Container registries</b> \u2192 <b>Attach registry</b> \u2192 select the ACR \u2192 <b>Save</b>.",
 "Open ACR \u2192 <b>Access control (IAM)</b> \u2192 <b>Role assignments</b> and find <b>AcrPull</b> on the kubelet identity.",
 "##Diagnose pulls",
 "Use <b>Cloud Shell</b> for <code>az aks check-acr</code> and <code>kubectl describe pod</code>; pod event text is the source of truth.",
],
"cli": r"""# Azure CLI (bash) — ACR attach, import, build, validation
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab52
ACR=acrakslab$RANDOM

az acr create -g "$RG" -n "$ACR" -l "$LOC" --sku Basic
az aks update -g "$RG" -n "$AKS" --attach-acr "$ACR"
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

az acr import -n "$ACR" --source mcr.microsoft.com/azuredocs/aks-helloworld:v1 --image aks-helloworld:v1
az acr repository list -n "$ACR" -o table
az aks check-acr -g "$RG" -n "$AKS" --acr "$ACR.azurecr.io"

mkdir -p lab52-build
cat > lab52-build/Dockerfile <<'EOF'
FROM nginx:1.27
RUN printf 'hello from acr tasks\n' > /usr/share/nginx/html/index.html
EOF
az acr build -r "$ACR" -t lab52-nginx:v1 lab52-build
az acr repository show-tags -n "$ACR" --repository lab52-nginx -o table
""",
"kubectl": r"""# kubectl & YAML — pull without imagePullSecrets
NS=lab52
ACR=${ACR:-acrakslab12345}
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: acr-hello
  namespace: $NS
spec:
  replicas: 2
  selector:
    matchLabels:
      app: acr-hello
  template:
    metadata:
      labels:
        app: acr-hello
    spec:
      containers:
      - name: web
        image: $ACR.azurecr.io/aks-helloworld:v1
        ports:
        - containerPort: 80
EOF
kubectl rollout status deploy/acr-hello -n "$NS" --timeout=180s
kubectl describe pod -n "$NS" -l app=acr-hello | sed -n '/Events:/,$p'
kubectl run bad-tag -n "$NS" --image="$ACR.azurecr.io/aks-helloworld:no-such-tag" --restart=Never || true
sleep 20
kubectl describe pod bad-tag -n "$NS" | sed -n '/Events:/,$p'
""",
"traps": [
 "Granting <b>AcrPull</b> to the cluster identity leaves pulls failing because kubelet, not the control plane, pulls images.",
 "Adding <code>imagePullSecrets</code> after attach can hide the real configuration and later fail when a password expires.",
 "<b>401/403</b> means auth or network path; <b>manifest unknown</b> usually means repository or tag typo.",
 "ACR names are globally unique and lowercase alphanumeric only; hyphens and underscores fail validation.",
 "Private endpoint ACR still needs node DNS and network reachability; role assignment alone cannot cross broken DNS.",
],
"cleanup": r"""RG=rg-aks-labs
AKS=aks-lab
NS=lab52
kubectl delete ns "$NS" --ignore-not-found
if [ -n "$ACR" ]; then
  az aks update -g "$RG" -n "$AKS" --detach-acr "$ACR" || true
  az acr delete -g "$RG" -n "$ACR" --yes || true
fi
rm -rf lab52-build
""",
},
# ---------------------------------------------------------------- 5.3
{
"id": "5.3",
"title": "Exchange pod tokens for Azure tokens",
"time": "50 min",
"level": "Advanced",
"objective": "Use AKS workload identity so a pod reads a Key Vault secret through a federated credential instead of a stored secret.",
"exam": [
 "Workload identity replaces retired Azure AD pod identity; enable it with <code>--enable-oidc-issuer --enable-workload-identity</code>.",
 "The federated credential subject must exactly be <code>system:serviceaccount:&lt;namespace&gt;:&lt;serviceaccount&gt;</code>.",
 "ServiceAccount annotation <code>azure.workload.identity/client-id</code> uses managed identity <b>clientId</b>, not objectId or resourceId.",
 "Pod label <code>azure.workload.identity/use: \"true\"</code> triggers webhook injection of <code>AZURE_FEDERATED_TOKEN_FILE</code> and related env vars.",
 "The projected token audience is <code>api://AzureADTokenExchange</code>; Entra exchanges it for an Azure access token.",
 "Key Vault RBAC reads need <b>Key Vault Secrets User</b>; <b>Reader</b> sees vault metadata but not secret values.",
 "A user-assigned managed identity supports up to <b>20</b> federated identity credentials.",
 "The OIDC issuer URL is per cluster and changes after cluster recreation, invalidating old federated credentials.",
],
"prereq": "Shared cluster <code>aks-lab</code>, rights to create a user-assigned identity and Key Vault, and namespace <code>lab53</code>.",
"portal": [
 "##Confirm the issuer",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Properties</b> and confirm the <b>OIDC issuer URL</b> exists after CLI enablement.",
 "Open <b>Managed identities</b> \u2192 lab identity \u2192 <b>Federated credentials</b> and verify Subject <code>system:serviceaccount:lab53:kv-reader</code>.",
 "##Grant vault access",
 "Open <b>Key vaults</b> \u2192 lab vault \u2192 <b>Access control (IAM)</b> \u2192 confirm <b>Key Vault Secrets User</b> is assigned to the identity.",
 "Open <b>Secrets</b> \u2192 <code>lab53-secret</code>; the pod reads this value without a Kubernetes Secret.",
 "##Verify in Cloud Shell",
 "Run <code>kubectl exec</code> and print <code>AZURE_FEDERATED_TOKEN_FILE</code>; do not copy token contents into tickets or chat.",
],
"cli": r"""# Azure CLI (bash) — identity, federated credential, Key Vault RBAC
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab53
SA=kv-reader
ID=mi-aks-lab53-$RANDOM
KV=kvakslab53$RANDOM
SECRET=lab53-secret

az aks update -g "$RG" -n "$AKS" --enable-oidc-issuer --enable-workload-identity
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
az identity create -g "$RG" -n "$ID" -l "$LOC"
CLIENT_ID=$(az identity show -g "$RG" -n "$ID" --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -g "$RG" -n "$ID" --query principalId -o tsv)
ISSUER=$(az aks show -g "$RG" -n "$AKS" --query oidcIssuerProfile.issuerUrl -o tsv)

az keyvault create -g "$RG" -n "$KV" -l "$LOC" --enable-rbac-authorization true
az keyvault secret set --vault-name "$KV" -n "$SECRET" --value "workload-identity-secret-v1"
KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)
az role assignment create --assignee-object-id "$PRINCIPAL_ID" --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$KV_ID"
az identity federated-credential create -g "$RG" --identity-name "$ID" --name fc-lab53 \
  --issuer "$ISSUER" --subject "system:serviceaccount:$NS:$SA" --audience api://AzureADTokenExchange
""",
"kubectl": r"""# kubectl & YAML — annotated service account and Azure CLI pod
NS=lab53
SA=kv-reader
CLIENT_ID=${CLIENT_ID:-00000000-0000-0000-0000-000000000000}
KV=${KV:-kvakslab5312345}
SECRET=lab53-secret
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SA
  namespace: $NS
  annotations:
    azure.workload.identity/client-id: "$CLIENT_ID"
---
apiVersion: v1
kind: Pod
metadata:
  name: wi-reader
  namespace: $NS
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: $SA
  containers:
  - name: azure-cli
    image: mcr.microsoft.com/azure-cli:2.63.0
    command: ["/bin/sh", "-c", "sleep 3600"]
EOF
kubectl wait pod/wi-reader -n "$NS" --for=condition=Ready --timeout=180s
kubectl exec -n "$NS" wi-reader -- printenv | grep '^AZURE_'
kubectl exec -n "$NS" wi-reader -- sh -c 'az login --service-principal -u "$AZURE_CLIENT_ID" -t "$AZURE_TENANT_ID" --federated-token "$(cat $AZURE_FEDERATED_TOKEN_FILE)" >/dev/null && az keyvault secret show --vault-name '"$KV"' --name '"$SECRET"' --query value -o tsv'
""",
"traps": [
 "Using <b>objectId</b> in the service account annotation fails; use the identity <b>clientId</b>.",
 "Forgetting the pod label means no injected token file and no Azure workload identity environment variables.",
 "Recreated clusters have new OIDC issuers, so old federated credentials stop matching.",
 "Key Vault <b>Reader</b> cannot read secret values; use <b>Key Vault Secrets User</b> for RBAC vaults.",
 "One identity has only <b>20</b> federated credentials, so plan identities by app or environment.",
],
"cleanup": r"""RG=rg-aks-labs
NS=lab53
kubectl delete ns "$NS" --ignore-not-found
if [ -n "$KV" ]; then az keyvault delete -g "$RG" -n "$KV" || true; az keyvault purge -n "$KV" --location eastus2 || true; fi
if [ -n "$ID" ]; then az identity delete -g "$RG" -n "$ID" || true; fi
""",
},
# ---------------------------------------------------------------- 5.4
{
"id": "5.4",
"title": "Mount secrets as files",
"time": "40 min",
"level": "Core",
"objective": "Enable the Key Vault CSI driver, mount a secret as a file, rotate the value, and understand synced Kubernetes Secret behavior.",
"exam": [
 "Enable the add-on with <code>az aks enable-addons --addons azure-keyvault-secrets-provider</code>; it installs Secrets Store CSI driver and Azure provider.",
 "The add-on creates a user-assigned identity named like <code>azurekeyvaultsecretsprovider-&lt;cluster&gt;</code>; grant that identity vault access unless using workload identity.",
 "<code>SecretProviderClass</code> references Key Vault <b>secrets</b>, <b>keys</b>, or <b>certs</b>; optional <code>objectVersion</code> pins a version.",
 "Mounted values are <b>files</b> on a CSI volume, not environment variables and not Kubernetes Secrets by default.",
 "<code>secretObjects</code> sync creates a real Kubernetes Secret only while at least <b>one pod</b> mounts the volume.",
 "Secret rotation uses <code>--enable-secret-rotation</code>; default poll interval is <b>2m</b> and mounted files update automatically.",
 "Environment variables sourced from synced Secrets require pod restart; use a reloader controller if apps need automatic restarts.",
 "RBAC-enabled vaults need <b>Key Vault Secrets User</b>; legacy vaults need access policy <b>Get</b> on secrets.",
],
"prereq": "Shared cluster <code>aks-lab</code>, Key Vault creation rights, and namespace <code>lab54</code>.",
"portal": [
 "##Enable the provider",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Extensions + applications</b> and verify <b>Azure Key Vault Secrets Provider</b> after CLI enablement.",
 "Open the managed resource group \u2192 <b>Managed identities</b> and find <code>azurekeyvaultsecretsprovider-aks-lab</code>.",
 "##Grant access",
 "Open <b>Key vaults</b> \u2192 lab vault \u2192 <b>Access control (IAM)</b> \u2192 <b>+ Add role assignment</b> \u2192 <b>Key Vault Secrets User</b> \u2192 add the provider identity.",
 "##Observe rotation",
 "Open the secret \u2192 <b>New Version</b> \u2192 set a new value. In Cloud Shell, run <code>kubectl exec</code> until the mounted file changes within about 2 minutes.",
],
"cli": r"""# Azure CLI (bash) — enable provider and create a vault secret
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab54
KV=kvakslab54$RANDOM
SECRET=lab54-message

az aks enable-addons -g "$RG" -n "$AKS" --addons azure-keyvault-secrets-provider
az aks update -g "$RG" -n "$AKS" --enable-secret-rotation --rotation-poll-interval 2m
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
az keyvault create -g "$RG" -n "$KV" -l "$LOC" --enable-rbac-authorization true
az keyvault secret set --vault-name "$KV" -n "$SECRET" --value "secret-version-one"
ADDON_OBJECT_ID=$(az aks show -g "$RG" -n "$AKS" --query addonProfiles.azureKeyvaultSecretsProvider.identity.objectId -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv)
az role assignment create --assignee-object-id "$ADDON_OBJECT_ID" --assignee-principal-type ServicePrincipal \
  --role "Key Vault Secrets User" --scope "$KV_ID"
""",
"kubectl": r"""# kubectl & YAML — SecretProviderClass, file mount, and sync
NS=lab54
KV=${KV:-kvakslab5412345}
SECRET=lab54-message
TENANT_ID=${TENANT_ID:-00000000-0000-0000-0000-000000000000}
kubectl apply -f - <<EOF
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: kv-file-sync
  namespace: $NS
spec:
  provider: azure
  secretObjects:
  - secretName: synced-kv-secret
    type: Opaque
    data:
    - objectName: $SECRET
      key: message
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "true"
    keyvaultName: $KV
    tenantId: $TENANT_ID
    objects: |
      array:
        - |
          objectName: $SECRET
          objectType: secret
EOF
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: kv-reader
  namespace: $NS
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["/bin/sh", "-c", "while true; do date; cat /mnt/secrets-store/$SECRET; sleep 30; done"]
    volumeMounts:
    - name: secrets-store
      mountPath: /mnt/secrets-store
      readOnly: true
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: kv-file-sync
EOF
kubectl wait pod/kv-reader -n "$NS" --for=condition=Ready --timeout=180s
kubectl exec -n "$NS" kv-reader -- cat "/mnt/secrets-store/$SECRET"
kubectl get secret synced-kv-secret -n "$NS" -o jsonpath='{.data.message}' | base64 -d; echo
az keyvault secret set --vault-name "$KV" -n "$SECRET" --value "secret-version-two"
kubectl exec -n "$NS" kv-reader -- sh -c "for i in 1 2 3 4 5; do date; cat /mnt/secrets-store/$SECRET; sleep 30; done"
""",
"traps": [
 "<code>secretObjects</code> does nothing until a pod mounts the SecretProviderClass volume.",
 "Pinning <code>objectVersion</code> prevents latest-version rotation from appearing in the mounted file.",
 "Mounted files rotate, but environment variables from synced Secrets stay old until restart.",
 "Granting access to the cluster identity does not help the add-on identity or workload identity path.",
 "CSI means file delivery without code change; direct SDK plus workload identity means native Azure client behavior.",
],
"cleanup": r"""RG=rg-aks-labs
NS=lab54
kubectl delete ns "$NS" --ignore-not-found
if [ -n "$KV" ]; then az keyvault delete -g "$RG" -n "$KV" || true; az keyvault purge -n "$KV" --location eastus2 || true; fi
""",
},
# ---------------------------------------------------------------- 5.5
{
"id": "5.5",
"title": "Block unsafe pods early",
"time": "45 min",
"level": "Advanced",
"objective": "Use Pod Security Admission for immediate namespace guardrails and Azure Policy for managed Gatekeeper audit and deny controls.",
"exam": [
 "The Azure Policy add-on is managed <b>Gatekeeper v3</b>; enable it with <code>az aks enable-addons --addons azure-policy</code>.",
 "Kubernetes policy effects include <b>audit</b>, <b>deny</b>, and <b>disabled</b>; parameters include <code>excludedNamespaces</code> such as <code>kube-system</code>.",
 "The built-in initiative <b>Kubernetes cluster pod security baseline standards</b> should be assigned in Audit before Deny.",
 "Policy assignment sync commonly takes about <b>15 minutes</b>; full compliance scans can take up to <b>24h</b>.",
 "Pod Security Admission uses labels <code>pod-security.kubernetes.io/enforce</code>, <code>audit</code>, and <code>warn</code> with levels <code>privileged</code>, <code>baseline</code>, <code>restricted</code>.",
 "Pin rule versions with <code>pod-security.kubernetes.io/enforce-version</code> to avoid surprise behavior after cluster upgrades.",
 "Restricted requires <code>runAsNonRoot</code>, <code>seccompProfile: RuntimeDefault</code>, dropping <code>ALL</code> capabilities, and no privilege escalation.",
 "Deployment safeguards and managed best-practice warnings catch risky AKS settings but do not replace pod admission control.",
],
"prereq": "Shared cluster <code>aks-lab</code>, rights to enable add-ons and create Azure Policy assignments, and namespace <code>lab55</code>.",
"portal": [
 "##Azure Policy",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Extensions + applications</b> and confirm <b>Azure Policy</b> after CLI enablement.",
 "Open <b>Policy</b> \u2192 <b>Definitions</b> \u2192 search <code>Kubernetes cluster pod security baseline standards</code> and inspect <code>excludedNamespaces</code>.",
 "Open <b>Policy</b> \u2192 <b>Assignments</b> \u2192 <b>Assign initiative</b> \u2192 Scope <code>rg-aks-labs</code> \u2192 Effect <b>Audit</b> \u2192 <b>Create</b>.",
 "Move to <b>Deny</b> only after violations and exclusions are understood; enforcement is not instant.",
 "##Pod Security Admission",
 "Open <b>Cloud Shell</b> and label <code>lab55</code> with <code>enforce=restricted</code>; PSA blocks immediately at Kubernetes admission.",
],
"cli": r"""# Azure CLI (bash) — enable policy and create an audit assignment
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab55
ASSIGN=aks-lab55-baseline-audit

az aks enable-addons -g "$RG" -n "$AKS" --addons azure-policy
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
RG_ID=$(az group show -n "$RG" --query id -o tsv)
INITIATIVE=$(az policy set-definition list --query "[?displayName=='Kubernetes cluster pod security baseline standards'].id | [0]" -o tsv)
az policy assignment create --name "$ASSIGN" --display-name "AKS lab pod security baseline audit" \
  --scope "$RG_ID" --policy-set-definition "$INITIATIVE" \
  --params '{"effect":{"value":"Audit"},"excludedNamespaces":{"value":["kube-system","gatekeeper-system"]}}' || true
az aks show -g "$RG" -n "$AKS" --query addonProfiles.azurepolicy.enabled -o tsv
""",
"kubectl": r"""# kubectl & YAML — PSA block and compliant replacement
NS=lab55
kubectl label ns "$NS" pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=latest \
  pod-security.kubernetes.io/audit=restricted pod-security.kubernetes.io/warn=restricted --overwrite
kubectl apply -f - <<EOF || true
apiVersion: v1
kind: Pod
metadata:
  name: privileged-fail
  namespace: $NS
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      privileged: true
EOF
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pass
  namespace: $NS
spec:
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    securityContext:
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop: ["ALL"]
EOF
kubectl wait pod/restricted-pass -n "$NS" --for=condition=Ready --timeout=180s
kubectl get events -n "$NS" --sort-by=.lastTimestamp
""",
"traps": [
 "Azure Policy is not instant; PSA blocks immediately, while Gatekeeper sync can take about <b>15 minutes</b>.",
 "Starting with Deny cluster-wide can break controllers; Audit first, then narrow Deny and exclusions.",
 "Forgetting <code>excludedNamespaces</code> can deny system or add-on pods and cause an outage.",
 "Restricted PSA blocks root defaults, missing seccomp, added capabilities, and privilege escalation.",
 "Malformed custom <code>ConstraintTemplate</code> Rego can block production creates; test constraints in Audit first.",
],
"cleanup": r"""RG=rg-aks-labs
NS=lab55
ASSIGN=aks-lab55-baseline-audit
RG_ID=$(az group show -n "$RG" --query id -o tsv)
kubectl delete ns "$NS" --ignore-not-found
az policy assignment delete --name "$ASSIGN" --scope "$RG_ID" || true
""",
},
]
