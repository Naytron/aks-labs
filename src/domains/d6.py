DOMAIN = {
    "key": "ops",
    "name": "Scaling, Observability & Ops",
    "weight": "Day-2 operations",
    "blurb": "The three autoscalers (HPA, cluster autoscaler, KEDA), managed Prometheus and Container insights, and the troubleshooting muscle memory \u2014 events, describes, debug nodes \u2014 that turns red pods green. Where AKS operators spend most of their time.",
}

LABS = [
# ---------------------------------------------------------------- 6.1
{
"id": "6.1",
"title": "Scale pods from CPU requests",
"time": "35 min",
"level": "Core",
"objective": "Create an autoscaling/v2 Horizontal Pod Autoscaler, drive CPU load, and watch replicas scale out and back in from requests.",
"exam": [
 "AKS includes <b>metrics-server</b> by default; HPA needs resource metrics unless you add custom or external metrics adapters.",
 "<code>autoscaling/v2</code> supports <b>Resource</b>, <b>Pods</b>, <b>Object</b>, and <b>External</b> metric types.",
 "CPU utilization target is a percentage of container <b>requests.cpu</b>, not limits and not node CPU; no request gives <code>&lt;unknown&gt;</code>.",
 "Default HPA sync period is <b>15s</b>; default scale-down stabilization window is <b>300s</b>.",
 "<code>minReplicas</code> defaults to <b>1</b>; HPA scale-to-zero needs alpha behavior, so use KEDA for production zero.",
 "<code>maxReplicas</code> is required and caps runaway scale even when metrics stay above target.",
 "The formula is <code>ceil(currentReplicas * currentMetric / targetMetric)</code>, then stabilization and behavior are applied.",
 "Behavior policies use <code>Pods</code> or <code>Percent</code>, <code>periodSeconds</code>, and <code>selectPolicy</code> <b>Max</b>, <b>Min</b>, or <b>Disabled</b>.",
 "Do not continuously set <code>spec.replicas</code> on a Deployment managed by HPA; GitOps can fight the controller.",
],
"prereq": "Shared cluster <code>aks-lab</code>, namespace <code>lab61</code>, and enough node capacity for several small pods.",
"portal": [
 "##Check metrics",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> and verify CPU appears after metrics-server has samples.",
 "Open <b>Cloud Shell</b>; HPA behavior is clearest with <code>kubectl get hpa -w</code> while load is running.",
 "##Watch replicas",
 "Filter Workloads to namespace <code>lab61</code> and watch Deployment replicas increase, then compare with HPA events in Cloud Shell.",
 "Open <b>Monitor</b> \u2192 <b>Metrics</b> for AKS and chart node CPU separately; node CPU is not the HPA target.",
],
"cli": r"""# Azure CLI (bash) — connect and confirm metrics-server
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab61

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes || echo "metrics-server may need a minute for the first sample"
""",
"kubectl": r"""# kubectl & YAML — HPA v2 plus load generator
NS=lab61
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: php-apache
  namespace: $NS
spec:
  selector:
    matchLabels:
      run: php-apache
  template:
    metadata:
      labels:
        run: php-apache
    spec:
      containers:
      - name: php-apache
        image: registry.k8s.io/hpa-example
        ports:
        - containerPort: 80
        resources:
          requests:
            cpu: 200m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: php-apache
  namespace: $NS
spec:
  selector:
    run: php-apache
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: php-apache
  namespace: $NS
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: php-apache
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
EOF
kubectl rollout status deploy/php-apache -n "$NS" --timeout=180s
kubectl run load-generator -n "$NS" --image=busybox:1.36 --restart=Never -- \
  /bin/sh -c "while true; do wget -q -O- http://php-apache.$NS.svc.cluster.local; done"
kubectl get hpa -n "$NS" -w
kubectl delete pod load-generator -n "$NS" --ignore-not-found
""",
"traps": [
 "No CPU request means HPA target is <code>&lt;unknown&gt;</code>; limits alone do not count.",
 "HPA creates pods, not nodes; Pending pods need cluster autoscaler capacity.",
 "Scale-down waits through the <b>300s</b> stabilization window by default.",
 "GitOps that reapplies <code>spec.replicas: 1</code> fights HPA and causes flapping.",
 "Unrealistic targets like <code>5%</code> can create many replicas quickly; always set maxReplicas.",
],
"cleanup": r"""NS=lab61
kubectl delete ns "$NS" --ignore-not-found
""",
},
# ---------------------------------------------------------------- 6.2
{
"id": "6.2",
"title": "Add nodes for Pending pods",
"time": "40 min",
"level": "Advanced",
"objective": "Enable cluster autoscaler on a node pool, create unschedulable pods, and observe AKS add and later remove nodes.",
"exam": [
 "Cluster autoscaler reacts to <b>Pending unschedulable pods</b>, not high CPU on running pods; HPA and autoscaler solve different layers.",
 "Enable per pool with <code>az aks nodepool update --enable-cluster-autoscaler --min-count 1 --max-count 5</code>.",
 "Default scan interval is <b>10s</b>; actual scale-up still waits for VMSS allocation, image pull, and kubelet join.",
 "Scale-down considers nodes under utilization threshold <b>0.5</b> after <code>scale-down-unneeded-time</code>, commonly <b>10m</b>.",
 "Set profile flags with <code>az aks update --cluster-autoscaler-profile</code>, including <code>expander</code> and <code>skip-nodes-with-local-storage</code>.",
 "Expanders include <code>least-waste</code>, <code>random</code>, and <code>priority</code>; least-waste minimizes unused CPU and memory.",
 "Scale-down blockers include restrictive PDBs, local storage, naked pods, no-PDB kube-system pods, and <code>safe-to-evict: \"false\"</code>.",
 "<code>balance-similar-node-groups</code> helps keep similar zonal node pools even.",
 "Node Autoprovisioning is Karpenter-based with <code>--node-provisioning-mode Auto</code>; it is rolling out by region, so check support.",
],
"prereq": "Shared cluster <code>aks-lab</code> with an application node pool named <code>apps</code> or adjust <code>POOL</code>.",
"portal": [
 "##Enable autoscaler",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Settings</b> \u2192 <b>Node pools</b> \u2192 select <code>apps</code> \u2192 <b>Scale</b> \u2192 enable autoscaler min <code>1</code>, max <code>5</code>.",
 "Open <b>Insights</b> \u2192 <b>Nodes</b> and note the node count before creating the large-request workload.",
 "##Watch scheduling",
 "Use <b>Cloud Shell</b> with <code>kubectl get pods -w</code> and <code>kubectl get nodes -w</code>; portal views lag behind events.",
 "Compare node <b>Allocatable</b> CPU/memory with the pod requests that triggered scale-up.",
],
"cli": r"""# Azure CLI (bash) — enable cluster autoscaler and profile
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
POOL=apps
NS=lab62

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
az aks nodepool update -g "$RG" --cluster-name "$AKS" -n "$POOL" \
  --enable-cluster-autoscaler --min-count 1 --max-count 5
az aks update -g "$RG" -n "$AKS" \
  --cluster-autoscaler-profile scan-interval=10s,scale-down-unneeded-time=10m,scale-down-utilization-threshold=0.5,expander=least-waste,max-graceful-termination-sec=600
az aks nodepool show -g "$RG" --cluster-name "$AKS" -n "$POOL" \
  --query "{name:name,count:count,min:minCount,max:maxCount,autoscaler:enableAutoScaling}" -o table
kubectl get nodes -L agentpool
""",
"kubectl": r"""# kubectl & YAML — force Pending, then watch new nodes
NS=lab62
POOL=apps
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: big-request
  namespace: $NS
spec:
  replicas: 10
  selector:
    matchLabels:
      app: big-request
  template:
    metadata:
      labels:
        app: big-request
    spec:
      nodeSelector:
        agentpool: $POOL
      containers:
      - name: web
        image: mcr.microsoft.com/azuredocs/aks-helloworld:v1
        resources:
          requests:
            cpu: "900m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "768Mi"
EOF
kubectl get pods -n "$NS" -w
kubectl get events -n "$NS" --sort-by=.lastTimestamp | tail -30
kubectl delete deploy big-request -n "$NS"
echo "Scale-down normally waits about 10 minutes after nodes are unneeded."
kubectl get nodes -w -L agentpool
""",
"traps": [
 "High CPU alone does not add nodes; pods must be Pending and unschedulable.",
 "A PDB with <code>minAvailable</code> equal to replicas blocks voluntary eviction and scale-down.",
 "Local storage or <code>safe-to-evict: \"false\"</code> can keep expensive nodes alive.",
 "Max count <code>5</code> is a hard ceiling; remaining Pending pods need more max or smaller requests.",
 "Spot pools work with autoscaler, but evictions still require PDBs and interruption-aware workloads.",
],
"cleanup": r"""RG=rg-aks-labs
AKS=aks-lab
POOL=apps
NS=lab62
kubectl delete ns "$NS" --ignore-not-found
az aks nodepool update -g "$RG" --cluster-name "$AKS" -n "$POOL" --disable-cluster-autoscaler || true
""",
},
# ---------------------------------------------------------------- 6.3
{
"id": "6.3",
"title": "Scale events to zero",
"time": "40 min",
"level": "Advanced",
"objective": "Enable the managed KEDA add-on and use a cron ScaledObject to scale nginx from zero to three replicas and back.",
"exam": [
 "Enable managed KEDA with <code>az aks update --enable-keda</code>; the operator runs in <code>kube-system</code>.",
 "A <code>ScaledObject</code> wraps a workload and owns the generated HPA; do not create both for the same target.",
 "KEDA has more than <b>60</b> scalers, including cron, Azure Service Bus, Event Hubs, Storage Queue, Prometheus, and Kafka.",
 "KEDA handles activation <b>0 to 1</b>; the generated HPA handles <b>1 to N</b>, which HPA alone cannot do.",
 "Default <code>pollingInterval</code> is <b>30s</b>; default <code>cooldownPeriod</code> is <b>300s</b> and applies to scale-to-zero.",
 "<code>minReplicaCount: 0</code> enables zero; <code>maxReplicaCount</code> still caps burst size.",
 "Cron scaler needs <code>timezone</code>, <code>start</code>, <code>end</code>, and <code>desiredReplicas</code> using five-field cron.",
 "Azure Service Bus can authenticate with <code>TriggerAuthentication</code> and <code>podIdentity.provider: azure-workload</code>.",
 "<code>ScaledJob</code> is for job-per-message; <code>ScaledObject</code> is for long-running services.",
],
"prereq": "Shared cluster <code>aks-lab</code>, namespace <code>lab63</code>, and permission to enable KEDA.",
"portal": [
 "##Enable KEDA",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Extensions + applications</b> and confirm <b>KEDA</b> appears after the CLI update.",
 "Open <b>Workloads</b> \u2192 Namespace <code>kube-system</code> and find <b>keda-operator</b> pods.",
 "##Watch generated HPA",
 "Open <b>Cloud Shell</b> and run <code>kubectl get scaledobject,hpa -n lab63</code>; KEDA generated the HPA.",
 "Open namespace <code>lab63</code> and watch the Deployment move from <code>0</code> to <code>3</code> during the cron window.",
],
"cli": r"""# Azure CLI (bash) — enable KEDA
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab63

az aks update -g "$RG" -n "$AKS" --enable-keda
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
az aks show -g "$RG" -n "$AKS" --query workloadAutoScalerProfile.keda.enabled -o tsv
kubectl get pods -n kube-system -l app=keda-operator
""",
"kubectl": r"""# kubectl & YAML — cron ScaledObject opens a five-minute window
NS=lab63
TZ=Etc/UTC
START=$(date -u -d '+1 minute' '+%M %H * * *')
END=$(date -u -d '+6 minutes' '+%M %H * * *')
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cron-nginx
  namespace: $NS
spec:
  replicas: 0
  selector:
    matchLabels:
      app: cron-nginx
  template:
    metadata:
      labels:
        app: cron-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
---
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-nginx
  namespace: $NS
spec:
  scaleTargetRef:
    name: cron-nginx
  pollingInterval: 30
  cooldownPeriod: 300
  minReplicaCount: 0
  maxReplicaCount: 3
  triggers:
  - type: cron
    metadata:
      timezone: $TZ
      start: "$START"
      end: "$END"
      desiredReplicas: "3"
EOF
kubectl describe scaledobject cron-nginx -n "$NS"
kubectl get scaledobject,hpa,deploy,pods -n "$NS"
kubectl get deploy cron-nginx -n "$NS" -w
""",
"traps": [
 "A separate HPA on a KEDA target causes two controllers to write replicas.",
 "<code>cooldownPeriod</code> controls return to zero, not every downscale step.",
 "Cron timezone mismatch makes the window look missed; verify UTC versus local time.",
 "KEDA can scale pods to zero, but cluster autoscaler node scale-down still depends on eviction rules.",
 "Connection strings work for Azure scalers but store secrets; workload identity is the native pattern.",
],
"cleanup": r"""NS=lab63
kubectl delete ns "$NS" --ignore-not-found
""",
},
# ---------------------------------------------------------------- 6.4
{
"id": "6.4",
"title": "Wire logs, metrics, and dashboards",
"time": "45 min",
"level": "Core",
"objective": "Enable Container insights, managed Prometheus, and Azure Managed Grafana, then query pod logs and view Kubernetes dashboards.",
"exam": [
 "Container insights sends <b>logs</b> and inventory through <code>ama-logs</code> to Log Analytics; <code>ContainerLogV2</code> is the current stdout/stderr schema.",
 "Managed Prometheus sends <b>metrics</b> through <code>ama-metrics</code> to an Azure Monitor workspace and is queried with <b>PromQL</b>.",
 "Azure Managed Grafana provides prebuilt Kubernetes dashboards when linked to the Azure Monitor workspace.",
 "Enable logs with <code>az aks enable-addons --addons monitoring</code>; enable metrics with <code>--enable-azure-monitor-metrics</code>.",
 "Default Prometheus scrape interval is commonly <b>30s</b>; managed metrics are retained up to <b>18 months</b>.",
 "Cost controls include <code>ContainerLogV2</code> Basic Logs, namespace exclusions, collection intervals, and dropping stdout for chatty namespaces.",
 "KQL starter: <code>ContainerLogV2 | where PodName startswith 'aks-hello' | take 100</code>.",
 "Join with <code>KubePodInventory</code> for namespace, node, controller, and restart context.",
 "Portal live logs require <b>Monitoring Reader</b> plus direct cluster access; Log Analytics read access alone may not be enough.",
],
"prereq": "Shared cluster <code>aks-lab</code> and rights to create Log Analytics, Azure Monitor workspace, and Azure Managed Grafana resources.",
"portal": [
 "##Container insights",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Monitoring</b> \u2192 <b>Insights</b> \u2192 <b>Enable</b> and choose the lab workspace.",
 "Open <b>Logs</b> and run <code>ContainerLogV2 | where Namespace == 'lab64' | take 100</code> after the sample app writes logs.",
 "##Prometheus and Grafana",
 "Open <b>Monitor</b> \u2192 <b>Managed Prometheus</b> and confirm collection from <code>ama-metrics</code>.",
 "Open <b>Azure Managed Grafana</b> \u2192 lab instance \u2192 <b>Endpoint</b> \u2192 Kubernetes dashboards \u2192 filter namespace <code>lab64</code>.",
 "##Cost",
 "Open the Log Analytics workspace \u2192 <b>Tables</b> \u2192 <code>ContainerLogV2</code> and review table plan options.",
],
"cli": r"""# Azure CLI (bash) — enable logs, metrics, and Grafana
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab64
LAW=law-aks-lab-$RANDOM
AMW=amw-aks-lab-$RANDOM
GRAF=grafana-aks-lab-$RANDOM

az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" --retention-time 30
LAW_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)
az aks enable-addons -g "$RG" -n "$AKS" --addons monitoring --workspace-resource-id "$LAW_ID"
az monitor account create -g "$RG" -n "$AMW" -l "$LOC"
AMW_ID=$(az monitor account show -g "$RG" -n "$AMW" --query id -o tsv)
az grafana create -g "$RG" -n "$GRAF" -l "$LOC"
GRAF_ID=$(az grafana show -g "$RG" -n "$GRAF" --query id -o tsv)
az aks update -g "$RG" -n "$AKS" --enable-azure-monitor-metrics \
  --azure-monitor-workspace-resource-id "$AMW_ID" --grafana-resource-id "$GRAF_ID"
az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl get pods -n kube-system -l app=ama-metrics || true
""",
"kubectl": r"""# kubectl & YAML — sample app and log generator
NS=lab64
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aks-hello
  namespace: $NS
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
      - name: web
        image: mcr.microsoft.com/azuredocs/aks-helloworld:v1
        resources:
          requests:
            cpu: 50m
            memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: log-writer
  namespace: $NS
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["/bin/sh", "-c", "i=0; while true; do echo lab64-log-$i; i=$((i+1)); sleep 5; done"]
EOF
kubectl rollout status deploy/aks-hello -n "$NS" --timeout=180s
kubectl logs -n "$NS" log-writer --tail=5
kubectl top pods -n "$NS" || true
cat <<'EOF'
# Paste into Log Analytics:
ContainerLogV2
| where Namespace == "lab64"
| project TimeGenerated, PodName, ContainerName, LogMessage
| take 100

KubePodInventory
| where Namespace == "lab64"
| summarize arg_max(TimeGenerated, *) by PodUid
| project TimeGenerated, Name, ContainerName, RestartCount, Computer
EOF
""",
"traps": [
 "Container insights logs and managed Prometheus metrics are separate pipelines; enabling one does not enable the other.",
 "Log Analytics can lag several minutes, while <code>kubectl logs</code> is immediate.",
 "Dropping stdout saves money but removes application logs from KQL; keep a break-glass path.",
 "Blank Grafana dashboards are often RBAC to Azure Monitor workspace, not missing metrics.",
 "<code>kubectl top</code> uses metrics-server, not managed Prometheus, so values can differ.",
],
"cleanup": r"""RG=rg-aks-labs
NS=lab64
kubectl delete ns "$NS" --ignore-not-found
if [ -n "$GRAF" ]; then az grafana delete -g "$RG" -n "$GRAF" --yes || true; fi
if [ -n "$AMW" ]; then az monitor account delete -g "$RG" -n "$AMW" --yes || true; fi
if [ -n "$LAW" ]; then az monitor log-analytics workspace delete -g "$RG" -n "$LAW" --yes --force true || true; fi
""",
},
# ---------------------------------------------------------------- 6.5
{
"id": "6.5",
"title": "Walk the failure ladder",
"time": "45 min",
"level": "Core",
"objective": "Create common pod failures, diagnose each with events, logs, and debug commands, then apply the smallest fix.",
"exam": [
 "Triage order is <code>kubectl get pods</code> \u2192 <code>describe pod</code> events \u2192 <code>logs --previous</code> \u2192 <code>exec</code> \u2192 <code>debug</code>.",
 "<b>Pending</b> means not scheduled or waiting; <b>ImagePullBackOff</b> is image retry; <b>CrashLoopBackOff</b> is repeated exit.",
 "CrashLoopBackOff backs off from about <b>10s</b> to <b>5m</b>; <code>--previous</code> shows the last failed container.",
 "OOMKilled is usually exit code <b>137</b> with <code>lastState.terminated.reason=OOMKilled</code>.",
 "Pending causes include insufficient CPU/memory, unbound PVC, taint mismatch, and nodeSelector or affinity with no matching node.",
 "Image pull events show <b>401/403</b> auth, <b>404/manifest unknown</b> tag errors, or DNS/network reachability failures.",
 "<code>kubectl debug node/&lt;n&gt; -it --image=mcr.microsoft.com/cbl-mariner/busybox:2.0</code> mounts the host at <code>/host</code>.",
 "Ephemeral containers use <code>kubectl debug pod/&lt;pod&gt; --target &lt;container&gt;</code> for distroless images without shells.",
 "AKS checks include <code>az aks show --query provisioningState</code>, <b>Diagnose and solve problems</b>, Resource Health, and <code>cluster-info dump</code>.",
],
"prereq": "Shared cluster <code>aks-lab</code>, namespace <code>lab65</code>, and comfort deleting intentionally broken pods.",
"portal": [
 "##Status and events",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> \u2192 Namespace <code>lab65</code> and group pods by Status.",
 "Select a failed pod \u2192 <b>Events</b>. The newest warning usually names image 404, missing ConfigMap, failed scheduling, or OOM.",
 "##AKS diagnostics",
 "Open <b>Diagnose and solve problems</b> \u2192 review <b>Cluster health</b>, <b>Node health</b>, <b>Connectivity</b>, and <b>Performance</b>.",
 "Open <b>Resource health</b> and compare Azure platform health with Kubernetes object failures; a green resource can still have bad YAML.",
 "##Debug safely",
 "Use <b>Cloud Shell</b> for <code>kubectl debug</code>; it is usually better than SSH for node inspection.",
],
"cli": r"""# Azure CLI (bash) — AKS context for troubleshooting
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab65

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
az aks show -g "$RG" -n "$AKS" --query "{name:name,state:provisioningState,power:powerState.code,kubernetes:kubernetesVersion}" -o table
kubectl get nodes -o wide
kubectl get events --sort-by=.lastTimestamp -A --field-selector type=Warning | tail -40
""",
"kubectl": r"""# kubectl & YAML — breakage zoo and fixes
NS=lab65
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: bad-image
  namespace: $NS
spec:
  containers:
  - name: web
    image: mcr.microsoft.com/azuredocs/aks-helloworld:no-such-tag
---
apiVersion: v1
kind: Pod
metadata:
  name: missing-config
  namespace: $NS
spec:
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    envFrom:
    - configMapRef:
        name: does-not-exist
---
apiVersion: v1
kind: Pod
metadata:
  name: oom-demo
  namespace: $NS
spec:
  containers:
  - name: mem
    image: busybox:1.36
    command: ["sh", "-c", "x=0123456789; while true; do x=$x$x$x$x; done"]
    resources:
      limits:
        memory: 16Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: impossible-selector
  namespace: $NS
spec:
  nodeSelector:
    lab65: no-such-node
  containers:
  - name: busybox
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
EOF
sleep 30
kubectl get pods -n "$NS" -o wide
kubectl describe pod bad-image -n "$NS" | sed -n '/Events:/,$p'
kubectl describe pod missing-config -n "$NS" | sed -n '/Events:/,$p'
kubectl describe pod impossible-selector -n "$NS" | sed -n '/Events:/,$p'
kubectl logs oom-demo -n "$NS" --previous || true
kubectl create configmap does-not-exist -n "$NS" --from-literal=MODE=fixed
kubectl delete pod missing-config impossible-selector -n "$NS"
kubectl run possible-selector -n "$NS" --image=busybox:1.36 --restart=Never -- sh -c 'sleep 3600'
NODE=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')
kubectl debug node/$NODE -it --image=mcr.microsoft.com/cbl-mariner/busybox:2.0 -- chroot /host sh -c 'hostname; crictl ps | head' || true
""",
"traps": [
 "The STATUS column is not enough; the actionable message is normally in <code>describe pod</code> Events.",
 "For CrashLoopBackOff, plain logs may show the new attempt; use <code>--previous</code>.",
 "Deleting a Pending pod before reading events hides CPU, PVC, taint, or nodeSelector causes.",
 "OOMKilled exit code <b>137</b> is a container memory limit problem, not an AKS outage.",
 "SSH node debugging is usually unnecessary; <code>kubectl debug node</code> is auditable and Kubernetes-native.",
],
"cleanup": r"""NS=lab65
kubectl delete ns "$NS" --ignore-not-found
""",
},
]
