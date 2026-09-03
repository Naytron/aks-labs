DOMAIN = {
    "key": "workloads",
    "name": "Workloads & Scheduling",
    "weight": "Day-1 skills",
    "blurb": "Deployments and rollouts, probes and resource governance, ConfigMaps and Secrets, the scheduler's full toolkit (selectors, affinity, taints, spread), batch workloads, and Helm. The pure-Kubernetes core you exercise on AKS every day.",
}

LABS = [
# ---------------------------------------------------------------- 2.1
{
"id": "2.1",
"title": "Roll out and roll back Deployments",
"time": "35 min",
"level": "Foundational",
"objective": "Create a Deployment, scale it, update its image, inspect ReplicaSet history, and roll back to a known revision.",
"exam": [
 "A Deployment owns ReplicaSets; do not edit ReplicaSets directly because the Deployment controller reconciles desired state.",
 "Default strategy is <b>RollingUpdate</b> with <code>maxSurge: 25%</code> and <code>maxUnavailable: 25%</code>.",
 "<code>revisionHistoryLimit</code> defaults to <b>10</b>, which controls how many old ReplicaSets remain for rollback.",
 "<code>kubectl rollout undo deployment/name --to-revision=N</code> rolls back to a specific stored revision.",
 "<code>kubernetes.io/change-cause</code> is shown in <code>kubectl rollout history</code> when you annotate changes.",
 "Old ReplicaSets normally remain with desired/current <code>0</code>; that is rollback history, not duplicate capacity.",
 "<b>Recreate</b> terminates old pods before creating new ones and is for incompatible or single-writer workloads, not zero-downtime web tiers.",
],
"prereq": "Shared cluster <code>aks-lab</code> is running and kubeconfig is configured.",
"portal": [
 "##Create from the portal",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Kubernetes resources</b> \u2192 <b>Workloads</b>.",
 "Click <b>+ Create</b> \u2192 <b>Apply a YAML</b> and paste the namespace, Deployment, and Service YAML for <code>lab21</code>.",
 "Open <b>Deployments</b> \u2192 <code>web</code> and inspect desired pods, available pods, labels, and related ReplicaSets.",
 "##Watch rollout",
 "Use <b>Cloud Shell</b> to run <code>kubectl set image</code>, <code>rollout status</code>, <code>history</code>, and <code>undo</code>.",
 "Open <b>Pods</b> and sort by Created time. New pods appear under the new ReplicaSet while old pods drain to <code>0</code>.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab21

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create deployment web --image=nginx:1.27 --replicas=2
kubectl -n "$NS" annotate deployment web kubernetes.io/change-cause="initial nginx 1.27" --overwrite
kubectl -n "$NS" expose deployment web --port 80 --target-port 80
kubectl -n "$NS" scale deployment web --replicas=4
kubectl -n "$NS" rollout status deployment/web
kubectl -n "$NS" get deploy,rs,pods,svc -o wide
""",
"kubectl": r"""# kubectl & YAML
NS=lab21
kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "$NS" -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  annotations:
    kubernetes.io/change-cause: initial nginx 1.27 deployment
spec:
  replicas: 3
  revisionHistoryLimit: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:1.27
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl -n "$NS" rollout status deployment/web
kubectl -n "$NS" set image deployment/web web=mcr.microsoft.com/azuredocs/aks-helloworld:v1
kubectl -n "$NS" annotate deployment web kubernetes.io/change-cause="switch to aks-helloworld v1" --overwrite
kubectl -n "$NS" rollout status deployment/web
kubectl -n "$NS" rollout history deployment/web
kubectl -n "$NS" get rs -o wide
kubectl -n "$NS" rollout undo deployment/web --to-revision=1
kubectl -n "$NS" rollout status deployment/web
""",
"traps": [
 "Editing a ReplicaSet does not update the Deployment template; the next rollout ignores the RS change.",
 "A bad image or failing readiness can trigger <code>ProgressDeadlineExceeded</code> even while old pods still serve traffic.",
 "Rollback needs retained ReplicaSet history; low <code>revisionHistoryLimit</code> can remove the target revision.",
 "Scaling and image updates are separate desired-state changes; combine them only when you can troubleshoot both.",
],
"cleanup": r"""kubectl delete ns lab21 --ignore-not-found
""",
},
# ---------------------------------------------------------------- 2.2
{
"id": "2.2",
"title": "Configure probes, requests and QoS",
"time": "40 min",
"level": "Core",
"objective": "Configure probes, requests, limits, LimitRange, and ResourceQuota, then watch restarts, events, QoS, and metrics.",
"exam": [
 "Liveness failure restarts a container; readiness failure removes a pod from Service endpoints; startup gates liveness for slow starters.",
 "Probe defaults include <code>periodSeconds: 10</code>, <code>failureThreshold: 3</code>, and <code>initialDelaySeconds: 0</code>.",
 "Probe handlers include <code>httpGet</code>, <code>exec</code>, <code>tcpSocket</code>, and <code>grpc</code>.",
 "Requests schedule pods; limits enforce ceilings. CPU over limit throttles, while memory over limit can OOMKill with exit code <b>137</b>.",
 "QoS is <b>Guaranteed</b> when every container has equal CPU/memory requests and limits, <b>Burstable</b> with some request, and <b>BestEffort</b> with none.",
 "Eviction pressure generally removes BestEffort before Burstable before Guaranteed, considering usage over request.",
 "<code>LimitRange</code> sets default/min/max values; <code>ResourceQuota</code> caps namespace totals for pods, CPU, memory, and objects.",
 "<code>kubectl top pod</code> depends on Metrics Server, which AKS installs in <code>kube-system</code>.",
],
"prereq": "Shared cluster is running and Metrics Server is healthy.",
"portal": [
 "##Apply policy and workload",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> \u2192 <b>+ Create</b> \u2192 <b>Apply a YAML</b>.",
 "Paste the namespace, LimitRange, ResourceQuota, and Deployment YAML for <code>lab22</code>.",
 "Open <b>Pods</b> \u2192 select a pod \u2192 inspect container restart count, requests, limits, and recent events.",
 "##Break liveness",
 "Use <b>Cloud Shell</b> to apply the bad liveness patch. Return to pod details and watch restarts increase.",
 "Use Cloud Shell for <code>kubectl describe quota</code> and <code>kubectl top pod</code>; CLI events are more complete than portal summaries.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab22

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl get deployment metrics-server -n kube-system
kubectl top nodes || true
""",
"kubectl": r"""# kubectl & YAML
NS=lab22
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "$NS" -f - <<EOF
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
spec:
  limits:
  - type: Container
    defaultRequest:
      cpu: 50m
      memory: 64Mi
    default:
      cpu: 250m
      memory: 256Mi
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
spec:
  hard:
    pods: "10"
    requests.cpu: "1"
    requests.memory: 1Gi
    limits.cpu: "2"
    limits.memory: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: probe-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: probe-demo
  template:
    metadata:
      labels:
        app: probe-demo
    spec:
      containers:
      - name: web
        image: mcr.microsoft.com/dotnet/samples:aspnetapp
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 5
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 15
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
EOF

kubectl -n "$NS" rollout status deployment/probe-demo
kubectl -n "$NS" get pods -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass,RESTARTS:.status.containerStatuses[0].restartCount
kubectl -n "$NS" describe quota quota
kubectl -n "$NS" top pod || true
kubectl -n "$NS" patch deployment probe-demo --type='json' -p='[{"op":"replace","path":"/spec/template/spec/containers/0/livenessProbe/httpGet/path","value":"/bad-health"}]'
sleep 45
kubectl -n "$NS" get pods
kubectl -n "$NS" describe pod -l app=probe-demo | sed -n '/Events:/,$p'
""",
"traps": [
 "Using liveness for downstream dependency health can create restart storms; readiness usually fits dependency outages.",
 "No requests means poor scheduling and possible BestEffort QoS when no limits are set either.",
 "CPU limits throttle; memory limits kill. Treat them as different failure modes.",
 "A ResourceQuota without LimitRange defaults can reject pods that omit request/limit fields.",
],
"cleanup": r"""kubectl delete ns lab22 --ignore-not-found
""",
},
# ---------------------------------------------------------------- 2.3
{
"id": "2.3",
"title": "Use ConfigMaps and Secrets",
"time": "30 min",
"level": "Foundational",
"objective": "Create ConfigMaps and Secrets from literals and YAML, consume them as environment variables and volumes, and verify update behavior.",
"exam": [
 "ConfigMaps and Secrets have a practical size limit of about <b>1 MiB</b> per object.",
 "Secret base64 is encoding, not encryption; AKS uses Azure-managed etcd encryption at rest, with KMS options for stricter control.",
 "<code>stringData</code> accepts plain text on write and the API server stores base64 <code>data</code>.",
 "Secret types include <code>Opaque</code>, <code>kubernetes.io/dockerconfigjson</code>, and <code>kubernetes.io/tls</code>.",
 "Env vars from ConfigMaps or Secrets are read at pod start and <b>never update</b> in a running pod.",
 "Volume-mounted ConfigMaps and Secrets refresh through kubelet sync/cache, often around a minute; <code>subPath</code> mounts do not live-update.",
 "<code>immutable: true</code> prevents edits and reduces watch load for fixed configuration.",
 "<code>kubectl create secret docker-registry</code> works for private pulls; AKS ACR attach is preferred for Azure Container Registry.",
],
"prereq": "Shared cluster credentials are configured. No private registry is required.",
"portal": [
 "##Create configuration",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> \u2192 <b>+ Create</b> \u2192 <b>Apply a YAML</b>.",
 "Paste the namespace, ConfigMap, Secret, and Deployment YAML for <code>lab23</code>.",
 "Open <b>Pods</b> \u2192 select the pod and inspect environment and volume settings where the portal exposes them.",
 "##Verify safely",
 "Use <b>Cloud Shell</b> for <code>kubectl exec</code>; the portal should not be used as a decoded secret viewer.",
 "Patch the ConfigMap, wait about one minute, and compare mounted file refresh with the unchanged environment variable.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab23

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
printf 'color=blue\nregion=eastus2\n' > app.properties
kubectl -n "$NS" create configmap app-file --from-file=app.properties --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create secret generic app-secret --from-literal=password='not-for-production' --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" get configmap,secret
rm -f app.properties
""",
"kubectl": r"""# kubectl & YAML
NS=lab23
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "$NS" -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: lab
  message: hello-from-configmap
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  PASSWORD: not-for-production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: config-demo
spec:
  replicas: 1
  selector:
    matchLabels:
      app: config-demo
  template:
    metadata:
      labels:
        app: config-demo
    spec:
      containers:
      - name: box
        image: busybox:1.36
        command: ["sh", "-c", "while true; do echo $APP_MODE $(cat /config/message); sleep 30; done"]
        envFrom:
        - configMapRef:
            name: app-config
        - secretRef:
            name: app-secret
        volumeMounts:
        - name: config
          mountPath: /config
      volumes:
      - name: config
        configMap:
          name: app-config
EOF

kubectl -n "$NS" rollout status deployment/config-demo
POD=$(kubectl -n "$NS" get pod -l app=config-demo -o jsonpath='{.items[0].metadata.name}')
kubectl -n "$NS" exec "$POD" -- sh -c 'echo APP_MODE=$APP_MODE; echo PASSWORD length=${#PASSWORD}; cat /config/message'
kubectl -n "$NS" patch configmap app-config --type merge -p '{"data":{"message":"updated-volume-value","APP_MODE":"changed-env-value"}}'
sleep 70
kubectl -n "$NS" exec "$POD" -- sh -c 'echo APP_MODE=$APP_MODE; cat /config/message'
kubectl -n "$NS" apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: immutable-config
immutable: true
data:
  version: "1"
EOF
kubectl -n "$NS" get configmap immutable-config -o yaml
""",
"traps": [
 "Anyone with Secret read permission can decode base64 values; restrict RBAC and avoid logging secrets.",
 "Env var consumers need a pod restart after config changes.",
 "<code>subPath</code> ConfigMap mounts do not get projected updates.",
 "Immutable objects must be replaced with new names when values change.",
],
"cleanup": r"""kubectl delete ns lab23 --ignore-not-found
""",
},
# ---------------------------------------------------------------- 2.4
{
"id": "2.4",
"title": "Schedule with selectors, affinity and taints",
"time": "45 min",
"level": "Advanced",
"objective": "Place pods with selectors and affinity, repel them with taints, spread replicas, and verify scheduler decisions.",
"exam": [
 "<code>nodeSelector</code> is exact-match; AKS pools expose <code>kubernetes.azure.com/agentpool</code>.",
 "<code>requiredDuringSchedulingIgnoredDuringExecution</code> is mandatory at scheduling time but does not evict if labels change later.",
 "Preferred node affinity uses weights <code>1-100</code> and affects scoring only.",
 "Pod anti-affinity with <code>topologyKey: kubernetes.io/hostname</code> spreads replicas across nodes when enough nodes exist.",
 "Taints repel: <code>NoSchedule</code> blocks, <code>PreferNoSchedule</code> discourages, and <code>NoExecute</code> can evict.",
 "<code>tolerationSeconds</code> applies to <code>NoExecute</code> and controls eviction delay.",
 "Topology spread uses <code>maxSkew</code> and <code>whenUnsatisfiable</code> to control placement by node or zone.",
 "PriorityClasses can preempt lower-priority pods but cannot bypass taints, selectors, or missing resources.",
],
"prereq": "A user pool named <code>apps</code> is recommended; the CLI pane creates it if missing.",
"portal": [
 "##Inspect nodes",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Node pools</b> and confirm <code>apps</code> is a User pool.",
 "Open <b>Kubernetes resources</b> \u2192 <b>Nodes</b> and inspect labels and taints.",
 "##Apply and watch",
 "Use <b>Workloads</b> \u2192 <b>+ Create</b> \u2192 <b>Apply a YAML</b> for namespace <code>lab24</code> and the two Deployments.",
 "Compare each pod's <b>Node</b> with the expected <code>agentpool</code> or <code>apps</code> selector.",
 "Use <b>Cloud Shell</b> to taint a node. Pods without toleration become <code>Pending</code>; remove the taint before cleanup.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab24

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
if ! az aks nodepool show -g "$RG" --cluster-name "$AKS" -n apps >/dev/null 2>&1; then
  az aks nodepool add -g "$RG" --cluster-name "$AKS" -n apps --mode User --node-count 2 --node-vm-size Standard_DS2_v2 --labels workload=apps
fi
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl get nodes -L kubernetes.azure.com/agentpool,workload,topology.kubernetes.io/zone
""",
"kubectl": r"""# kubectl & YAML
NS=lab24
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "$NS" -f - <<EOF
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: lab24-high
value: 100000
globalDefault: false
description: "Lab priority class."
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pinned-apps
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pinned-apps
  template:
    metadata:
      labels:
        app: pinned-apps
    spec:
      priorityClassName: lab24-high
      nodeSelector:
        kubernetes.azure.com/agentpool: apps
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchLabels:
                  app: pinned-apps
              topologyKey: kubernetes.io/hostname
      containers:
      - name: web
        image: nginx:1.27
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spread-web
spec:
  replicas: 4
  selector:
    matchLabels:
      app: spread-web
  template:
    metadata:
      labels:
        app: spread-web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: spread-web
      containers:
      - name: web
        image: nginx:1.27
EOF

kubectl -n "$NS" rollout status deployment/pinned-apps
kubectl -n "$NS" rollout status deployment/spread-web
kubectl -n "$NS" get pods -o wide
NODE=$(kubectl get nodes -l kubernetes.azure.com/agentpool=apps -o jsonpath='{.items[0].metadata.name}')
kubectl taint node "$NODE" lab24=reserved:NoSchedule
kubectl -n "$NS" run no-toleration --image=busybox:1.36 --restart=Never -- sleep 3600 || true
kubectl -n "$NS" describe pod no-toleration | sed -n '/Events:/,$p'
kubectl taint node "$NODE" lab24=reserved:NoSchedule-
""",
"traps": [
 "A toleration permits a tainted node; it does not attract the pod without selector or affinity.",
 "A typo in required affinity leaves pods <code>Pending</code> with scheduler events.",
 "IgnoredDuringExecution means a later label change does not evict an already placed pod.",
 "Priority cannot overcome missing resources, impossible selectors, or untolerated taints.",
],
"cleanup": r"""NODE=$(kubectl get nodes -l kubernetes.azure.com/agentpool=apps -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
if [ -n "$NODE" ]; then kubectl taint node "$NODE" lab24=reserved:NoSchedule- 2>/dev/null || true; fi
kubectl delete ns lab24 --ignore-not-found
kubectl delete priorityclass lab24-high --ignore-not-found
""",
},
# ---------------------------------------------------------------- 2.5
{
"id": "2.5",
"title": "Run DaemonSets, Jobs and CronJobs",
"time": "35 min",
"level": "Core",
"objective": "Deploy node-wide agents, finite Jobs, and scheduled CronJobs with retries, deadlines, history, and concurrency controls.",
"exam": [
 "A DaemonSet runs one pod on every eligible node, including new nodes added later.",
 "DaemonSet updates default to <b>RollingUpdate</b>; <code>maxUnavailable</code> controls unavailable daemon pods.",
 "Job pod <code>restartPolicy</code> must be <code>Never</code> or <code>OnFailure</code>; <code>Always</code> is invalid.",
 "Job <code>backoffLimit</code> defaults to <b>6</b>, and <code>activeDeadlineSeconds</code> caps total runtime.",
 "<code>completions</code> sets required successes; <code>parallelism</code> sets concurrent pods.",
 "<code>ttlSecondsAfterFinished</code> cleans completed Jobs after a fixed number of seconds.",
 "CronJob supports five-field cron plus <code>timeZone</code>; specify the zone when local time matters.",
 "CronJob history defaults are <b>3</b> successful and <b>1</b> failed Job; concurrency is <code>Allow</code>, <code>Forbid</code>, or <code>Replace</code>.",
],
"prereq": "Shared cluster is running. System-pool taints require DaemonSet tolerations.",
"portal": [
 "##Apply controllers",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Workloads</b> \u2192 <b>+ Create</b> \u2192 <b>Apply a YAML</b>.",
 "Paste the namespace, DaemonSet, Job, and CronJob YAML for <code>lab25</code>.",
 "Open <b>Daemon sets</b> and confirm desired/current pods match eligible nodes.",
 "Open <b>Jobs</b> and inspect completions, duration, pods, and CronJob-created Job history.",
 "Use <b>Cloud Shell</b> to scale a pool and verify the DaemonSet follows the node count automatically.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab25

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
kubectl get nodes -o wide
""",
"kubectl": r"""# kubectl & YAML
NS=lab25
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n "$NS" -f - <<EOF
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-reporter
spec:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  selector:
    matchLabels:
      app: node-reporter
  template:
    metadata:
      labels:
        app: node-reporter
    spec:
      tolerations:
      - key: CriticalAddonsOnly
        operator: Exists
        effect: NoSchedule
      containers:
      - name: reporter
        image: busybox:1.36
        command: ["sh", "-c", "while true; do echo node=$NODE_NAME; sleep 60; done"]
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
---
apiVersion: batch/v1
kind: Job
metadata:
  name: pi-once
spec:
  completions: 3
  parallelism: 2
  backoffLimit: 6
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: calc
        image: busybox:1.36
        command: ["sh", "-c", "echo job pod=$HOSTNAME; sleep 10"]
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello-every-minute
spec:
  schedule: "*/1 * * * *"
  timeZone: "Etc/UTC"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 30
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: hello
            image: busybox:1.36
            command: ["sh", "-c", "date; echo hello from cronjob"]
EOF

kubectl -n "$NS" rollout status daemonset/node-reporter
kubectl -n "$NS" wait --for=condition=complete job/pi-once --timeout=180s
kubectl -n "$NS" get daemonset,job,cronjob,pods -o wide
kubectl -n "$NS" logs job/pi-once
sleep 70
kubectl -n "$NS" get jobs --sort-by=.metadata.creationTimestamp
""",
"traps": [
 "DaemonSets respect taints; add tolerations for system-tainted nodes when needed.",
 "Job templates with <code>restartPolicy: Always</code> are invalid because Jobs need finite completion.",
 "CronJob <code>Allow</code> can overlap slow runs every schedule tick; use <code>Forbid</code> or <code>Replace</code> deliberately.",
 "Without TTL or history limits, completed Job objects accumulate quickly.",
],
"cleanup": r"""kubectl delete ns lab25 --ignore-not-found
""",
},
# ---------------------------------------------------------------- 2.6
{
"id": "2.6",
"title": "Install and operate Helm releases",
"time": "35 min",
"level": "Core",
"objective": "Install, upgrade, inspect, roll back, template, and uninstall a Helm release while locating its Kubernetes release state.",
"exam": [
 "Helm v3 stores release records as Secrets named like <code>sh.helm.release.v1.NAME.vREV</code> in the release namespace.",
 "<code>helm upgrade --install</code> is idempotent: install if missing, upgrade if present.",
 "Values precedence is chart defaults, then <code>-f/--values</code> files in order, then <code>--set</code> flags last.",
 "<code>helm template</code> renders manifests locally; <code>helm install --dry-run</code> previews release behavior without writing resources.",
 "<code>helm history</code> and <code>helm rollback RELEASE REVISION</code> use Helm release revisions, not Git commits.",
 "<code>helm uninstall</code> removes release resources; <code>--keep-history</code> keeps release metadata.",
 "Chart <code>version</code> identifies the package; <code>appVersion</code> is informational and usually maps to the app.",
 "Azure Cloud Shell includes Helm; local installs can use <code>brew</code>, <code>winget</code>, or the official script.",
],
"prereq": "Shared cluster credentials are configured and Helm 3 is available locally or in Cloud Shell.",
"portal": [
 "##Run Helm from Cloud Shell",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Connect</b> \u2192 launch <b>Cloud Shell</b>.",
 "Run the Helm commands from this lab. The portal verifies resources; it does not replace Helm release management.",
 "##Verify workloads",
 "Open <b>Namespaces</b> and confirm <code>lab26</code> exists.",
 "Open <b>Workloads</b> \u2192 filter namespace <code>lab26</code> and inspect labels such as <code>app.kubernetes.io/managed-by=Helm</code>.",
 "Open <b>Configuration</b> \u2192 <b>Secrets</b> if available and look for <code>sh.helm.release.v1</code> history secrets.",
],
"cli": r"""# Azure CLI (bash)
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab26

az aks get-credentials -g "$RG" -n "$AKS" --overwrite-existing
helm version
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -
""",
"kubectl": r"""# kubectl & YAML
NS=lab26
kubectl create ns "$NS" --dry-run=client -o yaml | kubectl apply -f -

helm repo add podinfo https://stefanprodan.github.io/podinfo
helm repo update podinfo
cat > values-lab26.yaml <<EOF
replicaCount: 2
ui:
  color: "#34577c"
resources:
  requests:
    cpu: 25m
    memory: 64Mi
  limits:
    cpu: 250m
    memory: 256Mi
EOF

helm upgrade --install podinfo podinfo/podinfo -n "$NS" \
  --values values-lab26.yaml \
  --set logLevel=info

helm status podinfo -n "$NS"
helm ls -n "$NS"
helm history podinfo -n "$NS"
kubectl -n "$NS" get deploy,svc,pods,secrets -l app.kubernetes.io/instance=podinfo
helm template podinfo podinfo/podinfo -n "$NS" --values values-lab26.yaml | head -80
helm upgrade podinfo podinfo/podinfo -n "$NS" --reuse-values --set replicaCount=3
kubectl -n "$NS" rollout status deployment/podinfo
helm rollback podinfo 1 -n "$NS"
kubectl -n "$NS" rollout status deployment/podinfo
helm uninstall podinfo -n "$NS" --keep-history
helm history podinfo -n "$NS" || true
rm -f values-lab26.yaml
""",
"traps": [
 "Deleting Helm-managed objects with kubectl leaves Helm history inconsistent; use Helm for release lifecycle changes.",
 "<code>--set</code> wins over values files and can silently override reviewed configuration.",
 "Release names are namespace-scoped; use <code>helm ls -A</code> when you cannot find a release.",
 "Pin chart versions in production; chart version and app version are different fields.",
],
"cleanup": r"""helm uninstall podinfo -n lab26 --keep-history 2>/dev/null || true
kubectl delete ns lab26 --ignore-not-found
rm -f values-lab26.yaml
""",
},
]
