# Course workload

The workload has two dependency-free Python services:

- `storefront`: serves the learner UI and proxies `/api/*` to the internal API.
- `orders-api`: persists orders to SQLite, exposes probes and Prometheus metrics, and reports whether a CSI secret is mounted without exposing its value.

It is intentionally small. The platform, not application development, is the subject.

## Local run

```powershell
docker compose -f app/compose.yaml up --build --detach
Invoke-RestMethod http://localhost:8080/healthz
Invoke-RestMethod http://localhost:8080/api/orders -Method Post -ContentType application/json -Body '{"item":"book","quantity":1}'
docker compose -f app/compose.yaml down --volumes
```

Both images run as UID/GID 10001, write only to explicit volumes or `/tmp`, drop Linux capabilities at runtime, and expose structured logs, liveness, readiness, and Prometheus endpoints.

## Controlled behavior

`orders-api` accepts:

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_MESSAGE` | Visible non-secret configuration | `orders-api` |
| `DATA_DIR` | Persistent data directory | `/data` |
| `SECRET_PATH` | CSI-mounted secret path | `/mnt/secrets-store/course-api-key` |
| `FAIL_READINESS` | Safe readiness failure injection | `false` |
| `STARTUP_DELAY_SECONDS` | Startup-probe exercise | `0` |

`storefront` accepts `CPU_BURN_MS` (0-250, default 0) to add bounded CPU work to proxied API requests. Day 4 sets it temporarily so HPA behavior is deterministic; it must be reset after the scaling exercise.
