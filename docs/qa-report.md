# AKS bootcamp QA report

**QA date:** 2026-08-20
**Attendee baseline:** Azure fundamentals, basic CLI/networking/container knowledge, no Kubernetes

## Outcome

The course structure is technically strong, but the first authoring pass was closer to a challenge outline than a self-directed attendee experience. The QA pass has added explicit starting state, checkpoints, expected evidence, tips, production callouts, staged platform progression, stronger gates, deterministic operations exercises, and supplemental references.

## High-confidence issues fixed

- Dev Container exposed `python3` while every course command used `python`.
- Prework deployed the full workload while Day 1 expected an incomplete starting point.
- Starter-to-full promotion caused server-side ownership and NodePort conflicts.
- VM size/region was hardcoded to a v5 SKU unavailable in the QA subscription.
- Compute provider, effective role-assignment capability, AKS region, vCPU, quota, and ephemeral-disk support were not all preflighted.
- Subscription deployment names could not be reused across regions.
- Automatic explicitly disabled CSI drivers needed by the workload and enabled the retiring NGINX profile before Gateway API.
- Day 2 exposed Day 3 security and Day 4 monitoring controls too early.
- Failure instructions could overlap faults instead of restoring between them.
- Day 2/3 gates were documented after cluster shutdown.
- Flux reconciled raw unresolved ACR/identity placeholders and Day 4 could be pruned back to Day 3.
- Day 4 scale-pressure objects exceeded their own namespace quota.
- Day 4 HPA, cluster-autoscaler, Spot, drain, and backup exercises lacked deterministic harnesses.
- Cleanup failed when repeated after successful deletion.
- Validation gates proved object existence but not enough taught behavior.
- A malformed patch transcript was present in one learner YAML file.

## Supplemental material added

Five concise cheat sheets now cover:

1. must-know Kubernetes/AKS terms and control loops;
2. kubectl and incident triage;
3. AKS Automatic/Standard and Day-0 architecture;
4. Entra/RBAC/Workload Identity/Key Vault/NetworkPolicy;
5. scaling, reliability, upgrades, backup/DR, and cost.

The optional ARC extension adds a sixth operations sheet for GitHub job assignment, ARC runner scaling, Kubernetes scheduling, AKS node scaling, security evidence, and safe cleanup.

## Local evidence

- Full Dev Container with Azure CLI, PowerShell, Docker-in-Docker, kubectl, Helm, kind, Flux, kubelogin, Kustomize, and kubeconform: passed.
- Dev Container post-create local preflight: passed after adding the Python alias.
- Application unit tests: passed.
- Docker Compose build, health, create/list transaction, and teardown: passed.
- Two-node `kind` cluster: passed.
- Incomplete Day 1 starter state: passed.
- Starter-to-full workload promotion: passed after deterministic starter cleanup.
- Full workload gate, probes, resources, restricted security, endpoints, and external health: passed.
- Separate image-pull and readiness evidence/restore paths: passed.
- Bicep builds, staged Kustomize renders, Kubernetes schema checks, local links, selected first-party external links, PowerShell parsing, and secret patterns: passed.

## Executable E2E harness

- `./scripts/test-e2e.ps1 -LocalOnly`: **READY**.
  - Full Dev Container plus post-create preflight: passed.
  - Final clean run: static/content 126 seconds; Compose 25 seconds; kind 205 seconds.
  - Host-orchestrated Dev Container plus child local E2E: 382 seconds.
  - Repeated cached runs varied materially, so instructor timing must come from the manual rehearsal rather than CI/runtime timings.
- Default no-write behavior without `.env`: **BLOCKED** with a specific remediation, as designed.
- Default no-write with temporary valid `.env`: **READY**.
  - Owner/capacity/provider/SKU checks, Automatic and Standard validate/what-if, and before/after zero-resource checks: passed in approximately 437 seconds on the final run.
- Generated E2E artifacts contain PASS/FAIL/BLOCKED/SKIPPED states, durations, evidence paths, and remediation.
- Persisted E2E artifacts, including copied incident bundles, were recursively redacted and scanned; no GUID identifiers, access tokens, or client secrets remained.
- Repeat cleanup left no Dev Container, Compose stack, kind cluster, `.env`, `.aks-labs`, `evidence`, or tagged Azure resource.
- Live mode is implemented but remains release-blocked by the AKS subscription and prepared Entra persona prerequisites below.
- Manual attendee rehearsal artifacts are ready but require a real target attendee/instructor/observer session.
- The reviewed live-mode gate refuses paid deployment when no-write checks are blocked; this was verified with zero tagged Azure resources.
- Final post-ARC `-LocalOnly -SkipDevContainerBuild` run: **READY**; repository/static/content 29+88 seconds, Compose 21 seconds, and kind learner path/incidents 122 seconds.
- ARC remains `SKIPPED` in the default/local path. An explicit `-ArcExtension` request without live mode returned structured **BLOCKED** at phase `05A` before any external mutation.

### Optional ARC extension evidence

- ARC controller and runner scale-set charts are pinned to stable `0.14.2`; OCI digests are recorded and verified during static validation.
- GitHub's documented Helm 3 prerequisite is satisfied by pinned Helm 3.21.4 alongside the course's Helm 4 tool.
- The controller and Actions runner images use immutable manifest digests.
- Both charts render with the course values and pass kubeconform; no credential is required for static validation.
- The private workflow template is manual-only, shell-only, bounded, unprivileged, and is not active under the public repository's `.github/workflows`.
- The guarded deployment rejects public `naytron/aks-labs`, requires GitHub CLI to prove `PRIVATE` visibility, and creates the App Secret from a key file rather than Helm plaintext.
- The separate runner-pool Bicep and all ARC PowerShell scripts parse/build in the Dev Container.
- Live ARC remains blocked until a working Standard AKS deployment, private disposable repository, GitHub App, and human permission/revocation rehearsal are available.

## Live Azure evidence

### Subscription and capacity

- Dedicated dev subscription provider registration and effective role-assignment capability: passed.
- Central US with `Standard_D4ds_v7`, three zones, ephemeral OS support, and 100-vCPU family/regional headroom: passed.
- Retail Linux VM rate used for the hard-stop estimate: USD 0.313/node-hour as of the QA date.
- Immediate Cost Management query for the deleted QA resource groups returned no posted rows; delayed reconciliation is still required.

### AKS Automatic

- West US 3 preview: passed.
- West US 3 creation remained in `Creating` for 78 minutes with no node resources or surfaced failure.
- The operation was canceled; parent and managed node resource groups were verified absent.
- Central US retry with a different current-generation SKU showed the same `Creating` behavior after 20 minutes.
- The retry was canceled; parent and managed node resource groups were verified absent.
- Repeat cleanup reported the already-absent group as success.
- The instructor no-write comparison fallback is now explicit in Day 1.

### AKS Standard

- Initial Central US preview passed.
- Initial creation failed before AKS compute because the newest Public IP API unexpectedly required the `AllowBringYourOwnPublicIpAddress` feature.
- The broadly supported stable Public IP API showed the same subscription feature gate, confirming this was not an API-version defect.
- The lab now uses one AKS-managed Standard Load Balancer outbound IP; stricter custom/static egress remains a production design option.
- The partial deployment contained only VNet, monitoring workspaces, and control-plane identity.
- The managed-egress retry passed preview but the AKS resource remained in `Creating` for 30 minutes with zero managed node resources and no surfaced provider error.
- The deployment was canceled; parent and managed node resource groups were verified absent.
- Repeat final cleanup reported the already-absent group as success.
- Live Days 2-5 remain blocked on a subscription where AKS control-plane creation completes.

## Remaining live prerequisites

- Public GitHub source is now available at `https://github.com/naytron/aks-labs` on `main`; live Flux still requires a working AKS cluster.
- Instructor-prepared Entra test groups/accounts are required for real human authentication tests. Impersonation is only an authorization simulation.
- A working dedicated AKS subscription is required; this QA subscription stalled Automatic in two regions and Standard in Central US before node creation.
- Cost Management records settle later; final measured spend must be reconciled after teardown.

## Release recommendation

The automated local/no-write course path is repeatable and ready. Do not publish the bootcamp as fully delivery-ready until the live Automatic/Standard sequence, managed Flux, persona tests, Day 4 operations, manual attendee rehearsal, capstone scoring, and delayed cost reconciliation are completed in `release-readiness.md`.
