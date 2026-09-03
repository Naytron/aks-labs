DOMAIN = {
    "key": "networking",
    "name": "Networking",
    "weight": "Where clusters break",
    "blurb": "Service types and Azure load balancers, the CNI decision (kubenet vs Azure CNI vs Overlay), managed NGINX ingress via the app routing add-on, NetworkPolicy enforcement, controlling egress, and locking down the API server. Most production AKS incidents trace back to this domain.",
}

LABS = [
# ---------------------------------------------------------------- 3.1
{
"id": "3.1",
"title": "Expose services deliberately",
"time": "40 min",
"level": "Foundational",
"objective": "Create ClusterIP, NodePort and LoadBalancer services, inspect the Azure load balancer objects AKS creates, and verify traffic behavior from inside and outside the cluster.",
"exam": [
 "<b>ClusterIP</b> is the default Service type; it creates a virtual IP reachable only inside the cluster and kube-proxy programs iptables or IPVS rules to fan out to matching pod endpoints.",
 "<b>NodePort</b> opens the same port on every node from the default range <code>30000-32767</code>; it is usually a building block for load balancers, not a production front door by itself.",
 "<b>LoadBalancer</b> on AKS creates an Azure <b>Standard Load Balancer</b> rule and a public IP in the node resource group named <code>MC_*</code> unless annotations say otherwise.",
 "An internal load balancer uses <code>service.beta.kubernetes.io/azure-load-balancer-internal: \"true\"</code>; use <code>service.beta.kubernetes.io/azure-load-balancer-internal-subnet</code> to choose a subnet.",
 "For a static public IP, create the IP in the node resource group or grant the cluster identity <b>Network Contributor</b> on another resource group, then set <code>loadBalancerIP</code> or the Azure PIP annotation.",
 "<code>externalTrafficPolicy: Local</code> preserves client source IP and creates a <code>healthCheckNodePort</code>; <code>Cluster</code> spreads traffic across nodes but SNATs to node IPs.",
 "A headless service uses <code>clusterIP: None</code> and returns DNS records for individual pod endpoints instead of a load-balanced virtual IP.",
 "<code>sessionAffinity: ClientIP</code> pins a client IP to the same backend pod, which helps legacy sticky sessions but can create uneven pod load.",
],
"prereq": "Shared cluster <code>aks-lab</code> in <code>rg-aks-labs</code>, created with Azure CNI Overlay in <code>eastus2</code>.",
"portal": [
 "##Kubernetes services",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Services and ingresses</b>. Filter namespace <code>lab31</code> after you apply the YAML and compare service types <code>ClusterIP</code>, <code>NodePort</code> and <code>LoadBalancer</code>.",
 "Select <code>hello-lb</code> \u2192 confirm <b>External IP</b>, <b>Ports</b>, selector <code>app=hello</code> and endpoints. The portal reads Kubernetes service status; it does not create a different Azure object model.",
 "##Azure load balancer objects",
 "Open the cluster <b>Overview</b> \u2192 copy the <b>Node resource group</b> value. It begins with <code>MC_</code> and contains the VMSS, NICs, public IPs and load balancer managed by AKS.",
 "Go to <b>Resource groups</b> \u2192 the <code>MC_*</code> node RG \u2192 open the <b>Load balancer</b>. Under <b>Frontend IP configuration</b>, find the public IP created for <code>hello-lb</code>.",
 "Open <b>Load balancing rules</b> \u2192 note the frontend port <code>80</code>, backend pool using AKS nodes, and health probe. This rule is owned by the Kubernetes Service; edit the Service, not the rule, for durable changes.",
 "##Internal and static IP options",
 "Return to <b>Services and ingresses</b> \u2192 inspect annotations on <code>hello-internal</code>. Internal services show a private frontend IP from the VNet instead of a public IP.",
 "For static public IPs, create the <b>Public IP address</b> in the node RG first, then reference it in the Service manifest. If the IP is in another RG, grant the AKS managed identity <b>Network Contributor</b> on that RG.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab31

az aks get-credentials -g $RG -n $AKS --overwrite-existing
NODE_RG=$(az aks show -g $RG -n $AKS --query nodeResourceGroup -o tsv)
echo "Node resource group: $NODE_RG"

kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

# Inspect the Azure load balancer before creating the service.
az network lb list -g $NODE_RG -o table
az network public-ip list -g $NODE_RG -o table

# Optional static public IP pattern. Uncomment to reserve one and use it in the YAML.
# az network public-ip create -g $NODE_RG -n pip-lab31-static --sku Standard --allocation-method static -l $LOC
# STATIC_IP=$(az network public-ip show -g $NODE_RG -n pip-lab31-static --query ipAddress -o tsv)
# echo $STATIC_IP

# Watch the cloud controller manager allocate Azure infrastructure after kubectl apply.
kubectl get svc -n $NS -w""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab31

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hello
  template:
    metadata:
      labels:
        app: hello
    spec:
      containers:
      - name: hello
        image: mcr.microsoft.com/azuredocs/aks-helloworld:v1
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: hello-clusterip
spec:
  selector:
    app: hello
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: hello-nodeport
spec:
  type: NodePort
  selector:
    app: hello
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080
---
apiVersion: v1
kind: Service
metadata:
  name: hello-lb
spec:
  type: LoadBalancer
  externalTrafficPolicy: Local
  sessionAffinity: ClientIP
  selector:
    app: hello
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: hello-internal
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  selector:
    app: hello
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: hello-headless
spec:
  clusterIP: None
  selector:
    app: hello
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl rollout status deploy/hello -n $NS
kubectl get pods,svc,endpoints -n $NS -o wide
kubectl describe svc hello-lb -n $NS

kubectl run curl-$NS --rm -i --restart=Never -n $NS --image=busybox:1.36 -- \
  wget -qO- --timeout=5 http://hello-clusterip

PUBLIC_IP=$(kubectl get svc hello-lb -n $NS -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Public IP: $PUBLIC_IP"
[ -n "$PUBLIC_IP" ] && curl -m 10 http://$PUBLIC_IP || true

kubectl run dns-$NS --rm -i --restart=Never -n $NS --image=busybox:1.36 -- \
  nslookup hello-headless.$NS.svc.cluster.local""",
"traps": [
 "Creating a <code>LoadBalancer</code> Service and then editing the Azure load balancer rule in the portal is temporary; the Kubernetes cloud provider reconciles the Azure objects back to Service spec.",
 "A <code>NodePort</code> value outside <code>30000-32767</code> is rejected by the API server unless the cluster was created with a custom service node port range.",
 "Putting <code>externalTrafficPolicy: Local</code> on a deployment with pods on only one node preserves source IP but drops traffic to nodes without local endpoints, so probe health controls which nodes receive traffic.",
 "Static IP failures usually mean the IP is in the wrong resource group or the AKS identity lacks <b>Network Contributor</b>; the Service stays <code>Pending</code> with an event explaining authorization.",
 "Internal load balancers are private to the VNet; a browser on your laptop will not reach the private frontend unless you are on VPN, ExpressRoute, peering or a jump host.",
],
"cleanup": r"""# Delete only the namespace and optional static IP created by this lab.
RG=rg-aks-labs
AKS=aks-lab
NS=lab31
NODE_RG=$(az aks show -g $RG -n $AKS --query nodeResourceGroup -o tsv)

kubectl delete ns $NS --ignore-not-found
az network public-ip delete -g $NODE_RG -n pip-lab31-static --yes 2>/dev/null || true""",
},
# ---------------------------------------------------------------- 3.2
{
"id": "3.2",
"title": "Choose the right CNI",
"time": "45 min",
"level": "Advanced",
"objective": "Compare kubenet, Azure CNI node-subnet and Azure CNI Overlay address behavior, capacity math and migration options before choosing a production networking model.",
"exam": [
 "<b>kubenet</b> assigns pods from a private pod CIDR and NATs through node IPs; it depends on route tables and has a practical <b>400-node</b> route-table scale limit.",
 "Microsoft has announced <b>kubenet retirement on March 31, 2028</b>; new AKS clusters should use Azure CNI Overlay or another current Azure CNI mode.",
 "<b>Azure CNI node-subnet</b> gives every pod a VNet IP. Subnet sizing is nodes x <code>max-pods</code> plus upgrade surge; with 50 nodes and default 30 pods, reserve at least 1,500 pod IPs before system overhead.",
 "<b>Azure CNI Overlay</b> gives nodes VNet IPs and pods IPs from a private overlay CIDR, default <code>10.244.0.0/16</code>, conserving VNet addresses and supporting a default <b>250 pods per node</b>.",
 "Overlay pods are not directly reachable from the VNet; expose them with Kubernetes Services, LoadBalancers, ingress or other routed entry points.",
 "Cilium dataplane is selected with <code>--network-dataplane cilium</code>; it uses eBPF and includes NetworkPolicy enforcement through <code>--network-policy cilium</code>.",
 "Overlay creation uses <code>--network-plugin azure --network-plugin-mode overlay --pod-cidr</code>; classic node-subnet CNI uses <code>--network-plugin azure</code> without overlay mode.",
 "Migration support changes: kubenet-to-overlay in-place update is supported, and node-subnet-to-overlay has supported paths in current AKS releases, but always check the current AKS support matrix for your Kubernetes version, dataplane and policy engine.",
],
"prereq": "Azure CLI access to <code>rg-aks-labs</code>. This lab creates throwaway cluster <code>aks-lab-net</code> in the same RG; delete it in cleanup to stop cost.",
"portal": [
 "##Compare networking on the cluster blade",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Networking</b>. Confirm the shared cluster uses Azure CNI Overlay and note the pod CIDR and service CIDR fields.",
 "After creating <code>aks-lab-net</code>, open it \u2192 <b>Networking</b> and compare <b>Network plugin</b>, <b>Network plugin mode</b>, <b>Network policy</b> and <b>Pod CIDR</b> to the shared cluster.",
 "##Subnet planning",
 "Open the VNet containing the cluster subnet \u2192 <b>Subnets</b>. For classic Azure CNI, calculate nodes x max pods x surge before creating the cluster because every pod consumes a subnet IP.",
 "For overlay, only nodes and Azure infrastructure consume subnet IPs; pod IPs come from the overlay CIDR and are hidden behind Services for VNet clients.",
 "##Cost and deletion",
 "Open <b>Resource groups</b> \u2192 <code>rg-aks-labs</code> and verify <code>aks-lab-net</code> plus its <code>MC_*</code> node resource group. Delete the AKS resource or run cleanup when done.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NET_AKS=aks-lab-net

# Shared cluster: Azure CNI Overlay baseline.
az aks show -g $RG -n $AKS \
  --query '{networkPlugin:networkProfile.networkPlugin, mode:networkProfile.networkPluginMode, podCidr:networkProfile.podCidr, serviceCidr:networkProfile.serviceCidr, dataplane:networkProfile.networkDataplane, maxPods:agentPoolProfiles[0].maxPods}' -o table

# Throwaway overlay cluster with explicit CIDRs and Cilium dataplane.
# Cost warning: this creates VM capacity. Run cleanup at the end.
az aks create \
  -g $RG -n $NET_AKS -l $LOC \
  --node-count 1 --node-vm-size Standard_B2s \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --pod-cidr 10.246.0.0/16 \
  --service-cidr 10.247.0.0/16 \
  --dns-service-ip 10.247.0.10 \
  --network-dataplane cilium \
  --network-policy cilium \
  --generate-ssh-keys

az aks show -g $RG -n $NET_AKS \
  --query '{networkPlugin:networkProfile.networkPlugin, mode:networkProfile.networkPluginMode, podCidr:networkProfile.podCidr, serviceCidr:networkProfile.serviceCidr, dataplane:networkProfile.networkDataplane, policy:networkProfile.networkPolicy, maxPods:agentPoolProfiles[0].maxPods}' -o table

# Documented patterns; do not run unless you intentionally create more clusters.
# kubenet (retiring):
# az aks create -g $RG -n aks-kubenet-demo -l $LOC --network-plugin kubenet --pod-cidr 10.244.0.0/16 --generate-ssh-keys
# Azure CNI node-subnet:
# az aks create -g $RG -n aks-cni-node-demo -l $LOC --network-plugin azure --max-pods 30 --generate-ssh-keys
# Migration example; verify current support matrix before production use:
# az aks update -g $RG -n old-kubenet-cluster --network-plugin-mode overlay --pod-cidr 10.244.0.0/16""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
NET_AKS=aks-lab-net
NS=lab32

az aks get-credentials -g $RG -n $NET_AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ip-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ip-demo
  template:
    metadata:
      labels:
        app: ip-demo
    spec:
      containers:
      - name: agnhost
        image: registry.k8s.io/e2e-test-images/agnhost:2.45
        args: ["netexec", "--http-port=8080"]
        ports:
        - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: ip-demo
spec:
  selector:
    app: ip-demo
  ports:
  - port: 80
    targetPort: 8080
EOF

kubectl rollout status deploy/ip-demo -n $NS
kubectl get nodes -o wide
kubectl get pods -n $NS -o wide
kubectl get svc -n $NS -o wide

# Pod IPs should come from the overlay pod CIDR, not from the VNet subnet.
kubectl run curl-$NS --rm -i --restart=Never -n $NS --image=busybox:1.36 -- \
  wget -qO- --timeout=5 http://ip-demo/hostname""",
"traps": [
 "Classic Azure CNI subnet math that ignores surge upgrades fails later: a node image upgrade needs extra node and pod IP capacity at the same time.",
 "Overlay pod IPs are not VNet-routable; testing from a VM directly to a pod IP fails by design even when Service traffic works.",
 "Choosing kubenet for new clusters because it saves IPs ignores the March 31, 2028 retirement date and the route-table scaling ceiling.",
 "Network plugin, dataplane and NetworkPolicy choices are coupled; you cannot assume a cluster can switch every combination in place without checking the current AKS support matrix.",
 "Overlapping <code>pod-cidr</code>, <code>service-cidr</code>, VNet CIDR or peered-network CIDR causes DNS, Service routing or peering failures that are painful to unwind.",
],
"cleanup": r"""# Delete only the throwaway cluster and namespace created by this lab.
RG=rg-aks-labs
NET_AKS=aks-lab-net
NS=lab32

kubectl delete ns $NS --ignore-not-found 2>/dev/null || true
az aks delete -g $RG -n $NET_AKS --yes --no-wait""",
},
# ---------------------------------------------------------------- 3.3
{
"id": "3.3",
"title": "Publish apps with managed NGINX",
"time": "40 min",
"level": "Core",
"objective": "Enable the AKS app routing add-on, deploy two applications behind a managed NGINX ingress, and verify host and path routing with curl.",
"exam": [
 "The app routing add-on is enabled with <code>az aks approuting enable</code> and installs Microsoft-managed NGINX components in namespace <code>app-routing-system</code>.",
 "The managed IngressClass is <code>webapprouting.kubernetes.azure.com</code>; ingresses without the matching class may be ignored when multiple controllers exist.",
 "Path routing uses <code>pathType: Prefix</code> for prefix matches and <code>pathType: Exact</code> for exact matches; host rules are matched before path rules.",
 "Azure DNS integration is added with <code>az aks approuting zone add</code>, which lets the add-on manage records in the DNS zone you authorize.",
 "Key Vault TLS uses <code>az aks approuting update --enable-kv</code> and annotation <code>kubernetes.azure.com/tls-cert-keyvault-uri</code> with a certificate URI.",
 "Bring-your-own <code>ingress-nginx</code> installed by Helm is community-managed; the AKS app routing add-on is Microsoft-managed but has a narrower supported configuration surface.",
 "Internal managed NGINX uses an <code>NginxIngressController</code> custom resource with load balancer annotations such as <code>service.beta.kubernetes.io/azure-load-balancer-internal</code>.",
],
"prereq": "Shared cluster <code>aks-lab</code>. You need permission to enable AKS add-ons; DNS and Key Vault steps require pre-existing resources if you run them.",
"portal": [
 "##Enable and inspect the add-on",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Settings</b> \u2192 <b>Extensions + applications</b>. Confirm the app routing extension after the CLI enable command completes.",
 "Go to <b>Workloads</b> \u2192 namespace <code>app-routing-system</code>. Inspect the managed NGINX controller pods and service. Do not edit managed objects directly.",
 "##Ingress objects",
 "Open <b>Services and ingresses</b> \u2192 namespace <code>lab33</code> \u2192 select <code>hello-ingress</code>. Confirm host <code>lab33.example.com</code>, class <code>webapprouting.kubernetes.azure.com</code> and paths <code>/blue</code>, <code>/green</code>.",
 "##DNS and TLS integrations",
 "For Azure DNS, open the zone \u2192 <b>Access control (IAM)</b> and confirm the AKS add-on identity can write records before running <code>az aks approuting zone add</code>.",
 "For TLS, open <b>Key Vault</b> \u2192 <b>Certificates</b> \u2192 copy the certificate identifier and use it as <code>kubernetes.azure.com/tls-cert-keyvault-uri</code> on the Ingress.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab33
HOST=lab33.example.com

az aks get-credentials -g $RG -n $AKS --overwrite-existing

# Enable the Microsoft-managed NGINX app routing add-on.
az aks approuting enable -g $RG -n $AKS
kubectl get pods,svc -n app-routing-system
kubectl get ingressclass

# Optional Azure DNS integration. Replace values before running.
# DNS_ZONE_ID=$(az network dns zone show -g $RG -n example.com --query id -o tsv)
# az aks approuting zone add -g $RG -n $AKS --ids $DNS_ZONE_ID

# Optional Key Vault certificate integration. Replace values before running.
# az aks approuting update -g $RG -n $AKS --enable-kv
# CERT_URI=$(az keyvault certificate show --vault-name kv-lab --name tls-lab33 --query sid -o tsv)

kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab33
HOST=lab33.example.com

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: blue
  template:
    metadata:
      labels:
        app: blue
    spec:
      containers:
      - name: app
        image: mcr.microsoft.com/azuredocs/aks-helloworld:v1
        ports:
        - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: green
spec:
  replicas: 2
  selector:
    matchLabels:
      app: green
  template:
    metadata:
      labels:
        app: green
    spec:
      containers:
      - name: app
        image: nginx:1.27
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: blue
spec:
  selector:
    app: blue
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: green
spec:
  selector:
    app: green
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hello-ingress
  annotations:
    # To use Key Vault TLS after enabling KV integration, uncomment and set the certificate URI.
    # kubernetes.azure.com/tls-cert-keyvault-uri: "https://kv-lab.vault.azure.net/certificates/tls-lab33/00000000000000000000000000000000"
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: webapprouting.kubernetes.azure.com
  rules:
  - host: lab33.example.com
    http:
      paths:
      - path: /blue
        pathType: Prefix
        backend:
          service:
            name: blue
            port:
              number: 80
      - path: /green
        pathType: Prefix
        backend:
          service:
            name: green
            port:
              number: 80
EOF

kubectl rollout status deploy/blue -n $NS
kubectl rollout status deploy/green -n $NS
kubectl get ingress -n $NS -o wide

ING_IP=$(kubectl get ingress hello-ingress -n $NS -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Ingress IP: $ING_IP"
[ -n "$ING_IP" ] && curl -m 10 -H "Host: $HOST" http://$ING_IP/blue || true
[ -n "$ING_IP" ] && curl -m 10 -H "Host: $HOST" http://$ING_IP/green || true

# Internal NGINX pattern; install only when you need a private ingress controller.
cat <<EOF
apiVersion: approuting.kubernetes.azure.com/v1alpha1
kind: NginxIngressController
metadata:
  name: internal
spec:
  ingressClassName: webapprouting-internal
  controllerNamePrefix: internal
  loadBalancerAnnotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
EOF""",
"traps": [
 "Using <code>kubernetes.io/ingress.class</code> alone on new manifests can be ignored; prefer <code>spec.ingressClassName</code> with <code>webapprouting.kubernetes.azure.com</code>.",
 "DNS integration fails silently from the app perspective if the add-on identity lacks permission to the DNS zone; the Ingress exists but names do not resolve.",
 "Key Vault TLS needs the app routing KV integration and a certificate URI, not just a Kubernetes TLS secret copied from another ingress guide.",
 "Path rewrites are controller-specific annotations; a manifest that works on community ingress-nginx may behave differently on another ingress controller.",
 "Deleting only the Ingress leaves deployments and services running; cleanup should delete namespace <code>lab33</code> and disable the add-on only if no other lab uses it.",
],
"cleanup": r"""# Delete this lab's apps. Disable the add-on only if you no longer need managed ingress.
RG=rg-aks-labs
AKS=aks-lab
NS=lab33

kubectl delete ns $NS --ignore-not-found
# Optional shared add-on cleanup:
# az aks approuting disable -g $RG -n $AKS""",
},
# ---------------------------------------------------------------- 3.4
{
"id": "3.4",
"title": "Enforce least-privilege pod traffic",
"time": "40 min",
"level": "Advanced",
"objective": "Build a NetworkPolicy-enabled AKS cluster, apply default-deny ingress and egress, then allow only frontend-to-backend HTTP and DNS traffic.",
"exam": [
 "With no NetworkPolicy selecting a pod, Kubernetes allows all ingress and all egress for that pod; policy enforcement starts only after a policy engine exists.",
 "AKS policy engines include Azure NPM, Calico and Cilium; the engine is selected with <code>--network-policy azure|calico|cilium</code>, often at cluster create time or through supported upgrade paths.",
 "<code>podSelector: {}</code> means all pods in the policy namespace; an omitted selector is invalid, while an empty selector is intentionally broad.",
 "<code>policyTypes: [Ingress, Egress]</code> matters: an ingress-only policy does not restrict egress, and an egress-only policy does not restrict ingress.",
 "NetworkPolicies are additive unions; one allow policy cannot deny traffic allowed by another policy. There is no priority order in standard Kubernetes NetworkPolicy.",
 "Egress default-deny breaks DNS until you allow UDP and TCP <code>53</code> to kube-dns or CoreDNS in namespace <code>kube-system</code>.",
 "Namespace selectors can match the built-in label <code>kubernetes.io/metadata.name</code>, which is safer than hand-labeling system namespaces.",
 "Azure-to-Cilium and other enablement paths have changed over time; historically many policy choices were create-time, so check the current AKS support matrix before promising in-place changes.",
],
"prereq": "This lab creates throwaway cluster <code>aks-lab-np</code> with Calico NetworkPolicy because the shared overlay cluster is assumed to have no policy engine. Delete it in cleanup to stop cost.",
"portal": [
 "##Why a separate cluster",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Networking</b>. If <b>Network policy</b> is blank, the API accepts NetworkPolicy objects but no dataplane enforces them.",
 "After running the CLI create, open <code>aks-lab-np</code> \u2192 <b>Networking</b> and confirm <b>Network policy</b> shows <code>calico</code>.",
 "##Inspect policies and events",
 "Open <code>aks-lab-np</code> \u2192 <b>Workloads</b> \u2192 namespace <code>lab34</code>. Confirm frontend, backend and blocked test pods are healthy before assuming network policy is the failure.",
 "Use <b>Cloud Shell</b> from the portal for the kubectl tests if your workstation context points at the shared cluster. Cloud Shell is portal-side but still uses kubectl against the selected cluster.",
 "##Cost cleanup",
 "Open <b>Resource groups</b> \u2192 <code>rg-aks-labs</code> and verify <code>aks-lab-np</code> plus its <code>MC_*</code> node RG disappear after cleanup.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NP_AKS=aks-lab-np
NS=lab34

# Read the shared cluster's policy setting.
az aks show -g $RG -n $AKS --query '{plugin:networkProfile.networkPlugin, mode:networkProfile.networkPluginMode, policy:networkProfile.networkPolicy}' -o table

# Create a small throwaway policy-enabled cluster for deterministic enforcement.
# Cost warning: this creates VM capacity. Run cleanup at the end.
az aks create \
  -g $RG -n $NP_AKS -l $LOC \
  --node-count 1 --node-vm-size Standard_B2s \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --pod-cidr 10.248.0.0/16 \
  --service-cidr 10.249.0.0/16 \
  --dns-service-ip 10.249.0.10 \
  --network-policy calico \
  --generate-ssh-keys

az aks get-credentials -g $RG -n $NP_AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -
kubectl get nodes -o wide
kubectl get pods -n kube-system""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
NP_AKS=aks-lab-np
NS=lab34

az aks get-credentials -g $RG -n $NP_AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
        tier: api
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: backend
spec:
  selector:
    app: backend
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
        tier: web
    spec:
      containers:
      - name: busybox
        image: busybox:1.36
        command: ["sh", "-c", "sleep 3600"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blocked
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blocked
  template:
    metadata:
      labels:
        app: blocked
    spec:
      containers:
      - name: busybox
        image: busybox:1.36
        command: ["sh", "-c", "sleep 3600"]
EOF

kubectl rollout status deploy/backend -n $NS
kubectl rollout status deploy/frontend -n $NS
kubectl rollout status deploy/blocked -n $NS

# Baseline: without policy, every pod can reach backend.
kubectl exec -n $NS deploy/frontend -- wget -qO- --timeout=3 http://backend
kubectl exec -n $NS deploy/blocked -- wget -qO- --timeout=3 http://backend

kubectl apply -n $NS -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 80
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-egress-http-and-dns
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 80
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
EOF

kubectl get networkpolicy -n $NS
kubectl exec -n $NS deploy/frontend -- wget -qO- --timeout=5 http://backend
kubectl exec -n $NS deploy/blocked -- wget -qO- --timeout=5 http://backend || echo "blocked pod denied as expected"
kubectl exec -n $NS deploy/frontend -- nslookup backend.$NS.svc.cluster.local""",
"traps": [
 "Applying NetworkPolicy to a cluster with no policy engine creates YAML objects but does not block packets; always verify the AKS <b>Network policy</b> setting.",
 "A default-deny egress policy without DNS exceptions makes service names look broken; the real issue is blocked UDP/TCP <code>53</code> to CoreDNS.",
 "Policies are namespace-scoped; a <code>podSelector</code> never selects pods in another namespace unless paired with a <code>namespaceSelector</code> in a peer rule.",
 "Adding a second allow policy widens access because policies are additive; there is no Kubernetes NetworkPolicy deny rule or ordered priority.",
 "Testing with cached connections can mislead; start a fresh busybox <code>wget --timeout</code> after each policy change.",
],
"cleanup": r"""# Delete only this lab's namespace and throwaway policy cluster.
RG=rg-aks-labs
NP_AKS=aks-lab-np
NS=lab34

kubectl delete ns $NS --ignore-not-found 2>/dev/null || true
az aks delete -g $RG -n $NP_AKS --yes --no-wait""",
},
# ---------------------------------------------------------------- 3.5
{
"id": "3.5",
"title": "Control outbound traffic",
"time": "40 min",
"level": "Advanced",
"objective": "Inspect the shared cluster outbound path, measure pod egress IP, and plan safer SNAT and firewall designs without disrupting the lab cluster.",
"exam": [
 "Default AKS outbound is commonly <code>loadBalancer</code>: the Standard Load Balancer provides SNAT through managed outbound public IPs, often starting with <b>1</b> managed IP.",
 "Load balancer outbound rule <code>allocatedOutboundPorts=0</code> means Azure auto-allocates SNAT ports per node; scale changes can change per-node port allocation.",
 "Managed NAT Gateway gives <b>64,512</b> SNAT ports per public IP and supports up to <b>16</b> public IPs, making it the usual fix for high outbound connection counts.",
 "<code>userDefinedRouting</code> sends egress to your route table next hop, commonly Azure Firewall or an NVA; you own default routes, allowed FQDNs and return paths.",
 "SNAT exhaustion looks like intermittent TCP timeouts to external dependencies while pod-to-pod and in-cluster DNS keep working.",
 "Azure Firewall AKS lockdown should use the <code>AzureKubernetesService</code> FQDN tag plus required endpoints such as <code>mcr.microsoft.com</code>, <code>*.data.mcr.microsoft.com</code>, <code>management.azure.com</code>, <code>login.microsoftonline.com</code> and <code>packages.microsoft.com</code>.",
 "Tunnel traffic for private control-plane connectivity may require network rules for TCP <code>9000</code> and UDP <code>1194</code> depending on cluster generation and connectivity mode.",
 "API server authorized IP ranges protect the public API endpoint; if egress is forced through a firewall, include the firewall public IP or kubectl clients behind it will be blocked.",
],
"prereq": "Shared cluster <code>aks-lab</code>. This lab is intentionally read-only for cluster outbound configuration; update commands are shown but not run.",
"portal": [
 "##Current outbound configuration",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab</code> \u2192 <b>Networking</b>. Note <b>Outbound type</b>, network plugin mode and any authorized IP range settings.",
 "Open the <code>MC_*</code> node resource group \u2192 <b>Load balancer</b> \u2192 <b>Outbound rules</b>. Check frontend IP count and allocated outbound ports if the cluster uses load balancer outbound.",
 "##NAT gateway target design",
 "Open <b>NAT gateways</b> \u2192 <b>+ Create</b>. Note that NAT Gateway attaches to subnets and can use up to <code>16</code> public IP addresses or prefixes for more SNAT ports.",
 "Do not attach NAT Gateway to the shared lab subnet from the portal during this lab. Changing AKS outbound type is a cluster networking operation and can disrupt running labs.",
 "##Firewall lockdown target design",
 "Open <b>Azure Firewall</b> \u2192 <b>Firewall Policy</b> \u2192 <b>Application rules</b>. Use the <code>AzureKubernetesService</code> FQDN tag instead of hand-copying every AKS control-plane dependency when possible.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
LOC=eastus2
NS=lab35

az aks get-credentials -g $RG -n $AKS --overwrite-existing
NODE_RG=$(az aks show -g $RG -n $AKS --query nodeResourceGroup -o tsv)

az aks show -g $RG -n $AKS \
  --query '{outboundType:networkProfile.outboundType, managedOutboundIPs:networkProfile.loadBalancerProfile.managedOutboundIPs.count, effectiveOutboundIPs:networkProfile.loadBalancerProfile.effectiveOutboundIPs[].id, authorizedRanges:apiServerAccessProfile.authorizedIpRanges}' -o json

az network lb outbound-rule list -g $NODE_RG --lb-name kubernetes -o table 2>/dev/null || true
az network public-ip list -g $NODE_RG --query '[].{name:name, ip:ipAddress, sku:sku.name}' -o table

# Documented migration path only. Review maintenance window and current support before running.
cat <<'EOF'
# Create NAT Gateway resources for an AKS subnet, then update outbound type.
az network public-ip create -g rg-aks-labs -n pip-aks-nat -l eastus2 --sku Standard --allocation-method Static
az network nat gateway create -g rg-aks-labs -n nat-aks -l eastus2 --public-ip-addresses pip-aks-nat
az network vnet subnet update -g <vnet-rg> --vnet-name <vnet-name> -n <aks-subnet> --nat-gateway nat-aks
az aks update -g rg-aks-labs -n aks-lab --outbound-type managedNATGateway

# UDR plus Azure Firewall pattern.
az aks update -g rg-aks-labs -n aks-lab --outbound-type userDefinedRouting
EOF""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
AKS=aks-lab
NS=lab35

az aks get-credentials -g $RG -n $AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n $NS -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: egress-check
spec:
  restartPolicy: Never
  containers:
  - name: agnhost
    image: registry.k8s.io/e2e-test-images/agnhost:2.45
    command: ["sleep", "3600"]
EOF

kubectl wait --for=condition=Ready pod/egress-check -n $NS --timeout=120s
kubectl exec -n $NS egress-check -- /agnhost connect --timeout=5s ifconfig.me:80 || true
kubectl exec -n $NS egress-check -- /agnhost connect --timeout=5s icanhazip.com:80 || true

# If agnhost output is too low-level for your shell, use a one-shot nginx-free busybox request.
kubectl run wget-egress --rm -i --restart=Never -n $NS --image=busybox:1.36 -- \
  wget -qO- --timeout=10 http://ifconfig.me || true

kubectl describe pod egress-check -n $NS""",
"traps": [
 "Updating outbound type on a shared cluster can restart or reconfigure networking; treat it as a maintenance-window change, not a casual lab command.",
 "Adding firewall UDRs before allowing AKS required FQDNs blocks image pulls, node bootstrapping, upgrades and extension traffic.",
 "SNAT exhaustion is often misdiagnosed as DNS or application bugs because failures appear as random external TCP timeouts under load.",
 "API server authorized IP ranges apply to the public API endpoint, not pod egress; locking the API to the wrong CIDR makes kubectl fail before workloads change.",
 "NAT Gateway SNAT capacity is per public IP; one busy cluster can still exhaust ports if all pods hammer the same external IP and port combination.",
],
"cleanup": r"""# Delete only the namespace created for egress checks.
NS=lab35
kubectl delete ns $NS --ignore-not-found

# If you intentionally created NAT resources from the documented example, delete them explicitly:
# az network nat gateway delete -g rg-aks-labs -n nat-aks --yes
# az network public-ip delete -g rg-aks-labs -n pip-aks-nat --yes""",
},
# ---------------------------------------------------------------- 3.6
{
"id": "3.6",
"title": "Harden API server access",
"time": "45 min",
"level": "Advanced",
"objective": "Create a private AKS cluster, understand private DNS requirements, and compare private API access with public authorized IP ranges and command invoke break-glass.",
"exam": [
 "<code>--enable-private-cluster</code> places the API server behind a private endpoint in the cluster VNet; the public API endpoint is disabled for normal kubectl access.",
 "Private cluster DNS uses <code>privatelink.&lt;region&gt;.azmk8s.io</code>; <code>--private-dns-zone system</code> lets AKS manage the private zone, while <code>none</code> or custom zones require you to handle resolution.",
 "Access paths for private clusters include a VM in the VNet, peered VNet, VPN, ExpressRoute, Cloud Shell connected to a VNet, or <code>az aks command invoke</code>.",
 "Public clusters can restrict the API endpoint with <code>--api-server-authorized-ip-ranges</code> CIDRs; your current egress IP must be listed or kubectl immediately fails.",
 "Authorized IP ranges protect the public API endpoint and are not combined with the normal private-cluster endpoint design; choose private endpoint or public endpoint with CIDR restriction deliberately.",
 "<code>az aks command invoke</code> runs a command pod inside the cluster and requires RBAC permission for the AKS <code>runCommand</code> action, making it useful break-glass access.",
 "API Server VNet Integration is the newer evolution that projects API server connectivity into your VNet in supported regions; check current GA and region support before standardizing on it.",
 "Private clusters change CI/CD design: hosted agents outside the VNet cannot run kubectl unless they use command invoke or a self-hosted runner with network reachability.",
],
"prereq": "This lab creates throwaway private cluster <code>aks-lab-priv</code> in <code>rg-aks-labs</code>. Delete it in cleanup to stop cost.",
"portal": [
 "##Create and inspect private access",
 "Open <b>Kubernetes services</b> \u2192 <code>aks-lab-priv</code> after the CLI create. On <b>Overview</b>, note that normal portal views work through Azure Resource Manager even when your laptop cannot reach the private API server.",
 "Open <b>Networking</b> \u2192 confirm <b>Private cluster</b> is enabled and review DNS settings. The private endpoint and private DNS zone are Azure resources, not Kubernetes objects.",
 "Open the managed resource group <code>MC_*</code> \u2192 find the <b>Private endpoint</b> and private DNS zone link. Confirm the zone name uses <code>privatelink.eastus2.azmk8s.io</code> for this region.",
 "##Portal-side command execution",
 "Use <b>Cloud Shell</b> if it has VNet reachability, or run <code>az aks command invoke</code> from Cloud Shell. Command invoke is useful when your workstation cannot resolve or route to the private endpoint.",
 "##Public endpoint alternative",
 "For the shared public cluster, open <code>aks-lab</code> \u2192 <b>Networking</b> \u2192 <b>API server authorized IP ranges</b>. This is the public-endpoint hardening option, not the private-cluster option.",
],
"cli": r"""# Azure CLI (bash) -- complete, runnable, commented
RG=rg-aks-labs
AKS=aks-lab
PRIV_AKS=aks-lab-priv
LOC=eastus2

# Create a throwaway private cluster. Cost warning: this creates VM capacity.
az aks create \
  -g $RG -n $PRIV_AKS -l $LOC \
  --node-count 1 --node-vm-size Standard_B2s \
  --network-plugin azure \
  --network-plugin-mode overlay \
  --pod-cidr 10.250.0.0/16 \
  --service-cidr 10.251.0.0/16 \
  --dns-service-ip 10.251.0.10 \
  --enable-private-cluster \
  --private-dns-zone system \
  --generate-ssh-keys

az aks show -g $RG -n $PRIV_AKS \
  --query '{private:apiServerAccessProfile.enablePrivateCluster, fqdn:fqdn, privateFqdn:privateFqdn, dnsZone:apiServerAccessProfile.privateDnsZone}' -o json

# This may fail from a workstation without VNet DNS and routing to the private endpoint.
az aks get-credentials -g $RG -n $PRIV_AKS --overwrite-existing
kubectl get nodes || echo "Expected from outside the VNet: private API is not reachable"

# Break-glass: ARM asks the cluster to run kubectl internally.
az aks command invoke -g $RG -n $PRIV_AKS --command "kubectl get nodes -o wide"

# Public cluster hardening example. Find your current public egress IP first.
MY_IP=$(curl -s https://ifconfig.me || true)
echo "Current egress IP: $MY_IP"
cat <<EOF
# Public endpoint alternative; run only after confirming all admin and CI CIDRs.
az aks update -g $RG -n $AKS --api-server-authorized-ip-ranges ${MY_IP}/32
EOF""",
"kubectl": r"""# kubectl & YAML -- complete, runnable
RG=rg-aks-labs
PRIV_AKS=aks-lab-priv
NS=lab36

# From outside the VNet this direct kubectl path may fail by design.
az aks get-credentials -g $RG -n $PRIV_AKS --overwrite-existing
kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f - || true

# Use command invoke for portal/ARM-side verification when direct API access is blocked.
az aks command invoke -g $RG -n $PRIV_AKS --command "kubectl create ns $NS --dry-run=client -o yaml | kubectl apply -f -"
az aks command invoke -g $RG -n $PRIV_AKS --command "kubectl apply -n $NS -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: private-check
spec:
  replicas: 1
  selector:
    matchLabels:
      app: private-check
  template:
    metadata:
      labels:
        app: private-check
    spec:
      containers:
      - name: nginx
        image: nginx:1.27
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: private-check
spec:
  selector:
    app: private-check
  ports:
  - port: 80
    targetPort: 80
EOF"

az aks command invoke -g $RG -n $PRIV_AKS --command "kubectl rollout status deploy/private-check -n $NS && kubectl get pods,svc -n $NS -o wide"

# If you are on a VM or runner inside the VNet, direct kubectl should now work too.
kubectl get pods -n $NS -o wide || true""",
"traps": [
 "Private cluster failures often look like kubeconfig problems, but the real issue is DNS resolution for <code>privatelink.&lt;region&gt;.azmk8s.io</code> or no route to the private endpoint.",
 "Hosted CI agents on the public internet cannot reach a private API server; use self-hosted agents in the VNet, VPN/peering, or <code>az aks command invoke</code>.",
 "Authorized IP ranges are easy to lock yourself out with; add your current egress IP and corporate/VPN CIDRs before saving changes on a public cluster.",
 "Custom private DNS zones require correct VNet links and records; choosing <code>none</code> means AKS will not fix name resolution for you.",
 "Command invoke is not a network tunnel and not a replacement for day-to-day operations; it is audited ARM access and depends on RBAC for runCommand.",
],
"cleanup": r"""# Delete only the throwaway private cluster created by this lab.
RG=rg-aks-labs
PRIV_AKS=aks-lab-priv

az aks delete -g $RG -n $PRIV_AKS --yes --no-wait

# If you changed authorized ranges on the shared cluster, restore them explicitly:
# az aks update -g $RG -n aks-lab --api-server-authorized-ip-ranges """,
},
]
