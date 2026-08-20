# Optional post-capstone - GitHub Actions Runner Controller on AKS

**Level:** 400 | **Scope:** optional post-capstone module

## Before you begin

- Complete the capstone and pass the Day 5 gate.
- Start the existing Standard AKS lab cluster and confirm the expected context:

```powershell
./scripts/start-lab.ps1 -Environment standard
./scripts/show-lab.ps1 -Environment standard
kubectl config current-context
git status --short
```

- Obtain an instructor-approved **private sandbox repository** and a narrowly scoped GitHub App installation for only that repository.
- Never configure the public `naytron/aks-labs` repository, a learner fork of it, or any other public repository as the live runner target.
- Keep the temporary GitHub App private key in ignored `.aks-labs/arc-github-app.pem` inside the Dev Container workspace, or in a separately mounted external path. The script rejects a key inside any unignored repository path. Do not paste it into a command, values file, terminal transcript, screenshot, or evidence file.
- Copy [the decision worksheet](arc-decision-record.md) and [the evidence worksheet](arc-evidence.md) into the ignored `evidence/` directory.
- Keep [the ARC operations cheat sheet](../../docs/cheatsheets/arc-runner-operations.md) open.
- Treat local script help as authoritative for the checked-out script version:

```powershell
Get-Help ./scripts/manage-arc-runner-pool.ps1 -Full
Get-Help ./scripts/deploy-arc.ps1 -Full
Get-Help ./scripts/validate-arc.ps1 -Full
Get-Help ./scripts/inject-arc-failure.ps1 -Full
Get-Help ./scripts/cleanup-arc.ps1 -Full
```

## Outcome

You can design, install, observe, secure, scale, upgrade, troubleshoot, and remove an ephemeral GitHub Actions runner scale set on AKS. You can also explain why the shared Standard cluster is a lab shortcut and why a separate runner cluster is the production recommendation.

## Must-know facts

- A self-hosted runner executes repository-controlled code inside your trust boundary. Repository administration, workflow changes, reusable workflows, dependencies, environments, and secret access are security boundaries.
- The lab uses the existing Standard cluster only to control cost and setup time. Production runners should use a separate, policy-owned runner cluster unless a documented risk assessment proves equivalent isolation.
- `arc-systems` contains the ARC controller and runner scale set listener. `arc-runners` contains the runner scale set resource, its authentication Secret, and ephemeral runner pods. Keep controller and workload concerns separate.
- The runner node pool is dedicated, tainted, autoscaling, and configured with a minimum of zero and a bounded maximum. Runner pods must have matching placement constraints; ordinary workloads must not tolerate the runner taint.
- ARC and AKS implement different control loops. ARC creates one-job ephemeral runner pods from assigned jobs. AKS cluster autoscaler adds nodes only after pods cannot schedule. Scale-down also occurs in layers.
- `minRunners: 0` means idle runner pods are not retained. A bounded `maxRunners` limits concurrent runner demand. Neither setting guarantees immediate node removal or zero cost.
- The default test workflow is `workflow_dispatch` only. It uses shell steps, has empty token permissions, and receives no kubeconfig, cluster credential, Docker socket, or privileged Docker-in-Docker access.
- Ephemeral means one job per runner registration. It does not make untrusted code safe, erase external effects, or replace image, network, identity, and secret controls.
- The GitHub App private key is a credential. App and installation IDs identify objects but must still use placeholders in course evidence.
- Chart and runner image versions must be pinned and upgraded deliberately. Never infer compatibility from a `latest` tag.

## Challenge

### Challenge 1 - Decide the trust and isolation model

1. Draw the path from a human dispatch through GitHub, the GitHub App, the ARC controller, the runner scale set, the runner pod, and the runner node.
2. Identify who can change the workflow, dispatch it, approve protected environments, administer the App, read Kubernetes objects, and change the runner image.
3. List assets reachable from the runner network and the controls that prevent unintended access.
4. Compare the shared Standard cluster shortcut with a separate production runner cluster. Include blast radius, Kubernetes administration, network egress, patching, availability, cost, and evidence ownership.
5. Complete the first sections of [the decision worksheet](arc-decision-record.md). Reject automatic execution from pull requests and forks for this module.

Stop if the target repository is public, its visibility is uncertain, or the GitHub App is installed on more repositories than intended.

### Challenge 2 - Build isolated, scale-to-zero capacity

Create the lab runner pool through the repository abstraction:

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Deploy
```

Use the script output and Azure or Kubernetes read-only views to prove:

- the pool belongs to the Standard lab cluster;
- autoscaling is enabled with minimum zero and a bounded maximum;
- its taint and labels reserve it for runner pods;
- the always-on general pool remains available for the ARC controller and listener;
- no runner node is required while no runner pod is pending.

Useful read-only views:

```powershell
kubectl get nodes -L agentpool
kubectl get pods -A -o wide
```

Do not remove the taint to make scheduling work. The correct fix is a matching runner placement policy.

### Challenge 3 - Install ARC without exposing credentials

Verify the private repository and App installation with the instructor. Then run the deployment script with placeholders replaced locally:

```powershell
./scripts/deploy-arc.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>" `
  -GitHubAppId "<github-app-id>" `
  -GitHubAppInstallationId "<github-app-installation-id>" `
  -GitHubAppPrivateKeyPath "./.aks-labs/arc-github-app.pem"
```

The script, not a Helm `--set` argument, creates or updates the Kubernetes authentication Secret and installs pinned charts with `minRunners: 0` and a course-bounded `maxRunners`. Do not print, decode, export, or capture that Secret. After deployment succeeds, delete the downloaded private key file as directed by the instructor.

Prove the separation and registration without exposing secret data:

```powershell
kubectl get namespace arc-systems arc-runners
kubectl get pods -n arc-systems
kubectl api-resources | Select-String 'actions.github.com'
helm3 list -n arc-systems
helm3 list -n arc-runners
./scripts/validate-arc.ps1 -Check Install
./scripts/validate-arc.ps1 -Check Security
```

Record names, conditions, chart versions, and timestamps only. Do not include Secret YAML or Helm values containing credentials.

### Challenge 4 - Explain and observe two-layer autoscaling

1. Copy [the scale test template](templates/arc-scale-test.yml) into `.github/workflows/arc-scale-test.yml` in the **private sandbox repository**, not this course repository.
2. Replace `<arc-runner-scale-set-name>` with the scale set name reported by the deployment script.
3. Review the workflow before pushing it. Confirm it has only `workflow_dispatch`, shell steps, empty token permissions, a timeout, and no cluster or container-engine access.
4. Push to the private sandbox repository.
5. Start the read-only watches below, then use the course harness in another terminal to dispatch one run and capture count-only evidence:

```powershell
./scripts/test-arc-scale.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>" `
  -WorkflowFile "arc-scale-test.yml"
```

6. Observe the GitHub queue, ARC resources, runner pods, scheduler events, and AKS nodes in separate views:

```powershell
kubectl get pods -n arc-runners -o wide --watch
kubectl get events -n arc-runners --sort-by=.metadata.creationTimestamp
kubectl get nodes -L agentpool --watch
kubectl api-resources | Select-String 'actions.github.com'
```

Create a UTC timeline with these distinct transitions:

```text
dispatch -> job assignment -> ephemeral runner pod -> Pending
-> AKS node scale-up -> runner Ready -> job complete
-> runner deletion -> node becomes removable -> AKS node scale-down
```

Explain which controller owns every transition. Waiting is evidence: do not restart components merely because a cloud control loop is still reconciling. The four matrix jobs must never exceed the configured runner or node bounds.

After runner pods and ephemeral runner resources are gone:

```powershell
./scripts/validate-arc.ps1 -Check ScaleToZero
```

### Challenge 5 - Review security, observability, and upgrade design

Inspect only selected fields from the persistent runner template. Do not dump a live runner pod because short-lived registration data can appear in its environment:

```powershell
$runnerSet = kubectl get autoscalingrunnersets.actions.github.com -n arc-runners -o jsonpath='{.items[0].metadata.name}'
kubectl get autoscalingrunnersets.actions.github.com $runnerSet -n arc-runners -o jsonpath='hostNetwork={.spec.template.spec.hostNetwork} hostPID={.spec.template.spec.hostPID} serviceAccount={.spec.template.spec.serviceAccountName} automountToken={.spec.template.spec.automountServiceAccountToken}{"\n"}'
kubectl get autoscalingrunnersets.actions.github.com $runnerSet -n arc-runners -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{" privileged="}{.securityContext.privileged}{" allowPrivilegeEscalation="}{.securityContext.allowPrivilegeEscalation}{"\n"}{end}'
kubectl get autoscalingrunnersets.actions.github.com $runnerSet -n arc-runners -o jsonpath='{range .spec.template.spec.volumes[*]}{.name}{" hostPath="}{.hostPath.path}{"\n"}{end}'
kubectl get serviceaccount -n arc-runners
kubectl get events -n arc-runners --sort-by=.metadata.creationTimestamp
kubectl get deployment -n arc-systems
kubectl get podmonitor -n arc-systems
kubectl logs -n arc-systems deployment/arc-gha-rs-controller --tail=100
kubectl logs -n arc-systems -l app.kubernetes.io/component=runner-scale-set-listener --tail=100
./scripts/query-prometheus.ps1 -Query 'sum(gha_registered_runners)'
```

Prove or document the control that provides each of the following:

- no privileged container, host path, host network, Docker socket, or cluster credential;
- no default write permission for the workflow token;
- no long-lived idle runner;
- dedicated node placement and bounded concurrency;
- restricted App installation and private-repository scope;
- controlled image source, immutable version, vulnerability response, and outbound destinations;
- useful controller, runner, Kubernetes, Azure, and GitHub audit signals without secret logging.
- controller and listener PodMonitors plus a successful managed Prometheus query for an ARC metric.

Write an upgrade runbook that pins chart and runner image versions, reads release notes, checks Kubernetes and chart compatibility, tests a canary scale set, pauses new dispatches, preserves rollback inputs, validates one safe job, and removes the old version only after acceptance. State an abort condition for registration, scheduling, job completion, and security regression.

### Challenge 6 - Diagnose a deterministic failure and cleanly reverse it

Ask the coach to inject the approved scheduling failure:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling
```

Do not inspect the script. Use GitHub job status, runner resource conditions, pod state, scheduler events, node-pool bounds, taints, and runner placement to distinguish:

- no job assignment;
- ARC not creating a runner;
- runner pod created but unschedulable;
- node scale-up at its configured limit;
- runner started but job failed.

Preserve evidence, state a falsifiable hypothesis, and restore through the same abstraction:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling -Restore
./scripts/validate-arc.ps1 -Check Install
```

Dispatch the unchanged workflow again and prove successful registration, execution, runner deletion, and eventual node scale-down. Then complete the cleanup procedure below.

## Checkpoints

- The target is an instructor-approved private sandbox repository, never public `naytron/aks-labs`.
- The decision record identifies code, identity, network, cluster, and dependency trust boundaries.
- `arc-systems` and `arc-runners` exist and have distinct responsibilities.
- The runner pool is dedicated and tainted, has minimum zero, and has an explicit maximum.
- A dispatched job produces one-job ephemeral runners; runner pods disappear after their jobs.
- Evidence distinguishes ARC pod scaling from AKS node scaling.
- The workflow has only manual dispatch, empty token permissions, shell-only steps, and no cluster or privileged container access.
- Failure evidence shows why the runner pod cannot schedule before restoration.
- Validation passes after recovery and again before cleanup.

## Acceptance criteria

- [The decision worksheet](arc-decision-record.md) contains a defensible lab decision and a separate production recommendation.
- [The evidence worksheet](arc-evidence.md) contains UTC observations from GitHub, ARC, Kubernetes scheduling, and AKS node capacity.
- GitHub App authentication is used without key material in Git, command arguments, Helm values, screenshots, logs, or evidence.
- Controller and runner resources are separated into `arc-systems` and `arc-runners`.
- Runner pods land only on the dedicated tainted pool, and ordinary course workloads do not.
- The scale set is ephemeral, `minRunners` is zero, `maxRunners` is bounded, and the node pool maximum is bounded separately.
- Four manual matrix jobs complete using [the safe workflow template](templates/arc-scale-test.yml).
- `test-arc-scale.ps1` records at least two concurrent runner pods, at least one dedicated node, successful completion, runner deletion, and node scale-down.
- The learner explains delayed scale-up and scale-down without confusing controller ownership.
- Security and upgrade reviews include concrete evidence, abort criteria, and rollback boundaries.
- The deterministic failure is diagnosed from evidence and restored without weakening isolation.
- Cleanup removes ARC resources, authentication Secrets, and runner capacity, and the GitHub App installation is revoked or removed as instructed.

## Break/fix

The supported fault changes the runner placement relationship so assigned runner pods remain `Pending`. It must not alter the private repository, App permissions, credential, system pool, or node-pool maximum. Capture the first relevant `FailedScheduling` event and the pod's requested placement before restoring.

If the symptom differs, stop. Do not rotate credentials, increase the maximum, remove taints, install another controller, or dispatch more jobs until the coach confirms the fault boundary.

## Hints

1. Start at the GitHub job: was it assigned to the intended runner scale set?
2. If an ephemeral runner object exists, ask whether a pod was created and what its condition says.
3. `Pending` is not a reason. Read scheduler events and compare requested labels/tolerations with node-pool labels/taints.
4. Cluster autoscaler cannot make an impossible placement rule valid, and it cannot exceed the pool maximum.
5. After restore, reuse the unchanged workflow so only one variable changed.

## Tips and production notes

- **Tip:** Build one UTC timeline across GitHub, ARC resources, pods, events, and nodes.
- **Why it matters:** ARC and AKS are independent reconcilers with different signals and delays.
- **Lab shortcut:** the Standard cluster demonstrates the control loops at lower cost, but shares cluster administration and failure domains with course workloads.
- **Production default:** use a separate runner cluster with dedicated ownership, network policy and egress, identity, policy, patching, monitoring, capacity, and incident response.
- **Production design:** consider separate scale sets for trust classes. Do not mix public contribution, deployment credentials, and ordinary build work in one runner boundary.
- **Safety stop:** never troubleshoot by granting `cluster-admin`, mounting a Docker socket, enabling privileged DinD, changing a repository to public, or broadening the App installation.
- **Cost note:** scale-to-zero reduces idle runner compute, but the cluster, system capacity, disks, networking, logging, and delayed scale-down can still cost money.

## Cleanup

1. Cancel or let all private sandbox jobs finish. Confirm no queued or in-progress job targets the scale set.
2. Preserve sanitized evidence, then remove ARC releases, namespaces, and authentication material:

```powershell
./scripts/cleanup-arc.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
helm3 list --all-namespaces | Select-String 'arc-systems|arc-runners'
kubectl get namespace arc-systems arc-runners --ignore-not-found
```

3. Prove that cleanup is idempotent and that the dedicated runner node pool is absent:

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Delete
./scripts/validate-arc.ps1 `
  -Check Cleanup `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
```

4. In GitHub, remove the App installation from the private sandbox repository, revoke the course key, and delete the sandbox workflow or repository according to instructor policy.
5. Verify locally that the downloaded private key is absent and no key, kubeconfig, Secret export, or private URL was added to Git:

```powershell
git status --short
Get-ChildItem -Recurse -File -Include *.pem,*.key
Test-Path -LiteralPath "./.aks-labs/arc-github-app.pem"
kubectl get namespace arc-systems arc-runners --ignore-not-found
```

The key-path `Test-Path` result must be `False`, and the namespace checks must return no ARC resources.

6. Stop the Standard lab cluster when no later lab uses it:

```powershell
./scripts/cleanup-lab.ps1 -Mode Daily
```

Expected final state: no ARC namespaces or releases, no ARC authentication Secret, no runner pool, no queued runner job, no active App installation for the exercise, and no local private key.

## Daily gate

Submit the sanitized decision record, autoscaling timeline, security and upgrade review, failure diagnosis, successful recovery evidence, and cleanup proof. Pass only when every acceptance criterion is evidenced and no credential or private repository identifier appears in the submission. Use [the reference solution](../../solutions/arc-runners.md) only after completing the diagnosis.
