# End-to-end attendee rehearsal

Use this after the automated harness passes local/no-write phases.

## Participants

- **Attendee tester:** Azure fundamentals, basic CLI/networking/container knowledge, no Kubernetes.
- **Instructor:** provides only the help allowed by the hint ladder.
- **Observer/timekeeper:** stays silent and records evidence.

Use a fresh clone, browser profile, Dev Container, Azure lab account, and no helpful shell history.

## Before rehearsal

- [ ] Public course repository URL and release commit/tag recorded.
- [ ] Dedicated lab subscription selected.
- [ ] Instructor Entra personas prepared or simulation explicitly declared.
- [ ] Budget and delivery hard-stop set.
- [ ] `./scripts/test-e2e.ps1` default mode passed.
- [ ] Live automated critical phases passed or are documented BLOCKED.

## Daily rehearsal

For each challenge, the observer completes [the observation sheet](e2e-observation-sheet.md).

### Prework and Day 1

- Attendee finds setup from the root README.
- `.env`, subscription, region/SKU, and preflight sequence are clear.
- Compose and `kind` work by copying commands exactly.
- Attendee recognizes the starter is intentionally incomplete.
- Full promotion and separate failure restores work without undocumented cleanup.
- Attendee uses the term and kubectl cheat sheets before searching elsewhere.

### Day 2

- Day-0 worksheet is understandable without a solution.
- Provisioning wait has a useful parallel task and hard-stop.
- Attendee can trace Gateway -> Service -> EndpointSlice -> pod.
- Persistence and single-writer limitation are understood.
- Gate runs before shutdown; next-day state is clear.

### Day 3

- Missing Git/Entra prerequisites are detected before work starts.
- Real authentication and `--as` authorization simulation are not confused.
- Workload Identity flow can be explained without exposing the secret.
- Allowed and denied network paths match the worksheet.
- Flux drift/prune ownership is clear.

### Day 4

- Metrics query returns data or produces a bounded ingestion-delay message.
- HPA, VPA, KEDA, and cluster autoscaler ownership is distinguished.
- Scale pressure is admitted and removed.
- Drain has spare capacity and produces a measurable result.
- Spot and restore exercises clean themselves up.
- The day fits the schedule without rushing incident recovery.

### Day 5

- Attendee preserves evidence before remediation.
- Hypotheses and discriminating tests are distinct.
- Recovery, root cause, and prevention are distinct.
- The runbook and ADR templates are sufficient.
- Two instructors independently score within five points.

## Viability thresholds

- No critical setup or safety step depends on instructor tribal knowledge.
- Day 0/1 complete without opening solutions.
- Day 2 needs no more than two bounded coach hints.
- Day 3/4 external prerequisites are visible before the challenge.
- Infrastructure waits have a stated parallel task, timeout, and fallback.
- Every destructive action identifies scope/context and cleanup.
- Every gate runs before stop/delete.
- Each day fits the published rhythm, including cleanup and debrief.
- At least 75 percent of scheduled instructional time is hands-on.
- Attendee explains the outcome in their own words.
- Capstone scoring is repeatable.

## Decision

- **READY:** all critical thresholds pass.
- **READY WITH FACILITATOR NOTES:** no critical blocker; only bounded timing/region variance.
- **NOT READY:** any safety, hidden prerequisite, live platform, cleanup, or scoring blocker remains.

Record the decision in [the E2E report template](e2e-test-report-template.md) and `release-readiness.md`.
