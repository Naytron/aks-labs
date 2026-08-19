# IP planning worksheet

| Address space | Course value | Required capacity | Overlaps checked against | Rationale |
| --- | --- | ---: | --- | --- |
| VNet | `10.40.0.0/16` | | | |
| Node subnet | `10.40.0.0/22` | | | |
| API server subnet | `10.40.4.0/28` | | | |
| Service CIDR | `10.0.0.0/16` | | | |
| DNS service IP | `10.0.0.10` | 1 | | |
| Pod overlay CIDR | `10.244.0.0/16` | | | |
| Known peer/on-prem | learner supplied | | | |

Answer:

1. Which ranges consume VNet addresses?
2. How many usable Azure subnet addresses remain after Azure reservations?
3. What limits total pod count first: overlay addresses, `maxPods`, node count, or quota?
4. Which overlap would force cluster recreation?
5. What changes if pods must be directly reachable from on-premises?
