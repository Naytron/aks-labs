DOMAIN = {
    "key": "storage",
    "name": "Storage",
    "weight": "Stateful workloads",
    "blurb": "The CSI drivers for Azure Disks, Files and Blob, storage classes and PVC binding, volume expansion, snapshots and clones, and StatefulSets with per-pod volumes. What you must know before running anything stateful on AKS.",
}

LABS = [
# ---------------------------------------------------------------- 4.1
{
"id": "4.1",
"title": "Persist data on Azure Disks",
"time": "40 min",
"level": "Core",
"objective": "Create Azure Disk PVCs with built-in and custom storage classes, prove pod rescheduling preserves data, and expand a volume online.",
"exam": [
 "Azure Disk CSI built-in classes include <code>managed-csi</code> for Standard SSD and <code>managed-csi-premium</code> for Premium SSD; <code>kubectl get storageclass</code> is the source of truth for your cluster defaults.",
 "The key Azure Disk fact: an Azure Disk is <b>ReadWriteOnce</b> and attaches to one node at a time, so it is for single-writer pods, not shared multi-pod file storage.",
 "<code>volumeBindingMode: WaitForFirstConsumer</code> delays disk creation until a pod is scheduled, which places the disk in the pod's zone and avoids zone mismatch failures.",
 "<code>Immediate</code> binding can create a disk before the scheduler chooses a node; in zonal clusters this can pin the PVC to a zone with no available pod capacity.",
 "Default reclaim policy is commonly <code>Delete</code>: deleting the PVC deletes the underlying managed disk. Use <code>Retain</code> when data must survive PVC deletion.",
 "Expansion requires <code>allowVolumeExpansion: true</code>; you can grow from 4Gi to 8Gi online, but Kubernetes does not shrink PVCs.",
 "Custom disk classes can set <code>skuName: Premium_ZRS</code> for zone-redundant disks where region and AKS support allow it.",
 "VM size limits cap disk count: for example, <code>Standard_DS2_v2</code> supports <b>8</b> data disks, which can cap how many RWO PVC pods fit on one node.",
],
"prereq": "Shared cluster <code>aks-lab</code> in <code>rg-aks-labs</code>. Namespace <code>lab41</code> is created and deleted by this lab.",
"portal": [
 "##Storage classes and PVCs",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Storage</b> \u2192 <b>Storage classes</b>. Confirm disk CSI classes such as <code>managed-csi</code> and <code>managed-csi-premium</code> and note the default marker.",
 "Open <b>Storage</b> \u2192 <b>Persistent volume claims</b> \u2192 namespace <code>lab41</code>. Watch <code>disk-pvc</code> move from Pending to Bound only after the pod is scheduled when using WaitForFirstConsumer.",
 "##Azure managed disk",
 "Open the cluster node resource group <code>MC_*</code> \u2192 <b>Disks</b>. Find the disk created for the PVC and note size, SKU and zone.",
 "Do not resize the disk directly in the portal. Edit the PVC requested storage so Kubernetes and the CSI driver perform expansion consistently.",
 "##Reclaim policy",
 "Inspect the PV from kubectl and compare its reclaim policy with the StorageClass. Portal deletion of the managed disk behind a Bound PV causes pod mount failures.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab41

az aks get-credentials -g $RG -n $AKS --overwrite-existing
NODE_RG=$(az aks show -g $RG -n $AKS --query nodeResourceGroup -o tsv)
echo "Node resource group: $NODE_RG"

kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -
kubectl get storageclass

# Disk inventory before the lab.
az disk list -g $NODE_RG --query '[].{name:name, size:diskSizeGb, sku:sku.name, zone:zones[0]}' -o table""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab41

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f - <<EOF
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: premium-zrs-lab41
provisioner: disk.csi.azure.com
parameters:
  skuName: Premium_ZRS
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
EOF

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: disk-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: managed-csi
  resources:
    requests:
      storage: 4Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: writer
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "echo first-write > /data/message.txt && sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: disk-pvc
EOF

kubectl wait --for=condition=Ready pod/writer -n $NS --timeout=180s
kubectl exec -n $NS writer -- cat /data/message.txt
kubectl get pvc,pv -n $NS -o wide

kubectl delete pod writer -n $NS
kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: reader
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "cat /data/message.txt && sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: disk-pvc
EOF
kubectl wait --for=condition=Ready pod/reader -n $NS --timeout=180s
kubectl logs -n $NS reader

# Online expansion: grow only upward.
kubectl patch pvc disk-pvc -n $NS -p '{"spec":{"resources":{"requests":{"storage":"8Gi"}}}}'
kubectl get pvc disk-pvc -n $NS -w""",
"traps": [
 "Using Azure Disk for a multi-replica Deployment that needs shared writes fails because the access mode is RWO and the disk can attach to only one node.",
 "Immediate binding can strand a disk in the wrong availability zone; WaitForFirstConsumer lets the scheduler pick the node and the CSI driver create the disk in that zone.",
 "Deleting a PVC with reclaim policy <code>Delete</code> deletes the managed disk, so a namespace cleanup can be a data-destruction event.",
 "PVC expansion is one-way; lowering the requested size is rejected and direct portal shrink is not supported.",
 "Disk attach limits are per VM size, so pending pods with attach errors may indicate node SKU limits rather than storage class failure.",
],
"cleanup": r"""# Delete only objects created by this lab.
NS=lab41
kubectl delete ns $NS --ignore-not-found
kubectl delete storageclass premium-zrs-lab41 --ignore-not-found""",
},
# ---------------------------------------------------------------- 4.2
{
"id": "4.2",
"title": "Share storage with Files and Blob",
"time": "40 min",
"level": "Core",
"objective": "Mount one Azure Files RWX claim into multiple pods, verify shared writes, and understand when Blob CSI is a better fit than SMB files.",
"exam": [
 "<code>azurefile-csi</code> provisions Azure Files over SMB and supports <b>ReadWriteMany</b>, which lets multiple pods mount the same share concurrently.",
 "Azure Files SMB is convenient for shared config and simple content, but metadata-heavy workloads can be slow because every stat/list operation crosses the network.",
 "Azure Files NFS uses a custom StorageClass with <code>protocol: nfs</code>, requires Premium FileStorage, and relies on network rules/private endpoints rather than SMB key auth.",
 "The CSI driver commonly stores the storage account key in a Kubernetes Secret in the claim namespace; inspect secrets when mounts fail or when rotating storage keys.",
 "Common SMB mount options include <code>dir_mode=0777</code>, <code>file_mode=0777</code>, <code>mfsymlinks</code>, <code>cache=strict</code> and <code>nosharesock</code>; set permissions deliberately.",
 "Blob CSI can be enabled with <code>az aks update --enable-blob-driver</code> and provides classes such as <code>azureblob-fuse-premium</code> and <code>azureblob-nfs-premium</code>.",
 "Blobfuse2 is best for read-heavy analytics and object data; it is not a full POSIX filesystem, so rename may be copy-like and hard links are not available.",
 "Decision shortcut: Disk = fastest RWO block for one pod, Files = RWX SMB/NFS shared file semantics, Blob = object storage mounted for analytics or legacy file-like access.",
],
"prereq": "Shared cluster <code>aks-lab</code>. Azure Files CSI classes must be present; Blob CSI steps are shown as optional because enabling a driver changes the cluster.",
"portal": [
 "##Azure Files PVC",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Storage</b> \u2192 <b>Persistent volume claims</b>. Filter namespace <code>lab42</code> and confirm <code>files-pvc</code> is Bound with access mode <code>RWX</code>.",
 "Open the node resource group <code>MC_*</code> \u2192 find the storage account created by the Azure Files CSI driver. Open <b>File shares</b> and locate the dynamically created share.",
 "##Secrets and keys",
 "In the AKS portal, open <b>Configuration</b> \u2192 <b>Secrets</b> for namespace <code>lab42</code>, or use kubectl, to see the CSI-created storage secret when key-based SMB is used.",
 "##Blob CSI option",
 "Open <b>Storage classes</b> and look for <code>azureblob-fuse-premium</code> or <code>azureblob-nfs-premium</code>. If absent, the Blob CSI driver is not enabled on the cluster.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab42

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl get storageclass | grep -E 'azurefile|azureblob' || true

# Optional cluster change: enable Blob CSI if you need blob-backed mounts.
# az aks update -g $RG -n $AKS --enable-blob-driver
# kubectl get storageclass | grep azureblob""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab42

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: files-pvc
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: azurefile-csi
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: files-writers
spec:
  replicas: 2
  selector:
    matchLabels:
      app: files-writers
  template:
    metadata:
      labels:
        app: files-writers
    spec:
      containers:
      - name: busybox
        image: busybox:1.36
        command: ["sh", "-c", "while true; do echo $(hostname) $(date -Iseconds) >> /share/writes.txt; sleep 10; done"]
        volumeMounts:
        - name: share
          mountPath: /share
      volumes:
      - name: share
        persistentVolumeClaim:
          claimName: files-pvc
EOF

kubectl rollout status deploy/files-writers -n $NS
kubectl get pods,pvc,pv -n $NS -o wide

POD1=$(kubectl get pod -n $NS -l app=files-writers -o jsonpath='{.items[0].metadata.name}')
POD2=$(kubectl get pod -n $NS -l app=files-writers -o jsonpath='{.items[1].metadata.name}')
sleep 20
kubectl exec -n $NS $POD1 -- tail -n 5 /share/writes.txt
kubectl exec -n $NS $POD2 -- tail -n 5 /share/writes.txt

kubectl get secret -n $NS
kubectl describe pvc files-pvc -n $NS

cat <<EOF
# Azure Files NFS custom StorageClass sketch; requires Premium FileStorage and network access.
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: azurefile-nfs-premium
provisioner: file.csi.azure.com
parameters:
  skuName: Premium_LRS
  protocol: nfs
mountOptions:
- nconnect=4
EOF""",
"traps": [
 "RWX does not mean high-performance database storage; Azure Files SMB latency and metadata cost can crush workloads that expect local POSIX speed.",
 "NFS Azure Files is not the same auth model as SMB; if network rules or private endpoints block the node subnet, mounts fail even when the PVC is Bound.",
 "Deleting the CSI-created secret or rotating storage keys without coordination causes existing or future SMB mounts to fail.",
 "Blob CSI is not a magic POSIX disk; applications that need atomic rename, hard links or strict filesystem semantics should use Disk or Files instead.",
 "A two-replica Deployment writing one file proves shared storage, but it can also prove application-level write contention; RWX does not provide file locking for your app.",
],
"cleanup": r"""# Delete only the namespace created by this lab.
NS=lab42
kubectl delete ns $NS --ignore-not-found

# If you enabled Blob CSI only for this lab and no longer need it, review current AKS disable support before changing the shared cluster.""",
},
# ---------------------------------------------------------------- 4.3
{
"id": "4.3",
"title": "Snapshot and restore volumes",
"time": "35 min",
"level": "Advanced",
"objective": "Create a CSI VolumeSnapshot for an Azure Disk PVC, restore it to a new claim, and clone a PVC directly inside the cluster.",
"exam": [
 "AKS Azure Disk CSI supports Kubernetes <code>VolumeSnapshot</code>; snapshot CRDs are available on modern AKS clusters, but you create the <code>VolumeSnapshotClass</code> yourself.",
 "Azure Disk snapshot driver name is <code>disk.csi.azure.com</code>; a typical class uses <code>deletionPolicy: Delete</code> so deleting the VolumeSnapshot removes the cloud snapshot content.",
 "Parameter <code>incremental: \"true\"</code> creates incremental managed disk snapshots, reducing cost and time after the first snapshot.",
 "Restore uses a new PVC with <code>dataSource.kind: VolumeSnapshot</code> and a requested size at least as large as the source snapshot.",
 "PVC cloning uses <code>dataSource.kind: PersistentVolumeClaim</code>, normally in the same namespace, same storage class and same or larger requested size.",
 "A portal Azure disk snapshot captures the disk but is Kubernetes-unaware; CSI snapshots preserve the Kubernetes data-source workflow for restore manifests.",
 "AKS Backup protects cluster state and persistent volumes through a Backup vault and extension; use it for policy-based full-cluster recovery rather than one-off PVC snapshots.",
],
"prereq": "Shared cluster <code>aks-lab</code>. Namespace <code>lab43</code> and VolumeSnapshotClass <code>azuredisk-vsc-lab43</code> are created by this lab.",
"portal": [
 "##Snapshot CRDs",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Custom resources</b> and search for <code>volumesnapshots.snapshot.storage.k8s.io</code>. Modern AKS clusters include the snapshot CRDs.",
 "Open <b>Storage</b> \u2192 <b>Persistent volume claims</b> \u2192 namespace <code>lab43</code>. Watch original, restored and cloned PVCs bind to separate PVs.",
 "##Azure managed disk snapshots",
 "Open the node resource group <code>MC_*</code> \u2192 <b>Snapshots</b>. CSI-created disk snapshots appear as Azure snapshot resources behind the Kubernetes VolumeSnapshotContent.",
 "Do not delete snapshot resources directly in the portal while Kubernetes still has VolumeSnapshotContent objects; delete Kubernetes snapshots first when using CSI lifecycle management.",
 "##Backup product distinction",
 "Search <b>Backup vaults</b> \u2192 note that AKS Backup is configured as a backup policy and extension, not as ad hoc VolumeSnapshot YAML.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab43

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl api-resources | grep -i volumesnapshot
kubectl get crd | grep snapshot.storage.k8s.io
kubectl get volumesnapshotclass 2>/dev/null || true""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab43

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: azuredisk-vsc-lab43
driver: disk.csi.azure.com
deletionPolicy: Delete
parameters:
  incremental: "true"
EOF

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: source-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: managed-csi
  resources:
    requests:
      storage: 4Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: writer
spec:
  restartPolicy: Never
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "echo snapshot-data > /data/proof.txt && sync && sleep 20"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: source-pvc
EOF

kubectl wait --for=condition=Ready pod/writer -n $NS --timeout=180s
kubectl exec -n $NS writer -- cat /data/proof.txt
kubectl delete pod writer -n $NS --wait=true

kubectl apply -n $NS -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: source-snap
spec:
  volumeSnapshotClassName: azuredisk-vsc-lab43
  source:
    persistentVolumeClaimName: source-pvc
EOF

kubectl wait --for=jsonpath='{.status.readyToUse}'=true volumesnapshot/source-snap -n $NS --timeout=300s
kubectl get volumesnapshot,volumesnapshotcontent -n $NS

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: managed-csi
  dataSource:
    name: source-snap
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  resources:
    requests:
      storage: 4Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: cloned-pvc
spec:
  accessModes:
  - ReadWriteOnce
  storageClassName: managed-csi
  dataSource:
    name: source-pvc
    kind: PersistentVolumeClaim
  resources:
    requests:
      storage: 4Gi
EOF

kubectl wait --for=jsonpath='{.status.phase}'=Bound pvc/restored-pvc -n $NS --timeout=180s
kubectl wait --for=jsonpath='{.status.phase}'=Bound pvc/cloned-pvc -n $NS --timeout=180s

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: restored-reader
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "cat /data/proof.txt && sleep 3600"]
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: restored-pvc
EOF
kubectl wait --for=condition=Ready pod/restored-reader -n $NS --timeout=180s
kubectl logs -n $NS restored-reader""",
"traps": [
 "Creating a VolumeSnapshotClass with the wrong driver name leaves snapshots stuck because Azure Disk PVCs require <code>disk.csi.azure.com</code>.",
 "Restored PVC size must be at least the source size; asking for a smaller claim is rejected or never binds.",
 "Deleting the VolumeSnapshot with <code>deletionPolicy: Delete</code> can delete the underlying Azure snapshot, so choose <code>Retain</code> when snapshots are legal records.",
 "Snapshots are crash-consistent unless the application flushes/quiesces data; database restores need app-aware steps or backup tooling.",
 "PVC clones are namespace and driver constrained; cloning is not a cross-region disaster recovery strategy.",
],
"cleanup": r"""# Delete only objects created by this lab.
NS=lab43
kubectl delete ns $NS --ignore-not-found
kubectl delete volumesnapshotclass azuredisk-vsc-lab43 --ignore-not-found""",
},
# ---------------------------------------------------------------- 4.4
{
"id": "4.4",
"title": "Run StatefulSets with stable storage",
"time": "40 min",
"level": "Advanced",
"objective": "Deploy a three-replica StatefulSet with one PVC per pod, prove ordinal identity and volume reuse, and test scale-down retention.",
"exam": [
 "StatefulSet pods get stable ordinal names such as <code>web-0</code>, <code>web-1</code> and <code>web-2</code>; a headless service controls DNS names like <code>web-0.nginx.lab44.svc.cluster.local</code>.",
 "<code>serviceName</code> is required for StatefulSet network identity and must reference the governing headless service.",
 "<code>volumeClaimTemplates</code> creates one PVC per replica named <code>&lt;template&gt;-&lt;statefulset&gt;-&lt;ordinal&gt;</code>, for example <code>www-web-0</code>.",
 "PVCs are retained by default on StatefulSet scale-down and deletion; <code>persistentVolumeClaimRetentionPolicy.whenDeleted</code> and <code>whenScaled</code> default to <code>Retain</code> on modern Kubernetes.",
 "Default pod management is ordered: create <code>0</code> to <code>N-1</code> and terminate <code>N-1</code> to <code>0</code>; <code>podManagementPolicy: Parallel</code> trades ordering for speed.",
 "<code>updateStrategy: RollingUpdate</code> can use <code>partition</code> so only ordinals greater than or equal to the partition update, a common canary pattern.",
 "Deployment plus one shared RWX volume is not equivalent to StatefulSet plus RWO per-pod volumes; StatefulSet gives stable identity and isolated storage per replica.",
 "With WaitForFirstConsumer disk classes, each PVC is created in the zone where its pod schedules, so later rescheduling has zone constraints.",
],
"prereq": "Shared cluster <code>aks-lab</code>. Namespace <code>lab44</code> is created and deleted by this lab; PVC retention behavior is demonstrated before cleanup.",
"portal": [
 "##Stateful identity",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> \u2192 <b>Stateful sets</b> \u2192 namespace <code>lab44</code>. Select <code>web</code> and note replicas <code>web-0</code>, <code>web-1</code>, <code>web-2</code>.",
 "Open <b>Services and ingresses</b> \u2192 <code>nginx</code>. Confirm <b>Cluster IP</b> is <code>None</code>, making it a headless service for pod DNS rather than a virtual IP load balancer.",
 "##Per-pod PVCs",
 "Open <b>Storage</b> \u2192 <b>Persistent volume claims</b> \u2192 namespace <code>lab44</code>. Confirm PVC names <code>www-web-0</code>, <code>www-web-1</code> and <code>www-web-2</code>.",
 "After scaling down to <code>1</code>, refresh the PVC list. <code>www-web-1</code> and <code>www-web-2</code> remain even though pods are gone; that retention is intentional.",
 "##Node and zone placement",
 "Open each pod's details and compare node names. RWO disks follow their PVC topology, so repeated scheduling is constrained by the disk's zone and attachment rules.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab44

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl get storageclass managed-csi -o yaml | grep -E 'volumeBindingMode|allowVolumeExpansion|reclaimPolicy' || true
kubectl get nodes -o wide""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab44

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None
  selector:
    app: web
  ports:
  - port: 80
    name: web
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: nginx
  replicas: 3
  podManagementPolicy: OrderedReady
  persistentVolumeClaimRetentionPolicy:
    whenDeleted: Retain
    whenScaled: Retain
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        command: ["/bin/sh", "-c"]
        args:
        - echo $(hostname) > /usr/share/nginx/html/hostname.txt; nginx -g 'daemon off;'
        ports:
        - containerPort: 80
          name: web
        volumeMounts:
        - name: www
          mountPath: /usr/share/nginx/html
  volumeClaimTemplates:
  - metadata:
      name: www
    spec:
      accessModes:
      - ReadWriteOnce
      storageClassName: managed-csi
      resources:
        requests:
          storage: 1Gi
EOF

kubectl rollout status statefulset/web -n $NS --timeout=300s
kubectl get pods,pvc -n $NS -o wide

for i in 0 1 2; do
  kubectl exec -n $NS web-$i -- cat /usr/share/nginx/html/hostname.txt
done

kubectl run dns-$NS --rm -i --restart=Never -n $NS --image=busybox:1.36 -- \
  nslookup web-0.nginx.$NS.svc.cluster.local

# Kill pod-1; StatefulSet recreates web-1 and reattaches www-web-1.
kubectl delete pod web-1 -n $NS
kubectl wait --for=condition=Ready pod/web-1 -n $NS --timeout=300s
kubectl exec -n $NS web-1 -- cat /usr/share/nginx/html/hostname.txt

# Scale down; PVCs for removed ordinals remain.
kubectl scale statefulset web -n $NS --replicas=1
kubectl rollout status statefulset/web -n $NS --timeout=300s
kubectl get pods,pvc -n $NS -o wide

# Scale back; web-1 and web-2 reuse their retained PVCs.
kubectl scale statefulset web -n $NS --replicas=3
kubectl rollout status statefulset/web -n $NS --timeout=300s
kubectl get pods,pvc -n $NS -o wide
for i in 0 1 2; do
  kubectl exec -n $NS web-$i -- cat /usr/share/nginx/html/hostname.txt
done""",
"traps": [
 "Deleting a StatefulSet does not necessarily delete its PVCs; retained claims keep billing and data until you delete them or set a different retention policy.",
 "A normal ClusterIP service does not provide per-pod DNS names; StatefulSet identity depends on a headless service with <code>clusterIP: None</code>.",
 "Scaling down from 3 to 1 removes pods <code>web-2</code> then <code>web-1</code>, but their PVCs remain and are reused when scaling back up.",
 "Parallel pod management can break applications that require ordered bootstrap, such as quorum systems that expect ordinal 0 first.",
 "RWO disks plus zone topology can block rescheduling if no node is available in the disk's zone; this is a capacity and topology issue, not a StatefulSet bug.",
],
"cleanup": r"""# Delete only the namespace created by this lab. This also deletes retained PVCs in lab44.
NS=lab44
kubectl delete ns $NS --ignore-not-found""",
},
]
