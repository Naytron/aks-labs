# ARC optional module reference solution

Use this only after collecting learner evidence. Example values below are descriptive and deliberately omit repository names, IDs, keys, subscriptions, tenants, and Secret data.

## 1. Trust and architecture reasoning

A correct trust model starts with the fact that a self-hosted runner executes workflow-controlled code inside the operator's network. The repository is therefore not merely a source location; its administrators, branch controls, workflow editors, dispatchers, dependencies, and environment approvers are part of the compute trust boundary.

The lab accepts the existing Standard AKS cluster only as a cost and setup shortcut. It still isolates runner pods on a dedicated tainted node pool and separates `arc-systems` from `arc-runners`. A production recommendation uses a separate runner cluster because that isolates Kubernetes administration, network reachability, capacity exhaustion, upgrades, policy exceptions, telemetry, and incident response from application clusters.

Example decision evidence:

```text
Target visibility: private, verified before install
App installation: selected repository only
Trigger: manual dispatch only
Runner lifecycle: one job, then pod and registration removed
Lab cluster: shared Standard cluster, accepted only for training
Production: separate runner cluster with named platform ownership
```

The public `naytron/aks-labs` repository is never an acceptable live target. Making a runner ephemeral does not make public or fork-controlled code trusted.

## 2. Capacity isolation

`manage-arc-runner-pool.ps1` should produce a dedicated pool that:

- has a runner-specific taint and labels;
- enables node autoscaling;
- has minimum zero and an explicit maximum;
- permits only matching runner pods;
- leaves ARC controller pods on non-runner system capacity.

The taint is a security and reliability boundary, not a troubleshooting inconvenience. If runner pods remain `Pending`, compare their tolerations and affinity with the pool before changing the taint.

Example sanitized evidence:

```text
Pool role: dedicated ARC runners
Autoscaler: enabled
Minimum: 0
Maximum: bounded by course policy
Idle state: no runner node after the node autoscaler settled
Controller placement: system capacity, outside runner pool
```

## 3. Secure installation

The deployment uses GitHub App authentication. The App is installed only on the private sandbox repository. Repository Administration read/write is the runner-registration authority needed for a repository-scoped configuration; mandatory metadata access remains read-only. No unrelated repository or organization permission is added.

The key is passed to `deploy-arc.ps1` by file path. The script creates the Kubernetes Secret without placing private-key text in Helm `--set` values, a checked-in values file, or terminal output. Evidence records only the Secret reference and resource conditions.

Expected topology:

```text
arc-systems
  pinned ARC controller release, controller pod, and listener

arc-runners
  pinned runner scale set release
  authentication Secret reference
  runner scale set and ephemeral runner resources
  zero idle runner pods when minRunners is zero
```

Example safe evidence:

```text
Controller namespace: arc-systems
Runner namespace: arc-runners
Controller condition: Ready
Scale set condition: Ready
Authentication: GitHub App Secret reference present
Credential values captured: no
```

## 4. Two-layer autoscaling

The key reasoning is controller ownership:

1. A human dispatches the bounded matrix workflow.
2. GitHub assigns jobs to the configured runner scale set.
3. ARC requests ephemeral runner resources and pods for assigned work.
4. The pods are initially unschedulable because the runner pool is at zero.
5. Kubernetes scheduling evidence makes that demand visible; AKS cluster autoscaler adds a node within the configured maximum.
6. The runner starts, accepts one job, and exits after completion.
7. ARC removes the ephemeral runner resource and pod.
8. With no remaining runner pods, AKS can later remove the now-unneeded node.

ARC does not create AKS nodes, and AKS does not decide how many jobs need runners. `minRunners: 0` controls idle runner pods, bounded `maxRunners` controls runner concurrency, and the node-pool minimum and maximum control a separate capacity layer. Both minima are zero in this lab, but their scale-down timers and observations are independent.

Example timeline:

| UTC order | Observation | Owner |
| --- | --- | --- |
| 1 | Four manual matrix jobs dispatched | GitHub |
| 2 | Ephemeral runner resources appeared | ARC |
| 3 | Runner pods were `Pending` with scheduling events | Scheduler |
| 4 | Dedicated pool began adding capacity | AKS cluster autoscaler |
| 5 | Four jobs ran within configured bounds | ARC and kubelet |
| 6 | Each runner disappeared after one job | ARC |
| 7 | Dedicated node capacity later returned to zero | AKS cluster autoscaler |

Cloud timing varies. A long observation is not itself a failure. Conditions and events must show whether reconciliation is progressing.

The supplied `test-arc-scale.ps1` dispatches the private workflow, samples only runner/resource/node counts, requires concurrent runner evidence and at least one dedicated node, then waits for runner deletion and the configured node scale-down gate.

## 5. Security, observability, and upgrade

The provided workflow is intentionally limited:

- only `workflow_dispatch`;
- `permissions: {}`;
- four bounded shell jobs;
- no checkout or third-party action;
- no kubeconfig, service-account token, or deployment credential;
- no Docker socket, host path, or privileged DinD;
- a job timeout.

A production runner pod review should additionally cover non-root execution where the supported runner image permits it, immutable image references, admission policy, workload identity, egress allow lists, DNS, artifact and dependency trust, vulnerability response, and log redaction.

Useful signals and their questions:

| Signal | Question answered |
| --- | --- |
| GitHub job queue and run log | Was the job assigned and did its shell step finish? |
| ARC controller log and conditions | Did ARC reconcile registration and runner demand? |
| Ephemeral runner conditions | Did a runner register, become busy, and terminate? |
| Pod state and events | Did image pull, admission, scheduling, or startup fail? |
| AKS node-pool state | Was capacity requested, bounded, added, and removed? |
| Kubernetes and GitHub audit | Who changed configuration or dispatched work? |

An acceptable upgrade runbook does not assume an order from memory. It reads the release notes and compatibility guidance for the pinned source and target versions, tests a canary scale set, stops new dispatches, retains old values and image references, validates registration and a safe job, and rolls back before removing the known-good version. Abort on registration failure, unschedulable runners caused by the change, job failure, credential exposure, unexpected privilege, or loss of required telemetry.

## 6. Failure diagnosis and recovery

The deterministic failure breaks the relationship between runner pod placement and the dedicated runner pool. The expected signature is:

```text
GitHub: job queued for the intended scale set
ARC: ephemeral runner requested
Pod: created but Pending
Event: FailedScheduling cites an incompatible placement constraint
Node autoscaler: cannot repair an impossible label, taint, or affinity match
```

Correct diagnosis separates this from App authentication failure, controller failure, or a pool at its maximum. Removing the taint or broadening placement would hide the fault and weaken isolation.

Recovery uses:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling -Restore
./scripts/validate-arc.ps1 -Check Install
```

The unchanged workflow is dispatched again. Successful evidence shows registration, running jobs, one-job runner deletion, and eventual node scale-down. Keeping the workflow unchanged proves that restoration, not an unrelated workflow edit, caused recovery.

## Cleanup evidence

Safe order:

1. Finish or cancel jobs.
2. Run `cleanup-arc.ps1`.
3. Validate that releases, namespaces, and authentication material are absent.
4. Rerun `manage-arc-runner-pool.ps1 -Action Delete` to prove node-pool cleanup is idempotent.
5. Remove the App installation, revoke the course key, and delete the local key file.
6. Confirm Git contains no credential or private target identifier.
7. Stop the Standard cluster when no later exercise needs it.

Example final evidence:

```text
Queued/in-progress jobs: 0
arc-systems: absent
arc-runners: absent
Runner pool: absent
Course App installation/key: removed
Local key file: absent
Credential findings in Git diff: 0
```
