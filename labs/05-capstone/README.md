# Day 5 - Level 400 incident and production capstone

**Level:** 400 | **Hands-on:** approximately 6 hours

## Before you begin

- Days 1-4 gates passed; public Git remote and Flux are healthy.
- Start Standard and confirm a clean learner branch:

```powershell
./scripts/start-lab.ps1 -Environment standard
./scripts/show-lab.ps1 -Environment standard
git status --short
git switch -c "capstone/<learner-alias>"
```

- Keep [kubectl triage](../../docs/cheatsheets/kubectl-triage.md) and the [capstone rubric](../../docs/capstone-rubric.md) open.
## Outcome

You can operate an unfamiliar AKS failure, deliver a production-style platform from source, and defend trade-offs across reliability, security, cost, operational excellence, and performance.

## Must-know facts

- Level 400 work begins when the answer is not in the lab steps.
- Preserve evidence before remediation. A restart that clears symptoms can destroy root-cause data.
- Classify the failure plane: client, route, service discovery, workload, scheduler, storage, identity, network, node, or Azure control plane.
- Change one variable per hypothesis and prefer reversible actions.
- Recovery, root cause, and prevention are separate deliverables.
- Production readiness is an explicit set of SLO, ownership, threat, cost, recovery, and change-management decisions.
- A design is not mature until its failure modes and operational burden are understood.

## Challenge

### Part A - Incident gauntlet

The instructor injects three faults, including at least one compound incident. Possible symptoms include:

- `Pending`
- `ImagePullBackOff`
- `CrashLoopBackOff`
- `OOMKilled`
- readiness/rollout failure
- DNS or Service selection failure
- NetworkPolicy denial
- PVC/attachment issue
- Workload Identity or CSI failure
- node drain blocked by availability policy

For each incident:

1. Declare impact and start a timeline.
2. Collect evidence with `collect-evidence.ps1`.
3. Identify the fault plane and competing hypotheses.
4. Run discriminating tests.
5. Recover service with the lowest-risk reversible action.
6. Prove recovery from the user and control-plane perspectives.
7. Complete [the incident report](incident-report-template.md).

Collect evidence with the explicit environment:

```powershell
./scripts/collect-evidence.ps1 -Incident "<incident-name>" -Environment standard
```

### Part B - Production platform capstone

Starting from a clean branch and the existing Standard environment, deliver a platform that meets the fictional requirements in [capstone-scenario.md]. You may reuse repository components but must own every parameter and trade-off.

Required deliverables:

- Bicep and deployment preview.
- GitOps-managed workload release.
- Human and workload identity model.
- Key Vault integration with no static credential.
- Namespace, admission, resource, and network controls.
- Gateway API route, persistent-data decision, scaling, metrics, logs, and alerts.
- Safe rollout, PDB/topology, upgrade, backup, and DR decisions.
- Cost inventory and cleanup plan.
- [Runbook](runbook-template.md) and [architecture decision](adr-template.md).

### Part C - Defense

In 15 minutes, explain:

1. Why AKS is justified for this workload.
2. Why Automatic or Standard is the better production target.
3. Which Day-0 decision carries the largest future migration cost.
4. How identity, network, supply chain, and admission controls combine.
5. How the platform meets its SLO and what it costs.
6. The first failure you expect at 10x load.

## Checkpoints

- After each incident, user impact, hypotheses, evidence, recovery proof, cause, and prevention are distinct.
- Before defense, every rubric row links to evidence or a deliberate documented exception.
- `git diff` contains no credential, generated kubeconfig, or secret value.
- Flux reports ready after the capstone branch/source strategy selected by the instructor.
- Final external and internal order transactions succeed.

## Acceptance criteria

- All criteria in [the capstone rubric](../../docs/capstone-rubric.md) are demonstrably met.
- Static validation and Bicep `what-if` pass.
- Flux is healthy and repairs drift.
- Application validation passes from outside and inside the cluster.
- Secrets are absent from repository, rendered public evidence, and images.
- Incident reports distinguish impact, recovery, root cause, and prevention.
- The defense makes explicit trade-offs rather than reciting features.
- Final cleanup is run and Azure deletion is verified.

## Break/fix

The incident gauntlet is the break/fix. Learners do not see scenario names. The instructor may combine two faults only if each has independent evidence and a deterministic restore path.

## Hints

1. Reconstruct the request path and find the last healthy boundary.
2. Compare desired state, observed state, controller conditions, and recent events.
3. When evidence conflicts, check time windows, rollout revisions, and whether you are observing the correct context/namespace/pod.

## Tips and production notes

- **Tip:** Find the last healthy boundary before examining every component.
- **Why it matters:** recovery can destroy evidence; preserve it first.
- **Production default:** a recommendation must include ownership, SLO, threat, recovery, and cost consequences.
- **Stop and check:** do not delete the final resource group until assessment evidence is copied and reviewed.

## Cleanup

Before cleanup:

```powershell
./scripts/validate-lab.ps1 -Gate Day5
```

After assessment, continue directly to [the optional ARC module](../06-arc-runners/README.md) if the instructor is delivering it. Pass the Day 5 gate but delay final resource-group deletion; keep Standard running and use the ARC cleanup contract before final lab deletion.

Otherwise, delete the lab:

```powershell
./scripts/cleanup-lab.ps1 -Mode Final -Wait
```

Verify the resource group is absent, inspect for unexpected resources, delete local evidence containing identifiers, and review delayed Cost Management records the following day.

## Daily gate

Pass mark is 80/100 with no critical security failure. Submit three incident reports, capstone artifacts, validator evidence, runbook, ADR, cost inventory, and final cleanup evidence.
