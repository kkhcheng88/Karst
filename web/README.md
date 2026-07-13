# Karst dashboard (thin, read-only)

A monitoring surface for the daily top-down scan — see today's **Phase 0→4** read and
per-ticker scores from anywhere, without sitting at the machine. It renders, it does not
trade (NHITL). Compute and serve are **separated**: a slow/failing scan never blocks the page.

```
run_scan.py   COMPUTE  cron → writes web/data/latest.json (+ dated snapshots)
app.py        SERVE    Flask, read-only → renders latest.json
render.py     pure JSON → HTML (Phase 0 gate · sectors · tier-1 options · tier-2 long)
```

## Run locally

```bash
python web/run_scan.py                 # produce web/data/latest.json (uses yfinance-first locally)
python web/app.py                      # serve at http://localhost:8000
```

## Deploy to Zeabur (or any Docker VPS)

The repo root has a `Dockerfile`. The image bakes the safe headless defaults:

| env | default in image | meaning |
|---|---|---|
| `KARST_DATA_SOURCE` | `defeatbeta` | try defeatbeta FIRST (Yahoo throttles datacenter IPs); yfinance stays the fallback |
| `KARST_INPROC_CRON` | `1` | this one process also runs the daily scan (single-service deploy) |
| `KARST_REFRESH_HOUR` | `9` | server-local hour to refresh |
| `KARST_TOKEN` | *(unset)* | **set this** — required on every route except `/healthz` |
| `PORT` | `8000` | listen port |

1. Push the repo to a Git remote; create a Zeabur service from it (Dockerfile auto-detected).
2. **Set `KARST_TOKEN`** to a long random string (the dashboard is otherwise open).
3. Add a **persistent volume** mounted at `/app/web/data` so scans + history survive restarts.
4. Open `https://<your-app>/?token=YOUR_TOKEN` (a cookie is set, so later visits need no token).

Cold start: with `KARST_INPROC_CRON=1` and no `latest.json`, the app runs one scan on boot,
then daily at `KARST_REFRESH_HOUR`. First scan takes a few minutes (defeatbeta warm-up).

### Prefer a separate cron service?
Set `KARST_INPROC_CRON=0` on the web service and add a Zeabur **Cron Job** running
`python web/run_scan.py` (same volume). Keeps serve and compute in different containers.

## Routes
- `GET /` — dashboard (auth)
- `GET /api/scan` — raw scan JSON (auth)
- `GET /healthz` — liveness + freshness (no auth): `{ok, generated_at, asof}`

## Sizing / caveats
- ~1–2 GB RAM (pandas + sklearn). The 200 MB backtest price caches are **not** shipped
  (`.dockerignore`); the live scan pulls prices over the network.
- defeatbeta lags ~1 trading day — fine for a daily-check dashboard. For same-day closes
  run compute where yfinance works (leave `KARST_DATA_SOURCE` unset) and ship only the JSON.
- The insider overlay reads `thesis/insider_cache.json` (rebuild weekly via the existing
  `thesis/weekly_insider.cmd` equivalent / a second cron running `thesis/insider_edgar.py build`).
