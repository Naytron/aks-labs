# Instructor guide

## Before delivery

- Complete the [release-readiness checklist](release-readiness.md).
- Prepare [identity and Git prerequisites](instructor-identity-setup.md).
- If delivering the optional ARC module, complete [the private sandbox and GitHub App setup](instructor-arc-setup.md).
- Pilot in the exact region and subscription type learners will use.
- Confirm D-series quota and AKS feature availability.
- Run all static tests and a clean Azure deployment/cleanup.
- Record the measured cost and publish a region-specific estimate.
- Prepare one recovery subscription for quota or policy exceptions.
- Never distribute a shared kubeconfig or service-principal secret.

## Facilitation

- Give the scenario and acceptance criteria before commands.
- Timebox unproductive debugging, then reveal one hint at a time.
- Ask for evidence before accepting a restart as a fix.
- Compare learner designs; do not imply one universal production topology.
- Use the failure injector only against clusters labeled `aks-course=level400`.
- Keep the six [cheat sheets](cheatsheets/README.md) available as hint-level references.
- On Days 1-4, require the learner to state current context and checkpoint before revealing the next hint.
- Use the [Level 100-400 question bank](https://naytron.github.io/aks-labs/interview-questions/) for mock interviews. Probe reasoning and production evidence rather than accepting memorized definitions.

## Gate policy

Learners must pass the prior day's gate before advancing. Pair remediation is allowed on Days 1-4. Day 5 incident diagnosis and trade-off defense are individual.

Use the [daily gate matrix](gate-matrix.md) so automated and manual evidence are not conflated.

## Safety stops

Stop the lab if a learner targets an untagged resource group, cannot identify the active subscription, stores a credential in a manifest, or exceeds the agreed budget threshold.

For ARC, also stop on a public or ambiguous repository, broad GitHub App installation, unexpected queued workflow, exposed key material, or any attempt to add cluster credentials, privileged DinD, a Docker socket, or `cluster-admin`.
