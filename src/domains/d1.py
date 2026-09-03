DOMAIN = {
    "key": "clusters",
    "name": "Clusters & Node Pools",
    "weight": "Foundation",
    "blurb": "Creating and connecting to AKS clusters, system vs user node pools, upgrades and node images, stop/start and pricing tiers, availability zones, and how kubeconfig access actually works. Everything else in this guide assumes the cluster built here.",
}

LABS = [
# ---------------------------------------------------------------- 1.1
{
"id": "1.1",
"title": "Create an AKS cluster and connect with kubectl",
"time": "45 min",
"level": "Foundational",
"objective": "Create the shared AKS cluster, connect kubectl, inspect the system namespace, and deploy the first workload.",
"exam": [
 "AKS manages the <b>control plane</b>; the <b>Free</b> tier has no SLA, while paid tiers add an API-server SLA.",
 "AKS creates a node resource group named like <code>MC_rg-aks-labs_aks-lab_eastus2</code>; do not edit those VMSS/NIC/disk resources directly.",
 "New clusters use <b>managed identity</b> by default; service principals are legacy or explicit and require secret rotation.",
 "The first pool is commonly <code>agentpool</code>, and nodes carry <code>kubernetes.azure.com/agentpool=agentpool</code>.",
 "Azure CNI Overlay uses VNet IPs for nodes and overlay IPs for pods; AKS supports up to <b>250 pods/node</b> where configured.",
 "<b>konnectivity</b> is the current AKS API tunnel component; old <code>tunnelfront</code> references are legacy.",
 "<code>az aks install-cli</code> installs <code>kubectl</code>; <code>az aks get-credentials</code> only writes kubeconfig.",
],
"prereq": "Azure CLI signed in with permission to create <code>rg-aks-labs</code> and an AKS cluster in <code>eastus2</code>.",
"portal": [
 "##Create the cluster",
 "Search <b>Kubernetes services</b> \u2192 <b>+ Create</b> \u2192 <b>Create a Kubernetes cluster</b>.",
 "<b>Basics</b>: Resource group <code>rg-aks-labs</code>, Cluster name <code>aks-lab</code>, Region <code>East US 2</code>, Preset <b>Dev/Test</b>, Pricing tier <b>Free</b>.",
 "<b>Node pools</b>: keep system pool <code>agentpool</code>, VM size <code>Standard_DS2_v2</code>, node count <code>2</code>, autoscaling off.",
 "<b>Networking</b>: choose <b>Azure CNI Overlay</b> and keep default service CIDR, DNS service IP, and Standard load balancer.",
 "<b>Integrations</b>: keep managed identity. <b>Monitoring</b>: skip Container insights for now.",
 "<b>Review + create</b> \u2192 wait for validation \u2192 <b>Create</b>. Expect roughly <code>8-15</code> minutes.",
 "##Connect",
 "Open <code>aks-lab</code> \u2192 <b>Connect</b> \u2192 <b>Cloud Shell</b>; run the generated <code>az aks get-credentials</code> command.",
 "Run <code>kubectl get nodes -o wide</code>, then open <b>Kubernetes resources</b> \u2192 <b>Workloads</b> to see the same API data in the portal.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az group create -n "$RG" -l "$LOC"
az aks create -g "$RG" -n "$AKS" -l "$LOC" \
  --node-count 2 \
  --node-vm-size Standard_DS2_v2 \
  --tier free \
  --generate-ssh-keys \
  --network-plugin azure \
  --network-plugin-mode overlay

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl get nodes -o wide

az aks show -g "$RG" -n "$AKS" \
  --query "{name:name,location:location,tier:sku.tier,nodeRG:nodeResourceGroup,identity:identity.type,k8s:kubernetesVersion}" -o table
""",
"kubectl": r"""# kubectl & YAML
kubectl cluster-info
kubectl get pods -n kube-system -o wide
kubectl get pods -n kube-system | egrep 'coredns|konnectivity|metrics-server|csi|ip-masq' || true
kubectl get nodes --show-labels

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aks-hello
spec:
  replicas: 2
  selector:
    matchLabels:
      app: aks-hello
  template:
    metadata:
      labels:
        app: aks-hello
    spec:
      containers:
      - name: aks-hello
        image: mcr.microsoft.com/azuredocs/aks-helloworld:v1
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: aks-hello
spec:
  selector:
    app: aks-hello
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl rollout status deployment/aks-hello
kubectl get all -l app=aks-hello -o wide
""",
"traps": [
 "Editing resources in the <code>MC_*</code> node resource group is unsupported and can be reconciled over by AKS.",
 "Free tier is not a production SLA answer; it has <b>no</b> financially backed control-plane uptime guarantee.",
 "Deleting the node resource group removes the VMSS, NICs, and disks the cluster needs to function.",
 "SSH keys do not mean direct node SSH is the normal path; use <code>kubectl</code>, <code>az aks command invoke</code>, or approved node-shell workflows.",
],
"cleanup": r"""# Keep the shared cluster. Remove only the sample workload.
kubectl delete service aks-hello --ignore-not-found
kubectl delete deployment aks-hello --ignore-not-found
""",
},
# ---------------------------------------------------------------- 1.2
{
"id": "1.2",
"title": "Add user pools, taints and spot capacity",
"time": "40 min",
"level": "Core",
"objective": "Add regular and spot user pools, protect the system pool with a taint, and schedule pods with selectors and tolerations.",
"exam": [
 "Every AKS cluster needs at least <b>one System</b> pool; system pools host critical add-ons and cannot scale to <code>0</code>.",
 "User pools run application workloads and can scale independently, including to <code>0</code> when no required pods are pinned there.",
 "<code>CriticalAddonsOnly=true:NoSchedule</code> is <b>optional</b> on system pools, not default.",
 "Spot pools must be <b>User</b> mode, have no SLA, are evictable, and get <code>kubernetes.azure.com/scalesetpriority=spot:NoSchedule</code> automatically.",
 "<code>--max-pods</code> is chosen at pool creation; common defaults are kubenet <b>110</b>, Azure CNI classic <b>30</b>, and overlay up to <b>250</b>.",
 "Each node pool maps to a VM Scale Set; use <code>az aks nodepool</code> instead of direct VMSS edits.",
 "Kubernetes labels such as <code>kubernetes.azure.com/agentpool=apps</code> affect scheduling; Azure resource tags do not.",
],
"prereq": "The shared <code>aks-lab</code> cluster exists and your kubeconfig context points to it.",
"portal": [
 "##Add the apps pool",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Node pools</b> \u2192 <b>+ Add node pool</b>.",
 "Name <code>apps</code>, Mode <b>User</b>, VM size <code>Standard_DS2_v2</code>, Node count <code>2</code>, autoscaling off, label <code>workload=apps</code>.",
 "##Add the spot pool",
 "<b>Node pools</b> \u2192 <b>+ Add node pool</b> \u2192 Name <code>spot</code>, Mode <b>User</b>, enable <b>Spot</b>, Eviction policy <b>Delete</b>, Max price <code>-1</code>, Node count <code>1</code>.",
 "##Taint the system pool",
 "Portal coverage for taint editing varies; use <b>Cloud Shell</b> with the CLI command to apply <code>CriticalAddonsOnly=true:NoSchedule</code> to <code>agentpool</code>.",
 "Return to <b>Node pools</b> and compare Mode, Priority, node count, labels, and taints for all three pools.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az aks nodepool add -g "$RG" --cluster-name "$AKS" -n apps \
  --mode User --node-count 2 --node-vm-size Standard_DS2_v2 \
  --labels workload=apps --max-pods 110

az aks nodepool add -g "$RG" --cluster-name "$AKS" -n spot \
  --mode User --priority Spot --eviction-policy Delete --spot-max-price -1 \
  --node-count 1 --node-vm-size Standard_DS2_v2 --labels workload=spot

az aks nodepool update -g "$RG" --cluster-name "$AKS" -n agentpool \
  --node-taints CriticalAddonsOnly=true:NoSchedule

az aks nodepool list -g "$RG" --cluster-name "$AKS" \
  --query "[].{name:name,mode:mode,count:count,priority:scaleSetPriority,maxPods:maxPods,taints:nodeTaints}" -o table
""",
"kubectl": r"""# kubectl & YAML
kubectl get nodes -L kubernetes.azure.com/agentpool,kubernetes.azure.com/scalesetpriority,workload
kubectl describe nodes | egrep 'Name:|Taints:|agentpool|scalesetpriority' || true

kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: spot-demo
spec:
  nodeSelector:
    kubernetes.azure.com/scalesetpriority: spot
  tolerations:
  - key: kubernetes.azure.com/scalesetpriority
    operator: Equal
    value: spot
    effect: NoSchedule
  containers:
  - name: web
    image: nginx:1.27
EOF

kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: apps-demo
spec:
  nodeSelector:
    kubernetes.azure.com/agentpool: apps
  containers:
  - name: web
    image: nginx:1.27
EOF

kubectl get pods spot-demo apps-demo -o wide
kubectl describe pod spot-demo | sed -n '/Node-Selectors:/,/Events:/p'
""",
"traps": [
 "Spot workloads need both a selector/affinity and a toleration; the toleration alone does not attract pods to spot nodes.",
 "Adding the system taint makes ordinary pods <code>Pending</code> unless they target user pools or tolerate the taint.",
 "You cannot scale the only System pool to zero; create a User pool for disposable capacity.",
 "Changing max pods later usually means creating a replacement pool and moving workloads.",
],
"cleanup": r"""kubectl delete pod spot-demo apps-demo --ignore-not-found
# Keep pools for later labs. Optional:
# az aks nodepool delete -g rg-aks-labs --cluster-name aks-lab -n spot --yes
# az aks nodepool delete -g rg-aks-labs --cluster-name aks-lab -n apps --yes
""",
},
# ---------------------------------------------------------------- 1.3
{
"id": "1.3",
"title": "Upgrade Kubernetes and node images",
"time": "40 min",
"level": "Core",
"objective": "Inspect available AKS upgrades, distinguish control-plane, node-pool, and node-image upgrades, and configure maintenance-aware automation.",
"exam": [
 "Node pools can be up to <b>2 minor versions</b> behind the control plane, or <b>3</b> with AKS LTS where supported.",
 "AKS Kubernetes upgrades are one-way; <b>downgrades are not supported</b>.",
 "<code>az aks upgrade --control-plane-only</code> updates the managed API server without upgrading node pools.",
 "<code>az aks nodepool upgrade --node-image-only</code> patches node OS images without changing Kubernetes version.",
 "Node upgrades drain pods and honor PDBs; too-strict PDBs can stall or fail the upgrade when drain cannot evict pods.",
 "<code>--max-surge</code> defaults to about <b>10%</b>; higher values require vCPU and IP quota but reduce maintenance time.",
 "Auto-upgrade channels include <code>none</code>, <code>patch</code>, <code>stable</code>, <code>rapid</code>, and <code>node-image</code>.",
 "Maintenance schedule types include <code>aksManagedAutoUpgradeSchedule</code> and <code>aksManagedNodeOSUpgradeSchedule</code>.",
],
"prereq": "The cluster is healthy and the subscription has quota for any surge nodes used during upgrade.",
"portal": [
 "##Cluster version",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Settings</b> \u2192 <b>Cluster configuration</b>.",
 "Review the current Kubernetes version and upgrade picker. Do not start a production upgrade without a tested target version.",
 "##Node pools",
 "Open <b>Node pools</b> \u2192 select a pool \u2192 review Kubernetes version, node image version, and upgrade options.",
 "##Maintenance windows",
 "Open <b>Settings</b> \u2192 <b>Maintenance configurations</b>. Create separate windows for cluster upgrades and node OS/image upgrades when policy requires it.",
 "During a live upgrade, keep <b>Node pools</b>, <b>Workloads</b>, and Cloud Shell <code>kubectl get nodes -w</code> open.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az aks get-upgrades -g "$RG" -n "$AKS" -o table
az aks get-versions -l "$LOC" -o table

TARGET_VERSION=""
if [ -n "$TARGET_VERSION" ]; then
  az aks upgrade -g "$RG" -n "$AKS" --kubernetes-version "$TARGET_VERSION" --control-plane-only --yes
  az aks nodepool upgrade -g "$RG" --cluster-name "$AKS" -n agentpool \
    --kubernetes-version "$TARGET_VERSION" --max-surge 33% --yes
fi

az aks nodepool get-upgrades -g "$RG" --cluster-name "$AKS" -n agentpool -o table
az aks nodepool upgrade -g "$RG" --cluster-name "$AKS" -n agentpool --node-image-only --max-surge 33% --yes

az aks update -g "$RG" -n "$AKS" --auto-upgrade-channel patch
az aks update -g "$RG" -n "$AKS" --node-os-upgrade-channel SecurityPatch
az aks show -g "$RG" -n "$AKS" --query "{k8s:kubernetesVersion,auto:autoUpgradeProfile.upgradeChannel,nodeOS:autoUpgradeProfile.nodeOSUpgradeChannel}" -o table
""",
"kubectl": r"""# kubectl & YAML
kubectl get nodes -o wide
kubectl get pods -A -o wide

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: upgrade-pdb-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: upgrade-pdb-demo
  template:
    metadata:
      labels:
        app: upgrade-pdb-demo
    spec:
      containers:
      - name: web
        image: nginx:1.27
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: upgrade-pdb-demo
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: upgrade-pdb-demo
EOF

kubectl rollout status deployment/upgrade-pdb-demo
kubectl get pdb upgrade-pdb-demo
kubectl get pods -l app=upgrade-pdb-demo -o wide
# Run while upgrading: kubectl get nodes -w
""",
"traps": [
 "Control-plane-only does not upgrade worker nodes; validate both API and node versions after maintenance.",
 "A single-replica app with <code>minAvailable: 1</code> blocks voluntary eviction and can fail a drain.",
 "Rapid auto-upgrade is not a production stability default; patch or stable is usually the safer answer.",
 "High surge values fail when subnet IPs or regional vCPU quota are insufficient.",
],
"cleanup": r"""kubectl delete pdb upgrade-pdb-demo --ignore-not-found
kubectl delete deployment upgrade-pdb-demo --ignore-not-found
""",
},
# ---------------------------------------------------------------- 1.4
{
"id": "1.4",
"title": "Stop, start, scale and choose tiers",
"time": "30 min",
"level": "Foundational",
"objective": "Pause AKS safely, resume it, scale pools, and select Free, Standard, or Premium based on SLA and support requirements.",
"exam": [
 "<code>az aks stop</code> stops the managed control plane and deallocates nodes; workloads do not run until <code>az aks start</code> completes.",
 "Cluster identity and state are preserved, but dynamic LoadBalancer public IPs are not the same guarantee as static IP resources.",
 "User pools can scale to <code>0</code>; System pools must keep capacity for critical add-ons.",
 "Free tier has <b>no SLA</b>; Standard has <b>99.9%</b>, or <b>99.95%</b> with availability zones where supported.",
 "Premium adds long-term support options, commonly <b>2 years</b> for supported Kubernetes versions.",
 "Documented scale is up to <b>5000 nodes</b> per cluster on Standard tier and <b>1000</b> on Free tier.",
 "Stopped clusters should not be left stopped for very long periods because certificates and platform maintenance can age out.",
],
"prereq": "The shared cluster is running. Do not stop it if other labs are active.",
"portal": [
 "##Power state",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Overview</b>.",
 "Click <b>Stop</b> only in an approved window; click <b>Start</b> and expect several minutes before nodes return to <code>Ready</code>.",
 "##Scale pools",
 "Open <b>Node pools</b> \u2192 select <code>apps</code> \u2192 <b>Scale node pool</b> \u2192 set count <code>1</code>, then return to <code>2</code>.",
 "##Pricing tier",
 "Open <b>Cluster configuration</b> \u2192 compare <b>Free</b>, <b>Standard</b>, and <b>Premium</b>. Use Cloud Shell to verify <code>powerState</code> and tier.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az aks show -g "$RG" -n "$AKS" --query "{state:powerState.code,tier:sku.tier,pools:agentPoolProfiles[].count}" -o json

# Use only when no one needs the lab cluster.
# az aks stop -g "$RG" -n "$AKS"
# az aks start -g "$RG" -n "$AKS"

az aks scale -g "$RG" -n "$AKS" --node-count 2
if az aks nodepool show -g "$RG" --cluster-name "$AKS" -n apps >/dev/null 2>&1; then
  az aks nodepool scale -g "$RG" --cluster-name "$AKS" -n apps --node-count 1
  az aks nodepool scale -g "$RG" --cluster-name "$AKS" -n apps --node-count 2
fi

az aks update -g "$RG" -n "$AKS" --tier standard
az aks update -g "$RG" -n "$AKS" --tier free
""",
"kubectl": r"""# kubectl & YAML
kubectl get nodes -o wide
# During start/scale operations: kubectl get nodes -w

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scale-watch
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scale-watch
  template:
    metadata:
      labels:
        app: scale-watch
    spec:
      containers:
      - name: web
        image: nginx:1.27
EOF

kubectl rollout status deployment/scale-watch
NODE=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl cordon "$NODE"
kubectl drain "$NODE" --ignore-daemonsets --delete-emptydir-data --force
kubectl get pods -l app=scale-watch -o wide
kubectl uncordon "$NODE"
""",
"traps": [
 "Stopping AKS makes the API server and workloads unavailable; it is not the same as scaling one Deployment to zero.",
 "Dynamic Service IPs can change after recreation; use static IP resources for stable inbound endpoints.",
 "Manual drain without <code>--ignore-daemonsets</code> stalls on DaemonSet-managed pods.",
 "Free tier plus zone-spread nodes still does not create a control-plane SLA.",
],
"cleanup": r"""kubectl delete deployment scale-watch --ignore-not-found
""",
},
# ---------------------------------------------------------------- 1.5
{
"id": "1.5",
"title": "Create zone-resilient node pools",
"time": "35 min",
"level": "Advanced",
"objective": "Create a zone-spanning pool, verify zone labels, spread replicas, and identify storage and load-balancer zone implications.",
"exam": [
 "Node-pool zones are set with <code>--zones 1 2 3</code> and are <b>immutable</b>; changing zones requires a replacement pool.",
 "Current topology label is <code>topology.kubernetes.io/zone</code>; beta failure-domain labels are legacy.",
 "Standard Load Balancer supports zonal and zone-redundant front ends; Basic is not the current production AKS answer.",
 "Azure Disk <b>LRS</b> is zonal and pins attached pods to one zone; <b>ZRS</b> disks support cross-zone scenarios where available.",
 "<code>topologySpreadConstraints</code> uses <code>maxSkew</code>, <code>topologyKey</code>, and <code>whenUnsatisfiable</code>.",
 "<code>DoNotSchedule</code> enforces spread; <code>ScheduleAnyway</code> scores spread but still schedules if needed.",
 "A PDB protects voluntary disruption with settings such as <code>minAvailable: 4</code>; it does not survive a full zone outage by itself.",
],
"prereq": "<code>eastus2</code> supports availability zones and you have quota for a three-node user pool.",
"portal": [
 "##Add a zonal pool",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Node pools</b> \u2192 <b>+ Add node pool</b>.",
 "Name <code>zapps</code>, Mode <b>User</b>, VM size <code>Standard_DS2_v2</code>, Node count <code>3</code>, Availability zones <code>1</code>, <code>2</code>, <code>3</code>, label <code>workload=zonal</code>.",
 "After creation, note there is no simple edit path for zones; replacement pools are the migration pattern.",
 "##Verify placement",
 "Use <b>Cloud Shell</b> for the kubectl pane, then open <b>Workloads</b> and confirm six replicas are running.",
 "Inspect disks or load balancers in the node resource group only to read zone settings; do not edit AKS-owned resources there.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az aks nodepool add -g "$RG" --cluster-name "$AKS" -n zapps \
  --mode User --node-count 3 --node-vm-size Standard_DS2_v2 \
  --zones 1 2 3 --labels workload=zonal

az aks nodepool show -g "$RG" --cluster-name "$AKS" -n zapps \
  --query "{name:name,zones:availabilityZones,labels:nodeLabels}" -o json
""",
"kubectl": r"""# kubectl & YAML
kubectl get nodes -L topology.kubernetes.io/zone,kubernetes.azure.com/agentpool,workload

kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zonal-web
spec:
  replicas: 6
  selector:
    matchLabels:
      app: zonal-web
  template:
    metadata:
      labels:
        app: zonal-web
    spec:
      nodeSelector:
        workload: zonal
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: zonal-web
      containers:
      - name: web
        image: nginx:1.27
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: zonal-web
spec:
  minAvailable: 4
  selector:
    matchLabels:
      app: zonal-web
EOF

kubectl rollout status deployment/zonal-web
kubectl get pods -l app=zonal-web -o wide
kubectl get pdb zonal-web
""",
"traps": [
 "You cannot edit a pool from zones 1/2 to 1/2/3; build a new pool and drain workloads.",
 "Zone-spread stateless pods do not fix single-zone LRS disk attachment for stateful pods.",
 "Hard topology spread with too few eligible zones leaves pods <code>Pending</code>.",
 "A PDB controls voluntary evictions, not power, storage, or network loss in a zone.",
],
"cleanup": r"""kubectl delete pdb zonal-web --ignore-not-found
kubectl delete deployment zonal-web --ignore-not-found
# Optional quota recovery:
# az aks nodepool delete -g rg-aks-labs --cluster-name aks-lab -n zapps --yes
""",
},
# ---------------------------------------------------------------- 1.6
{
"id": "1.6",
"title": "Manage kubeconfig and cluster access",
"time": "30 min",
"level": "Core",
"objective": "Merge credentials, switch contexts, understand admin and Entra formats, and use command invoke when direct API access is blocked.",
"exam": [
 "<code>az aks get-credentials</code> merges into <code>~/.kube/config</code>; <code>--overwrite-existing</code> replaces an existing context entry.",
 "<code>KUBECONFIG</code> can point to a separate file for automation or isolated lab work.",
 "<code>kubectl config get-contexts</code>, <code>use-context</code>, and <code>current-context</code> prevent wrong-cluster operations.",
 "<code>--admin</code> downloads local cluster-admin credentials and is blocked when local accounts are disabled.",
 "Entra clusters can use <code>--format azure</code> and <code>kubelogin</code> for exec-auth kubeconfig entries.",
 "<code>az aks command invoke</code> runs inside the cluster and needs <code>Microsoft.ContainerService/managedClusters/runCommand/action</code>.",
 "<code>az aks rotate-certs</code> is disruptive; refresh kubeconfig after rotation.",
],
"prereq": "The shared cluster exists. Install <code>kubelogin</code> if testing Entra exec-auth conversion.",
"portal": [
 "##Connection commands",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Connect</b> and review the generated Azure CLI commands.",
 "Open <b>Access control (IAM)</b> \u2192 <b>My access</b> and confirm you have rights to read the cluster and run command invoke if needed.",
 "Open <b>Settings</b> \u2192 <b>Authentication and authorization</b> and note local account and Azure RBAC settings.",
 "##Locked clusters",
 "For private API servers or firewall restrictions, launch <b>Cloud Shell</b> or use <code>az aks command invoke</code> to run <code>kubectl get nodes</code> from Azure.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl config get-contexts
kubectl config current-context

mkdir -p .kube-lab
az aks get-credentials -g "$RG" -n "$AKS" --file .kube-lab/config --overwrite-existing
KUBECONFIG=.kube-lab/config kubectl get nodes

# Admin credentials may be disabled by policy.
# az aks get-credentials -g "$RG" -n "$AKS" --admin --overwrite-existing

az aks install-cli || true
az aks get-credentials -g "$RG" -n "$AKS" --format azure --overwrite-existing
kubelogin convert-kubeconfig -l azurecli || true

az aks command invoke -g "$RG" -n "$AKS" --command "kubectl get nodes -o wide"
""",
"kubectl": r"""# kubectl & YAML
kubectl config get-contexts
kubectl config current-context
kubectl auth can-i get pods -A
kubectl auth can-i '*' '*' --all-namespaces

kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: lab16-access
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: context-check
  namespace: lab16-access
data:
  cluster: aks-lab
EOF

kubectl get configmap context-check -n lab16-access -o yaml
kubectl delete namespace lab16-access
""",
"traps": [
 "Running destructive kubectl commands before checking <code>current-context</code> damages the wrong cluster.",
 "<code>--admin</code> is not always available and should not replace RBAC-aware Entra access.",
 "Private cluster connection failures can be network path issues even when kubeconfig is correct.",
 "Certificate rotation invalidates old credentials and can cause downtime during the operation.",
],
"cleanup": r"""kubectl delete namespace lab16-access --ignore-not-found
rm -rf .kube-lab
""",
},
]
