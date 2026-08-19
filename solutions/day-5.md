# Day 5 assessor reference

There is no single capstone topology. Accept a design that meets the scenario with explicit trade-offs and reproducible evidence.

## Strong production recommendation

AKS Automatic is a strong default if Northwind does not require unsupported network, node-pool, authorization, or upgrade customization. A Standard recommendation is valid when the learner identifies a concrete requirement and accepts the platform-engineering burden. "More control" alone is insufficient.

## Incident standard

Full credit requires:

- evidence captured before destructive recovery;
- at least two plausible hypotheses;
- a test that distinguishes them;
- a reversible recovery proportional to impact;
- user-path and controller-level recovery proof;
- root cause separate from trigger and recovery;
- preventive action tied to detection or design.

## Architecture red flags

- Static pod credentials or secrets in Git.
- Public exposure of orders-api.
- No separation between system and user workloads.
- Multiple autoscalers controlling one target.
- Multi-replica SQLite called highly available.
- PDB presented as protection from node failure.
- Backup presented as active high availability.
- No cost/telemetry retention boundary.
- CI pushes directly with a long-lived cluster credential.

Score with `docs/capstone-rubric.md`.
