from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
def test_health_is_demo_labeled():
 r=client.get('/health'); assert r.status_code==200 and r.json()['is_demo'] is True
def test_nodes_are_demo_data():
 r=client.get('/api/v1/nodes'); assert r.status_code==200 and r.json()['is_demo'] is True and r.json()['total'] >= 5
def test_route_plan():
 r=client.post('/api/v1/routes/plan',json={'source_id':'GS-MEERUT','destination_id':'GS-SVALBARD'}); assert r.status_code==200 and r.json()['recommended']['hop_count'] >= 1 and r.json()['is_demo'] is True
def test_invalid_route_endpoint():
 r=client.post('/api/v1/routes/plan',json={'source_id':'NOPE','destination_id':'GS-SVALBARD'}); assert r.status_code==422
def test_activity_filter():
 r=client.get('/api/v1/activity?severity=warning'); assert r.status_code==200 and all(x['severity']=='warning' for x in r.json()['items'])

def test_planned_route_can_be_retrieved():
    planned = client.post('/api/v1/routes/plan', json={
        'source_id': 'GS-MEERUT', 'destination_id': 'GS-SVALBARD'
    })
    assert planned.status_code == 200
    route_id = planned.json()['recommended']['route_id']
    detail = client.get(f'/api/v1/routes/{route_id}')
    assert detail.status_code == 200
    assert detail.json()['route']['route_id'] == route_id
    assert detail.json()['is_demo'] is True

def test_simulation_lifecycle_is_backend_managed():
    created = client.post('/api/v1/simulations', json={
        'scenario': 'satellite_failure', 'duration_seconds': 5
    })
    assert created.status_code == 200
    sim_id = created.json()['id']
    assert created.json()['is_demo'] is True
    status = client.get(f'/api/v1/simulations/{sim_id}')
    assert status.status_code == 200
    assert status.json()['status'] in ('running', 'completed')

def test_frontend_is_served_and_api_client_exists():
    page = client.get('/')
    assert page.status_code == 200
    assert 'PrioritySat' in page.text
    script = client.get('/static/api.js')
    assert script.status_code == 200
    assert 'planRoute' in script.text and 'startSimulation' in script.text
    app_script = client.get('/static/app.js')
    assert app_script.status_code == 200
    assert 'renderMap' in app_script.text and 'loadSimulationResults' in app_script.text

def test_satellite_and_ground_station_detail_aliases():
    sat = client.get('/api/v1/satellites/SAT-LEO-104')
    station = client.get('/api/v1/ground-stations/GS-MEERUT')
    assert sat.status_code == 200 and sat.json()['node']['type'] == 'satellite'
    assert station.status_code == 200 and station.json()['node']['type'] == 'ground_station'
    assert sat.json()['is_demo'] and station.json()['is_demo']

def test_orbit_filter_returns_only_matching_nodes():
    result = client.get('/api/v1/nodes?orbit=LEO')
    assert result.status_code == 200
    assert result.json()['items'] and all(n['orbit'] == 'LEO' for n in result.json()['items'])
