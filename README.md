# Owlet Dashboard

Local FastAPI + SQLite history collector and dashboard for Owlet Dream Sock / Smart Sock data.

Owlet Dashboard stores local historical vitals from the unofficial Owlet cloud API and shows oxygen, heart-rate, movement, and sleep/wake trends in a private web dashboard. It is designed for parents who want retrospective history beyond the short recent window shown in the Owlet app.

The Owlet app only exposes a short recent window. This server polls Owlet's unofficial cloud API via [`pyowletapi`](https://pypi.org/project/pyowletapi/), stores readings locally, and serves a simple historical dashboard.

> Safety note: this is for retrospective trend viewing only. Do **not** use it as a medical alerting system or as a replacement for the Owlet app/base station.

## What it stores

Each poll stores:

- timestamp
- device serial
- heart rate
- oxygen saturation / SpO₂
- movement
- sleep state, when available
- battery
- skin temperature, when available
- raw normalized payload for future fields

## Setup

```bash
cd /Users/paul/Projects/Personal/owlet-history-server
/Users/paul/.hermes/hermes-agent/venv/bin/python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env` and set your Owlet email/password.

Region options seen in community libraries:

- `world` — typical US/global account
- `europe` — EU account

## Run

```bash
cd /Users/paul/Projects/Personal/owlet-history-server
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8788
```

Open:

- Dashboard: <http://127.0.0.1:8788/>
- Health: <http://127.0.0.1:8788/api/health>
- All readings JSON: <http://127.0.0.1:8788/api/readings>
- Recent readings JSON: <http://127.0.0.1:8788/api/readings?hours=24>
- Summary JSON: <http://127.0.0.1:8788/api/summary>

Dashboard features:

- installable PWA shell with manifest, icons, service worker, and an in-app install button
- live auto-refresh every 15 seconds with visible countdown
- primary full-width vitals trace with synchronized drag/pan/zoom
- O₂ trend signal chart with 30m trailing average, 4h baseline, and green/red short-minus-long direction bars
- red offline/sock-off bands when Owlet reports zero-valued vitals
- offline/zero readings are kept visible in the raw trace/table but excluded from averages, trends, and sleep analysis
- Owlet alert/notification capture for low oxygen, sock disconnect/off, heart-rate, battery, and base-power alerts, with a pageable dashboard dropdown and warning markers on the main vitals trace
- BTC/ETH/XMR price glance powered by CoinGecko, plus an optional hidden-by-default BTC price overlay on the main vitals chart
- "today at a glance" latest vitals card
- breathing trend card comparing recent vs prior oxygen averages
- low-oxygen sample count for the selected window
- sleep/awake estimate using Owlet sleep-state codes (`1=awake`, `8=light sleep`, `15=deep sleep`)
- 5m/15m/30m/1h/6h/12h/daily drill-down averages for oxygen, HR, sleep, and awake time
- compact mobile layout with chart legends inside the chart area
- click a row to inspect that normalized reading
- CSV download for the current filtered view

Analytics endpoints:

- Insights: <http://127.0.0.1:8788/api/insights?hours=24>
- Hourly rollups: <http://127.0.0.1:8788/api/rollups?bucket=hour&hours=24>
- Daily rollups: <http://127.0.0.1:8788/api/rollups?bucket=day&hours=168>
- Notifications: <http://127.0.0.1:8788/api/notifications?hours=24>
- Crypto prices: <http://127.0.0.1:8788/api/crypto?hours=24>
- Compact widget JSON: <http://127.0.0.1:8788/api/widget?hours=24>

## Internet access

Best recommendation: **Cloudflare Tunnel + Cloudflare Access**. Cloudflare Access should be configured before starting a public named tunnel so unauthenticated visitors never reach the local FastAPI app.

Why this path:

- no router port forwarding
- no inbound firewall hole to your Mac
- HTTPS termination through Cloudflare
- Cloudflare Access can require your email / OTP / Google login before anyone reaches the app

Temporary test tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8788
```

Permanent local deployment notes live in [`docs/deployment.md`](docs/deployment.md).

## Run tests

```bash
cd /Users/paul/Projects/Personal/owlet-history-server
.venv/bin/python -m pytest -q
```

## Notes on Owlet API fragility

Owlet has no documented public API for this. This project intentionally isolates the unofficial dependency in `app/owlet_client.py`, so if Owlet changes auth/endpoints, the storage/API/dashboard should remain intact and only the adapter should need updates.

Libraries I checked while scaffolding:

- `pyowletapi` — current PyPI package, used here.
- `jlamendo/ha-sensor.owlet` — Home Assistant integration using the modern API.
- `hmostafa17/owlet-dream-logger` — real-time logger/dashboard with more aggressive reconnect logic.
- `edfincham/owlet-sock-scraper` — Go + Postgres + Grafana approach.

## Next improvements

- Add daily sleep rollups in a `sessions` table.
- Add CSV export endpoint.
- Add Grafana/Prometheus option if you want more powerful charts.
