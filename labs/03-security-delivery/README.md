# Day 3 - Identity, security, governance, and delivery

**Level:** 300 | **Hands-on:** approximately 6 hours

## Before you begin

- Instructor supplied the public GitHub course URL/branch and prepared two Entra test personas, or declared the authorization-only fallback.
- Read [identity and network security](../../docs/cheatsheets/identity-security-networking.md).
- Copy [the security evidence worksheet](security-evidence.md) to `evidence/day3-security.md`.
- Start and verify Standard:

```powershell
./scripts/start-lab.ps1 -Environment standard
./scripts/show-lab.ps1 -Environment standard
```

## Outcome

You can grant least-privilege human and workload access, retrieve a Key Vault secret without static credentials, enforce namespace and network boundaries, and make Git reconciliation the supported delivery path.

## Must-know facts

- Authentication establishes identity; authorization decides allowed actions. Azure RBAC and Kubernetes RBAC can both participate in AKS access.
- Disable local AKS accounts so kubeconfig is not a shared administrative credential.
- Workload Identity exchanges a signed Kubernetes service-account token through OIDC for short-lived Azure credentials.
- The federated credential subject must exactly match `system:serviceaccount:<namespace>:<name>`.
- Key Vault RBAC controls data-plane actions. CSI mounts data; it does not make every pod authorized.
- Pod Security Admission, policy, quotas, and network policy cover different controls.
- Default-deny policy requires explicit DNS and application flows.
- Flux pulls and reconciles; CI should validate artifacts, not hold cluster credentials.
- Mutable tags and unsigned images weaken provenance even when the registry is private.

## Challenge

### 1. Separate human duties

Create two Entra-backed personas:

- Platform operator: cluster-wide read plus controlled platform administration.
- Application operator: manage workload objects only in `orders`.

Do not create Kubernetes users or distribute certificates. Prove one allowed and one denied action for each persona using `kubectl auth can-i` with impersonation where permitted.

Real persona sign-in proves Entra authentication. `--as` proves authorization behavior only.

The instructor applies the prepared group assignments with `configure-personas.ps1`; learners do not paste group IDs into course files.

### 2. Give the API an Azure identity

1. Create the disposable `course-api-key` value in the provisioned Key Vault without placing it in Git.
2. Render the identity component with concrete client, vault, and tenant values.
3. Mount the value through the CSI driver.
4. Call `/api/config` and prove only mount state and a digest prefix are exposed.
5. Inspect the federated identity subject, OIDC issuer, service-account annotation, pod label, and Key Vault role assignment.

Use the secret creation steps in the Day 3 reference, then deploy:

```powershell
./scripts/deploy-workload.ps1 -Target azure -Environment standard -Stage day3
./scripts/validate-lab.ps1 -Environment standard -Check Identity
```

### 3. Enforce boundaries

Apply resource quota, limit range, restricted pod security, and default-deny policies. Prove:

- Storefront can reach orders-api.
- An unrelated pod cannot reach orders-api.
- DNS still works for allowed pods.
- A privileged pod is rejected.
- A workload exceeding quota is rejected with a useful admission message.

Use `labs/03-security-delivery/manifests/connectivity-probe.yaml` as the unrelated source for the denied-flow test.

```powershell
kubectl apply -f labs/03-security-delivery/manifests/connectivity-probe.yaml
kubectl wait --for=condition=Ready pod/connectivity-probe -n orders --timeout=2m
kubectl exec -n orders connectivity-probe -- python -c "import urllib.request; urllib.request.urlopen('http://orders-api:8080/healthz', timeout=3)"
kubectl exec -n orders deployment/storefront -- python -c "import urllib.request; print(urllib.request.urlopen('http://orders-api:8080/healthz', timeout=3).read().decode())"
kubectl delete -f labs/03-security-delivery/manifests/connectivity-probe.yaml
```

The unrelated probe should time out or be denied; storefront should succeed.

### 4. Reconcile through Git

Bootstrap managed Flux to the learner's public fork/branch. Configure `platform/environments/azure-day3` as desired state, enable pruning, and prove:

- A manual drift is reverted.
- An invalid manifest is blocked in CI before merge.
- Removing a Git object prunes it only from the intended scope.
- CI does not authenticate to the cluster.

```powershell
$repoUrl = "https://github.com/naytron/aks-labs"
./scripts/bootstrap-gitops.ps1 -RepositoryUrl $repoUrl -Branch main -Stage day3
flux get all -A
```

## Checkpoints

- Real/fallback persona method is recorded and not overstated.
- `/api/config` reports the Key Vault mount without revealing content.
- Allowed and denied traffic matrix matches the security cheat sheet.
- Privileged and over-quota manifests are rejected for the expected reason.
- Flux source/Kustomization are ready, manual drift is reverted, and prune stays inside the owned path.

## Acceptance criteria

- Local cluster accounts remain disabled.
- Least-privilege persona tests contain both allowed and denied evidence.
- No static Azure credential exists in pod spec, Secret, repository, or image.
- `/api/config` reports a mounted CSI secret without revealing it.
- Default-deny plus explicit DNS, gateway, and storefront-to-API policies pass connectivity tests.
- Restricted Pod Security and quota rejection are demonstrated.
- Flux reports ready source and Kustomization conditions and repairs drift.
- A commit/tag provenance strategy is documented.

## Break/fix

Change one character in the federated subject or service-account name, roll the API, and diagnose the CSI mount failure. Restore the Git/IaC source before continuing.

```powershell
./scripts/inject-failure.ps1 -Scenario network -Environment standard -Stage day3
./scripts/collect-evidence.ps1 -Incident day3-network -Environment standard
./scripts/inject-failure.ps1 -Scenario network -Environment standard -Stage day3 -Restore
```

## Hints

1. For CSI failures, pod events and provider logs are more useful than application logs.
2. Compare issuer, audience, and exact subject before changing role assignments.
3. For network policy, test DNS and TCP separately from a labeled ephemeral pod.

## Tips and production notes

- **Tip:** Draw issuer, audience, subject, identity, role, vault, and object before changing RBAC.
- **Why it matters:** a successful CSI mount proves several identity and authorization boundaries at once.
- **Production default:** assign access to Entra groups, not individual learners.
- **Lab shortcut:** the public repository allows credential-free Flux reads; private production repositories require managed authentication design.

## Cleanup

Restore the federated subject and network policy. Delete ephemeral test pods and any role assignments created only for simulated personas. Keep Flux and the workload for Day 4. Do not stop the cluster until the daily gate passes.

## Daily gate

```powershell
./scripts/validate-lab.ps1 -Gate Day3
./scripts/cleanup-lab.ps1 -Mode Daily
```

Submit authorization matrix, identity-flow diagram, connectivity matrix, and Flux drift evidence. See the [Day 3 reference](../../solutions/day-3.md).

**Next state:** Standard is stopped; Flux remains configured for the public repository.
