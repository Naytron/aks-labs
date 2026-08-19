# Daily coach notes

## Prework

Common blockers: Docker daemon unavailable, wrong `kubectl` context, provider not registered, D-series restriction, expired lab date. Do not bypass quota or use B-series as a shortcut.

## Day 1

- Recreate with `-Starter`; do not let prework's full overlay remove the reconstruction exercise.
- `imagepull`: expect events, no app logs.
- `readiness`: process alive, endpoint not ready.
- Restore and validate each fault before injecting the next.
- Delete Automatic on schedule; this is a cost gate.
- If Automatic exceeds the published provisioning hard-stop, cancel/delete and use the no-write comparison fallback. Never start a duplicate cluster blindly.

## Day 2

- Deploy only `azure-day2`; security and monitoring arrive later.
- `scheduling`: impossible node selector. Learner should inspect scheduler events.
- Selector fault: patch storefront or API Service selector manually after the scripted scenario. Restore from rendered baseline.
- Ask why Standard is needed; reject "because advanced."

## Day 3

- Confirm the Entra persona mode (real or simulation) and public Git source before the first challenge.
- Deploy/reconcile `azure-day3`.
- Verify `flux-system/course-values` contains only non-secret substitution values and `orders-workload` is Ready.
- Federated subject fault is manual so the learner cannot infer a scenario name.
- `network`: deletes only the allow policy; default deny remains.
- Check for accidental secret values in terminals/evidence before accepting.

## Day 4

- Retarget Flux to `azure-day4` and verify PodMonitor targets before tuning.
- Day 4 raises the namespace CPU quota so scale-pressure pods are admitted; remove pressure before drain.
- Set bounded CPU work for HPA and delete it afterward.
- Scale the user pool to two before drain and return it to one afterward.
- `oom`: low limit, not a leak. Learner must distinguish symptom from cause.
- `rollout`: wrong readiness path; old capacity may remain.
- Drain can expose the single-writer lab database limitation. Treat this as intended architecture evidence.
- Spot pool must be gone before the gate.

## Day 5

Recommended deterministic combinations:

1. Wrong Service selector plus healthy pods.
2. Readiness failure plus restrictive PDB during drain.
3. Workload Identity subject mismatch plus an unrelated warning event.

Avoid random node termination or uncontrolled Azure changes. Record the exact injection and restore command privately. Allow 45 minutes per incident, then 15 minutes for the report.
