# Level 400 capstone rubric

| Area | Points | Full-credit evidence |
| --- | ---: | --- |
| Reproducible platform | 10 | Bicep builds, `what-if` reviewed, parameters documented, no portal-only drift |
| Delivery | 10 | Immutable ACR release, Flux healthy, drift repair and rollback proven |
| Human identity | 5 | Entra/Azure RBAC, local accounts disabled, least-privilege persona tests |
| Workload identity and secrets | 10 | OIDC federation, Key Vault CSI, short-lived credentials, no secret exposure |
| Policy and isolation | 5 | Restricted pods, quota/limits, default deny, explicit flows, admission evidence |
| Reliability | 10 | Replicas, topology, PDB, probes, graceful termination, measured disruption |
| Observability and SLO | 10 | Metrics/logs/events tied to SLO and actionable alert/runbook |
| Scaling and performance | 5 | Requests, HPA/KEDA decision, node scale evidence, documented limits |
| Upgrade and recovery | 10 | Staged upgrade, abort/rollback, backup restore, RTO/RPO and DR |
| Cost | 5 | Inventory, budget, telemetry control, teardown, reliability trade-offs |
| Incident method | 15 | Evidence preservation, hypotheses, discriminating tests, safe recovery, RCA |
| Architecture defense | 5 | Clear Automatic/Standard and Day-0 trade-off reasoning |

**Pass:** 80 points and no critical security failure.

Critical security failures:

- Credential, kubeconfig, private key, or secret committed or exposed.
- Static Azure credential used by a pod.
- Key Vault purge protection disabled.
- Local AKS account deliberately enabled without an approved recovery exception.
- Broad public access introduced without identification and mitigation.
