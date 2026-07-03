# Owlet History Server

Local FastAPI + SQLite history collector for Owlet Dream Sock / Smart Sock data.

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
- Readings JSON: <http://127.0.0.1:8788/api/readings?hours=24>
- Summary JSON: <http://127.0.0.1:8788/api/summary?hours=24>

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

- Add auth/password to the local dashboard if exposed beyond localhost.
- Add daily sleep rollups in a `sessions` table.
- Add CSV export endpoint.
- Add launchd service so it starts automatically on the Mac mini/laptop.
- Add Grafana/Prometheus option if you want more powerful charts.
