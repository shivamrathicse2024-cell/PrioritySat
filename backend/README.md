# PrioritySat API

FastAPI backend for PrioritySat. This rapid build runs in **DEMO DATA** mode only. API reachability does not mean satellite telemetry is live or verified. No physical infrastructure controls are implemented.

## Run on Windows

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for the UI, `/docs` for Swagger, and `/health` for API health.

## Tests

```powershell
$env:PYTHONPATH="."
pytest -q
```

## Endpoints
- `GET /api/v1/system/status`, `/api/v1/overview`, `/api/v1/overview/metrics`
- `GET /api/v1/nodes`, `/api/v1/nodes/{node_id}`, `/api/v1/satellites`, `/api/v1/ground-stations`
- `POST /api/v1/routes/plan` — graph-based route calculation
- `GET /api/v1/simulations/scenarios`, `POST /api/v1/simulations`, `GET /api/v1/simulations/{id}`, pause/resume/reset/cancel and results endpoints
- `GET /api/v1/activity`, `/api/v1/activity/recent`, `GET /api/v1/alerts`, alert acknowledgement
- `WS /api/v1/ws/events`

All generated operational payloads are labeled `data_mode=demo`, `is_demo=true`, and `source=generated` where applicable. Sample fixtures and simulations are in-memory and reset on restart. SQLite/PostgreSQL persistence is not enabled in this rapid build; WebSocket emits demo heartbeats and simulation snapshots.
