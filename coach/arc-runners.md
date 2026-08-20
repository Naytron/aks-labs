# Coach guide - optional ARC runner module

Learners must not use this guide during diagnosis.

## Purpose and safety boundary

This module demonstrates GitHub Actions Runner Controller on the existing Standard AKS cluster as a lab-only shortcut. The live target must be an instructor-approved private sandbox repository. Public `naytron/aks-labs`, a public fork, production source, and repositories with real deployment credentials are prohibited.

Stop the exercise immediately if:

- repository visibility is public or uncertain;
- the GitHub App is installed beyond the intended private repository;
- a private key, token, Secret value, private repository identifier, subscription ID, or tenant ID appears in evidence;
- a learner proposes `cluster-admin`, privileged DinD, a Docker socket, host paths, a kubeconfig, or removal of the runner taint;
- node-pool maximum, Azure context, cluster context, ownership, quota, or cleanup authority is uncertain;
- an unexpected workflow or queued job targets the runner scale set.

## Delivery sequence and expected evidence

### 1. Decision and trust model

Expected evidence:

- source, dispatcher, App, controller, scale set, runner pod, node, network, and dependency trust boundaries;
- private repository visibility verified without recording its identity;
- App installation limited to the selected repository;
- automatic pull request and fork execution rejected;
- existing Standard cluster identified as a lab shortcut;
- separate runner cluster recommended for production, with blast-radius and operations reasoning.

Reject "ephemeral is secure" as a complete argument. Ephemeral runners reduce persistence; they do not neutralize malicious workflow code or external side effects.

### 2. Capacity isolation

Run only through:

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Deploy
```

Expected evidence:

- dedicated tainted runner pool;
- minimum zero and explicit bounded maximum;
- controller and listener remain on always-on general capacity;
- runner workload has matching placement;
- no weakening of ordinary workload placement.

At minimum zero, a learner may see no runner node before a job exists. Accept node-pool configuration evidence plus the later autoscaling timeline.

### 3. Secure installation

Expected evidence:

- `arc-systems` controller and `arc-runners` runner resources;
- pinned releases and Ready conditions;
- Secret name or reference only;
- key path is ignored `.aks-labs` or a mounted external location, and the temporary file is deleted after successful installation;
- no Helm `--set` plaintext, copied values, decoded Secret, or screenshot of credentials.

Inspect evidence before accepting it. If a credential is exposed, stop, revoke the App key, remove the material, and follow the organization's incident process before continuing.

### 4. Two-layer autoscaling

Expected evidence is a UTC sequence across:

1. manual GitHub dispatch;
2. assignment to the intended scale set;
3. ephemeral runner object and pod creation;
4. scheduling pressure while the runner pool is at zero;
5. AKS node scale-up within bounds;
6. job execution;
7. one-job runner deletion;
8. later AKS node scale-down.

`test-arc-scale.ps1` must pass and write the count-only timeline. Learners should still correlate its samples with live GitHub, ARC condition, scheduler-event, and node evidence.

Timing varies with GitHub assignment, image retrieval, scheduler reconciliation, Azure capacity, cluster autoscaler scan and cooldown behavior, and node readiness. Do not give learners a duration promise. Ask for conditions, events, and forward progress instead of elapsed-time guesses. Do not restart the controller or dispatch more jobs merely to make the timeline faster.

### 5. Security, observability, and upgrade

Expected evidence:

- workflow is manual-only, shell-only, bounded, timed out, and has empty permissions;
- runner has no cluster credential, Docker socket, privileged mode, host path, host network, or privileged DinD;
- App scope, image provenance, chart/image pinning, egress, audit, and log-redaction decisions are addressed;
- upgrade runbook uses release notes, compatibility checks, a canary, abort criteria, retained rollback inputs, and a safe validation job.

Do not require learners to print Helm values or Secret objects. Names, versions, conditions, timestamps, pod security fields, and sanitized logs are sufficient.

## Deterministic failure injection and recovery

Before injection:

1. Confirm the private workflow has completed successfully once.
2. Confirm no unrelated jobs are queued.
3. Confirm the current Kubernetes context and runner namespace.
4. Preserve the known-good output of `validate-arc.ps1`.
5. Record the exact injection and restore action privately.

Inject only:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling
```

Expected failure:

- GitHub job targets the correct scale set;
- ARC requests an ephemeral runner;
- the runner pod is `Pending`;
- `FailedScheduling` identifies a placement mismatch;
- adding nodes cannot satisfy the impossible relationship.

Hint ladder:

1. Ask which acceptance criterion failed first.
2. Ask whether GitHub assigned the job.
3. Ask whether ARC created a runner object and pod.
4. Ask for the first scheduler event.
5. Ask the learner to compare requested placement with labels and taints.

Safety stops:

- Do not inject an App key, permission, repository visibility, node maximum, system-pool, network, or credential failure.
- Do not combine failures.
- Do not allow a second controller or scale set as a workaround.
- Do not allow taint removal, broad tolerations, maximum increases, or privileged access.

Restore only through:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling -Restore
./scripts/validate-arc.ps1 -Check Install
```

Recovery evidence uses the unchanged workflow and shows job success, one-job runner deletion, and eventual node scale-down. If restore validation fails, stop dispatching and compare against the known-good configuration before any other change.

## Cleanup gate

Require this order:

```powershell
./scripts/cleanup-arc.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
helm3 list --all-namespaces | Select-String 'arc-systems|arc-runners'
kubectl get namespace arc-systems arc-runners --ignore-not-found
./scripts/manage-arc-runner-pool.ps1 -Action Delete
./scripts/validate-arc.ps1 `
  -Check Cleanup `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
```

Then verify:

- no queued or in-progress job targets the scale set;
- both ARC releases and namespaces are absent;
- the authentication Secret disappeared with cleanup;
- the runner pool is absent;
- the App installation is removed and the course key revoked;
- the downloaded private key is deleted;
- Git evidence contains no credential or private target identifier;
- Standard is stopped if no later exercise requires it.

Do not accept cleanup based only on a successful script exit. Require GitHub, Kubernetes, Azure node-pool, local-file, and Git status evidence.
