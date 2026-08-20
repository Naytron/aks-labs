# ARC trust and architecture decision record

Do not record App IDs, installation IDs, private repository names or URLs, key paths, Secret data, subscription IDs, tenant IDs, or cluster credentials.

## Scope

- Decision owner:
- Date in UTC:
- Lab target: private sandbox repository confirmed (yes/no):
- Workload class:
- Data handled by jobs:
- Production recommendation:

## Trust boundary map

| Boundary | Who can change it | Credential or authority | Reachable assets | Control | Evidence |
| --- | --- | --- | --- | --- | --- |
| Workflow source and default branch | | | | | |
| Manual dispatcher | | | | | |
| GitHub App and installation | | | | | |
| ARC controller in `arc-systems` | | | | | |
| Runner scale set in `arc-runners` | | | | | |
| Ephemeral runner pod | | | | | |
| Dedicated runner node pool | | | | | |
| Outbound network and dependencies | | | | | |

## Architecture decisions

| Decision | Lab choice | Production choice | Rejected option | Failure or abuse mode | Reversal cost |
| --- | --- | --- | --- | --- | --- |
| Shared or separate cluster | Existing Standard cluster | Separate runner cluster | | | |
| Repository visibility | Private sandbox | | Public course repository | | |
| Authentication | GitHub App | | Personal access token | | |
| App installation scope | Selected repository only | | All repositories | | |
| Controller namespace | `arc-systems` | | | | |
| Runner namespace | `arc-runners` | | | | |
| Runner lifecycle | One job, ephemeral | | Persistent idle runner | | |
| Idle runners | `minRunners: 0` | | | | |
| Runner concurrency | Bounded `maxRunners` | | Unbounded | | |
| Node capacity | Dedicated, tainted, min-zero pool | | Shared general pool | | |
| Workflow trigger | `workflow_dispatch` only | | Automatic pull request | | |
| Job capability | Shell-only safe test | | Privileged DinD or Docker socket | | |
| Version policy | Pinned chart and image | | `latest` | | |

## Shared lab cluster versus separate production cluster

| Concern | Existing Standard lab cluster | Separate production runner cluster | Required production control |
| --- | --- | --- | --- |
| Kubernetes-admin blast radius | Shared | Isolated | |
| Node and scheduler contention | Shared control plane | Dedicated | |
| Network reachability | Course network | Runner-specific | |
| Identity and secret policy | Shared administration | Runner-specific ownership | |
| Upgrade and maintenance | Coupled to lab | Independent | |
| Availability and regional design | Lab only | Requirement-driven | |
| Cost | Lower setup cost | Additional fixed services | |
| Logs, audit, and incident ownership | Course team | Named runner owner | |

## Threat review

For each threat, state prevention, detection, and recovery.

| Threat | Prevention | Detection | Recovery |
| --- | --- | --- | --- |
| Untrusted workflow change | | | |
| Pull request from a fork | | | |
| Excess workflow token permission | | | |
| App key disclosure | | | |
| Runner reaches cluster credentials | | | |
| Privileged or host-mounted runner | | | |
| Dependency or runner-image compromise | | | |
| Unbounded pod or node growth | | | |
| Egress to an unintended destination | | | |
| Stale runner after a job | | | |

## Decision

- Chosen design:
- Why it meets the lab requirement:
- Why it is not the production default:
- Conditions required before production:
- Largest residual risk:
- Approval and review date:
