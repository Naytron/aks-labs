# ARC learner evidence

Use UTC. Record resource names only when they are course-generated and non-sensitive. Never include private repository identifiers, App or installation IDs, Secret data, key paths, subscription or tenant IDs, kubeconfigs, tokens, or screenshots containing them.

## Preflight

- UTC:
- Correct Standard cluster context proved:
- Private repository visibility checked without recording its name:
- App installation limited to that repository:
- Public `naytron/aks-labs` is not the target:
- Key file stored in ignored `.aks-labs` or a mounted external path and excluded from evidence:

## Capacity isolation

| Check | Expected | Observed evidence |
| --- | --- | --- |
| Runner pool | Dedicated pool | |
| Pool taint | Runner-only `NoSchedule` intent | |
| Pool labels | Match runner placement | |
| Autoscaler minimum | Zero | |
| Autoscaler maximum | Explicit and bounded | |
| Idle runner nodes | Zero after scale-down settles | |
| Controller placement | Non-runner system capacity | |

## Installation

| Component | Namespace | Version or condition | UTC evidence |
| --- | --- | --- | --- |
| ARC controller | `arc-systems` | | |
| Runner scale set | `arc-runners` | | |
| Runner scale set listener | `arc-systems` | | |
| Authentication Secret | Name/reference only; never value | | |

- `minRunners` observed:
- `maxRunners` observed:

## Two-layer autoscaling timeline

| UTC | GitHub job state | ARC desired/observed runner state | Runner pod state/reason | Runner node count/action | Controller responsible |
| --- | --- | --- | --- | --- | --- |
| | Dispatched | | | | GitHub/ARC |
| | Queued or assigned | | | | ARC |
| | | Runner requested | Pending | | ARC/scheduler |
| | | | Pending | Scale-up requested | AKS cluster autoscaler |
| | Running | Ready | Running | Node ready | ARC/kubelet |
| | Completed | Deleted | Deleted | Node retained temporarily | ARC |
| | Completed | Zero | Zero | Scale-down complete | AKS cluster autoscaler |

## Workflow safety review

| Requirement | Pass/fail | Evidence |
| --- | --- | --- |
| `workflow_dispatch` is the only trigger | | |
| Workflow token permissions are empty | | |
| Only shell steps or reviewed commit-pinned actions | | |
| No kubeconfig or cluster credential | | |
| No Docker socket | | |
| No privileged Docker-in-Docker | | |
| Timeout and bounded matrix are present | | |

## Runtime security and operations

| Control | Evidence | Gap or production action |
| --- | --- | --- |
| Non-privileged runner pod | | |
| No host path, host network, or host PID | | |
| Dedicated tainted-node placement | | |
| Service account has no unnecessary cluster access | | |
| App scope is limited | | |
| Image and chart versions are pinned | | |
| Outbound destinations are governed | | |
| Controller logs and Kubernetes events are available | | |
| Secret values are absent from logs and evidence | | |

## Upgrade runbook

| Phase | Precheck | Change | Success signal | Abort condition | Rollback input |
| --- | --- | --- | --- | --- | --- |
| Release-note review | | | | | |
| Canary scale set | | | | | |
| Controller/chart change | | | | | |
| Runner image change | | | | | |
| Safe test job | | | | | |
| Old version removal | | | | | |

## Break/fix

- First failed acceptance criterion:
- Impact:
- First relevant UTC event:
- Competing hypotheses:
- Discriminating evidence:
- Root cause:
- Why adding capacity or removing the taint is not the correct fix:
- Restore action:
- Unchanged workflow rerun result:

## Cleanup

| Item | Expected final state | Evidence |
| --- | --- | --- |
| GitHub jobs | None queued or running | |
| ARC releases | Absent | |
| `arc-systems` | Absent | |
| `arc-runners` | Absent | |
| ARC authentication Secret | Absent with namespace | |
| Runner node pool | Absent | |
| GitHub App course installation/key | Removed or revoked | |
| Local private key | Absent | |
| Git status | No credential or private identifier | |
