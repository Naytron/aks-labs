# Instructor setup - optional ARC runner module

Complete this setup only for the optional post-capstone module. The existing Standard AKS lab cluster is an intentional training shortcut. A separate runner cluster is the production recommendation.

## 1. Prepare a private sandbox repository

Create or select a disposable GitHub repository that:

- is **Private**;
- contains no production code, deployment environment, organization secret, or real cloud credential;
- permits the assigned learner to push one workflow and use manual dispatch;
- has branch protection or rules appropriate to the exercise;
- is not `naytron/aks-labs`, a public fork, or any public repository.

Verify visibility in the GitHub UI immediately before setup. If GitHub CLI is available, use a read-only check and do not capture the repository identity in learner evidence:

```powershell
gh repo view "<owner>/<private-sandbox-repository>" --json visibility
```

Expected visibility is `PRIVATE`. Stop if the response differs or access is ambiguous.

## 2. Create a narrowly scoped GitHub App

Use a disposable or course-managed GitHub App dedicated to this exercise.

For a repository-scoped ARC configuration:

- make the App private;
- grant Repository **Administration: Read and write**;
- retain mandatory **Metadata: Read-only**;
- grant Organization **Self-hosted runners: Read and write**, as required by the current ARC GitHub App guidance;
- add no account permissions;
- add no webhook unless a separately documented course requirement needs one;
- install the App on **Only select repositories** and select only the private sandbox repository.

Do not grant Contents, Actions, Packages, Deployments, Environments, Secrets, Workflows, or additional organization permissions merely for convenience. Recheck current GitHub ARC documentation before delivery; if the supported minimum changes, document the exact reason for any added permission.

The learner's human repository permission is separate from the App. Grant only the access needed to push the template and manually dispatch it. Do not use a personal access token for ARC authentication.

## 3. Handle the private key safely

Generate one course key from the App immediately before use.

1. From the Dev Container, place the downloaded `.pem` file in the ignored course state directory:

```text
./.aks-labs/arc-github-app.pem
```

An instructor-managed external path may be used instead only when it is explicitly mounted into the Dev Container.

2. Restrict the directory and file to the instructor account using the operating system's normal ACL tooling.
3. Never place the key in a tracked or unignored repository path. The repository ignores `.aks-labs/`, `*.pem`, `*.key`, and `secrets/`, but ignore rules are defense in depth, not authorization.
4. Never paste key contents into PowerShell, chat, a ticket, a worksheet, Helm values, a YAML file, a screenshot, or a recording.
5. Never pass private-key text through Helm `--set`, `--set-string`, or a process argument. Command lines, shell history, process listings, diagnostics, and CI logs can preserve plaintext.
6. Pass only the absolute key **file path** to `deploy-arc.ps1`. The script owns Secret creation and must suppress sensitive output.
7. After successful installation and validation, delete the downloaded file:

```powershell
Remove-Item -LiteralPath "./.aks-labs/arc-github-app.pem" -Force
Test-Path -LiteralPath "./.aks-labs/arc-github-app.pem"
```

Expected `Test-Path` result is `False`. Empty the recycle or recovery location if local policy uses one. File deletion may not be cryptographic erasure on every storage system, so revoke the GitHub App key during final cleanup.

If the key is printed, committed, captured, or copied to an uncontrolled location, stop. Revoke it in GitHub, remove exposed copies according to organizational incident policy, create a new key, and only then resume.

## 4. Preflight the Standard cluster and runner pool

Confirm the course's Standard cluster is running, current, and owned by the lab:

```powershell
./scripts/start-lab.ps1 -Environment standard
./scripts/show-lab.ps1 -Environment standard
kubectl config current-context
```

Use the repository script to create the dedicated runner pool:

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Deploy
```

Confirm the script reports:

- a dedicated runner pool on Standard;
- a runner-specific taint and labels;
- autoscaling minimum zero;
- an explicit course-bounded maximum;
- no change to the system pool;
- safe idempotent behavior.

Do not manually remove the taint or raise the maximum to bypass capacity or scheduling problems.

Confirm outbound TCP 443 permits the current GitHub runner domains. At minimum the controller/runner path needs `github.com`, `api.github.com`, `*.actions.githubusercontent.com`, `ghcr.io`, and `pkg-containers.githubusercontent.com`. Additional actions, artifacts, releases, and packages require more entries from GitHub's current [accessible-domain list](https://docs.github.com/actions/reference/runners/self-hosted-runners#accessible-domains-by-function). Do not improvise a static IP allow list for CNAME-backed services.

## 5. Install and validate ARC

Use placeholders locally. Do not put real values in course files, recordings, or evidence:

```powershell
./scripts/deploy-arc.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>" `
  -GitHubAppId "<github-app-id>" `
  -GitHubAppInstallationId "<github-app-installation-id>" `
  -GitHubAppPrivateKeyPath "./.aks-labs/arc-github-app.pem"

./scripts/validate-arc.ps1 -Check Install
./scripts/validate-arc.ps1 -Check Security
```

The script abstraction uses the GitHub-documented Helm 3 prerequisite and pins both ARC charts to `0.14.2`; Helm 4 remains installed for the core course but is not used for ARC. It creates `arc-systems` and `arc-runners`, sets `minRunners` to zero and a bounded maximum, configures dedicated runner placement, and creates the authentication Secret without exposing values.

Safe validation:

```powershell
kubectl get namespace arc-systems arc-runners
kubectl get pods -n arc-systems
kubectl api-resources | Select-String 'actions.github.com'
helm3 list -n arc-systems
helm3 list -n arc-runners
```

Do not run `kubectl get secret -o yaml`, decode Secret data, print Helm values containing credentials, or archive a cluster dump without redaction.

Delete the local key file after validation as described above. ARC uses the Kubernetes Secret; it does not need the downloaded file to remain on disk.

## 6. Prepare the safe workflow

Copy `labs/06-arc-runners/templates/arc-scale-test.yml` only into:

```text
<private-sandbox-repository>\.github\workflows\arc-scale-test.yml
```

Confirm `runs-on: arc-aks-lab` matches the course scale set name. Change it only if the instructor deliberately selected a different name. Review before push:

- only `workflow_dispatch`;
- `permissions: {}`;
- shell steps only;
- four-job bounded matrix and timeout;
- no checkout, unpinned action, cluster credential, Docker socket, host mount, service container, or privileged DinD.

Do not add `pull_request`, `pull_request_target`, `push`, `schedule`, or a reusable-workflow trigger for the class default.

## 7. Rehearse validation and the deterministic failure

Run one successful manual workflow and retain sanitized conditions and timestamps:

```powershell
./scripts/test-arc-scale.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>" `
  -WorkflowFile "arc-scale-test.yml"
```

Then rehearse:

```powershell
./scripts/inject-arc-failure.ps1 -Scenario Scheduling
./scripts/inject-arc-failure.ps1 -Scenario Scheduling -Restore
./scripts/validate-arc.ps1 -Check Install
```

The fault must affect only runner placement and produce a deterministic `Pending` runner pod with a useful `FailedScheduling` event. It must not alter repository visibility, App permissions, credentials, system capacity, or the node-pool maximum.

Cloud and GitHub control-loop timing varies. Validate forward progress from conditions and events; do not publish duration guarantees.

## 8. Cleanup and revocation

After the module:

1. Cancel or finish all jobs targeting the scale set.
2. Preserve only sanitized course evidence.
3. Remove ARC and verify:

```powershell
./scripts/cleanup-arc.ps1 `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
helm3 list --all-namespaces | Select-String 'arc-systems|arc-runners'
kubectl get namespace arc-systems arc-runners --ignore-not-found
```

4. Prove node-pool cleanup is idempotent and validate the final state:

```powershell
./scripts/manage-arc-runner-pool.ps1 -Action Delete
./scripts/validate-arc.ps1 `
  -Check Cleanup `
  -RepositoryUrl "https://github.com/<owner>/<private-sandbox-repository>"
```

5. Remove the App installation from the private sandbox repository.
6. Revoke every key created for the course.
7. Delete any remaining local key file and instructor-only staging copy.
8. Delete the sandbox workflow or repository according to retention policy.
9. Confirm `arc-systems`, `arc-runners`, ARC releases, authentication Secrets, and runner nodes are absent.
10. Inspect `git status --short` and learner evidence for credentials and private identifiers.
11. Stop Standard if no later exercise requires it.

## Production comparison

| Concern | Shared Standard lab cluster | Recommended separate runner cluster |
| --- | --- | --- |
| Purpose | Short-lived training | Dedicated CI execution boundary |
| Kubernetes blast radius | Shared with course workloads | Isolated from application clusters |
| Node capacity | One dedicated lab pool | Capacity and quotas owned by runner team |
| Network | Shares lab network controls | Runner-specific egress and private access |
| Identity and policy | Shared cluster administration | Dedicated least-privilege administration |
| Upgrades | Coupled to lab lifecycle | Independent canary and maintenance plan |
| Availability | Training objective | Defined from CI SLO and business impact |
| Cost | Lower fixed setup cost | Higher fixed cost for stronger isolation |
| Incident response | Course owner | Named service owner with audit retention |

A production exception to the separate-cluster recommendation requires a documented threat model, equivalent policy and network isolation, independent capacity protection, named ownership, upgrade coordination, recovery testing, and approval by the application and runner platform owners.
