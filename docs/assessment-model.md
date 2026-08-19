# Assessment model

## Evidence, not screenshots

Daily validators write machine-readable results to `evidence/`. Learners may add a short decision record, incident timeline, or command transcript. Screenshots do not prove reproducibility.

## Scoring

| Area | Weight |
| --- | ---: |
| Reproducible platform and delivery | 20 |
| Identity, secrets, policy, and network security | 20 |
| Reliability and safe change | 15 |
| Observability and troubleshooting method | 20 |
| Scaling and cost discipline | 10 |
| Architecture trade-off defense | 15 |

The capstone pass mark is 80/100 with no critical security failure. Critical failures include committed credentials, public unauthenticated control-plane access introduced without justification, disabled Key Vault purge protection, or workload use of static Azure credentials.

See the [daily gate evidence matrix](gate-matrix.md) for the boundary between automated checks and instructor-reviewed artifacts.
