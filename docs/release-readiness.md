# Instructor release-readiness checklist

Complete for each delivery region and subscription type.

## Course source

- [x] Public GitHub URL and default branch: `https://github.com/naytron/aks-labs`, `main`.
- [ ] Release commit/tag:
- [ ] Solutions separated from learner starting points.
- [ ] CI passed on the release commit.
- [ ] All Microsoft/GitHub reference links checked.

## Local pilot

- [x] Dev Container built on the supported host architecture.
- [x] Pinned tool versions verified.
- [x] Docker Compose transaction and persistence passed.
- [x] `kind` starter and full stages passed.
- [x] Separate image/readiness restore paths passed.
- [x] Cloud Shell limitations documented.
- [ ] Measured prework duration: not representative during iterative QA.
- [ ] Measured Day 1 local duration: not representative during iterative QA.

## Executable E2E harness

- [x] `test-e2e.ps1 -LocalOnly` decision READY.
- [x] Full Dev Container child run and cleanup passed.
- [x] Static/content, Compose, kind promotion, persistence, and three local incidents passed.
- [x] Default missing-`.env` run reported BLOCKED with remediation.
- [x] Azure no-write run decision READY.
- [x] No-write run created zero Azure resources.
- [x] E2E result artifacts are GUID/token/secret-redacted.
- [x] Copied incident bundles are recursively redacted.
- [x] Manual no-Azure `workflow_dispatch` added.
- [ ] Manual attendee/instructor/observer rehearsal completed.
- [ ] Live E2E decision READY.

## Azure readiness

- [x] Subscription name: `dev-mcaps-nlangston` (QA only)
- [x] Region: Central US selected after discovery.
- [x] Availability Zones/features checked.
- [x] Selected four-vCPU-or-larger D-series SKU unrestricted: `Standard_D4ds_v7`.
- [x] Required family and regional vCPU headroom >= 12 (100 available during QA).
- [x] Policy/feature effects reviewed; custom Public IP was blocked by subscription feature registration.
- [ ] Test personas/groups verified.
- [x] Budget/hard-stop owner assigned.

## AKS Automatic pilot

- [x] `what-if` passed.
- [ ] Deployment passed (blocked: control plane remained Creating).
- [ ] ACR builds passed.
- [ ] Gateway external transaction passed.
- [ ] Managed defaults captured.
- [ ] Faults restored separately.
- [x] Resource group deletion verified in West US 3 and Central US.
- [x] Duration and observed/projected cost: canceled at 78 and 20 minutes; no Cost Management row posted immediately.

## AKS Standard Days 2-5 pilot

- [ ] Day 2 Gateway/network/persistence/scheduling gate passed.
- [ ] Stop/start transition passed.
- [ ] Day 3 Workload Identity/Key Vault/policy/persona gate passed.
- [ ] Managed Flux sync/drift/invalid-change/prune passed.
- [ ] Day 4 Prometheus/HPA/VPA/KEDA/CAS/Spot/drain/restore gate passed.
- [ ] Day 5 three incidents and capstone scoring passed.
- [x] Final resource group deletion and zero tagged inventory verified.
- [x] Duration and observed/projected cost: Standard canceled after 30-minute no-node stall; no Cost Management row posted immediately.

## Cost reconciliation

- [x] Immediate resource inventory zero.
- [ ] Cost records rechecked after settlement.
- [ ] Total measured Azure cost:
- [ ] Published learner estimate and assumptions updated.

## Known constraints and exceptions

Record region limitations, policy differences, delayed features, timing variance, and any optional lab disabled for this delivery.
