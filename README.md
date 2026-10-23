# PrioritySat — Orbital Operations Center

PrioritySat is a demo-mode satellite-network exploration and simulation prototype. It brings network overview, node inspection, graph-based route planning, scenario simulations, alerts, and activity history into one interface.

> **Data integrity:** This project uses generated **DEMO DATA** for satellite positions, telemetry, metrics, route estimates, alerts, activity, and simulation results. It does not connect to live satellite telemetry and does not control physical satellites or ground stations.

## Quick start (Windows)

1. Install Python 3.11 or newer.
2. Extract this repository or clone it with Git.
3. Open the project root folder.
4. Double-click `start_windows.bat`.
5. Open <http://127.0.0.1:8000>.
6. API docs: <http://127.0.0.1:8000/docs> · Health: <http://127.0.0.1:8000/health>.

The first run may need internet access to install Python dependencies. The current UI also references some external CDN assets, so some styling may require internet access.

## Manual setup

From the project root in PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

## Main modules

- **Mission Overview:** demo network metrics, alerts, and recent activity.
- **Network Explorer:** node search, selection, telemetry, and connection details.
- **Route Planner:** graph-based route calculation and alternative candidates.
- **Simulation Lab:** simulated failures, congestion, progress, and results.
- **Activity Log:** searchable/filterable events and alert acknowledgement.

## Architecture

```text
Frontend (HTML/CSS/JavaScript)
        |
        v
Central API client (frontend/api.js)
        |
        v
FastAPI REST API (/api/v1) + WebSocket events
        |
        v
Demo node graph, route service, simulation state, alerts/activity
```

## Tests

```powershell
cd backend
python -m pytest -q
```

## Configuration

See `backend/.env.example` for supported example settings. Do not commit real secrets or a local `.env` file.

## API overview

- `GET /health`
- `GET /api/v1/system/status`
- `GET /api/v1/overview` and `/api/v1/overview/metrics`
- `GET /api/v1/nodes` and node details
- `POST /api/v1/routes/plan`
- Simulation scenario, run, control, and result endpoints
- Activity and alert endpoints
- `WS /api/v1/ws/events`

Interactive API documentation is available at `/docs` while the backend is running.

## Current limitations

This is a runnable prototype, not a hardened production deployment. Demo state such as simulations, route plans, activity, and alert acknowledgements is held in process memory and resets when the server restarts. Durable database persistence, authentication, production rate limiting/observability, and live satellite-provider integration are not enabled. Do not present generated values as live or verified telemetry.
