from __future__ import annotations
import asyncio, heapq, math, os, uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(APP_DIR, "..", ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

def utcnow(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def meta(): return {"data_mode":"demo", "is_demo":True, "source":"generated", "generated_at":utcnow()}

NODES = [
 {"id":"SAT-LEO-104","name":"Aurora-104","type":"satellite","status":"active","orbit":"LEO","latitude":28.6,"longitude":72.1,"altitude_km":550,"connections":["SAT-LEO-219","GS-SVALBARD","GS-MEERUT"],"telemetry":{"latency_ms":24.8,"battery_pct":91.2,"signal_db":-67.4}},
 {"id":"SAT-LEO-219","name":"Kepler-219","type":"satellite","status":"degraded","orbit":"LEO","latitude":-8.2,"longitude":115.4,"altitude_km":570,"connections":["SAT-LEO-104","SAT-MEO-031"],"telemetry":{"latency_ms":48.1,"battery_pct":68.5,"signal_db":-82.1}},
 {"id":"SAT-LEO-408","name":"Pioneer-408","type":"satellite","status":"active","orbit":"LEO","latitude":51.4,"longitude":-18.3,"altitude_km":540,"connections":["SAT-MEO-031","GS-SVALBARD"],"telemetry":{"latency_ms":19.3,"battery_pct":96.1,"signal_db":-64.8}},
 {"id":"SAT-MEO-031","name":"Meridian-031","type":"satellite","status":"active","orbit":"MEO","latitude":12.4,"longitude":-96.8,"altitude_km":8200,"connections":["SAT-LEO-219","SAT-LEO-408","GS-MEERUT"],"telemetry":{"latency_ms":62.7,"battery_pct":87.9,"signal_db":-71.2}},
 {"id":"GS-SVALBARD","name":"Svalbard Ground Station","type":"ground_station","status":"active","orbit":None,"latitude":78.2,"longitude":15.6,"altitude_km":0.02,"connections":["SAT-LEO-104","SAT-LEO-408"],"telemetry":{"latency_ms":8.4,"uplink_mbps":42000,"signal_db":-54.1}},
 {"id":"GS-MEERUT","name":"Meerut Ground Station","type":"ground_station","status":"active","orbit":None,"latitude":28.98,"longitude":77.7,"altitude_km":0.22,"connections":["SAT-LEO-104","SAT-MEO-031"],"telemetry":{"latency_ms":11.2,"uplink_mbps":18500,"signal_db":-59.7}},
 {"id":"GS-PERTH","name":"Perth Ground Station","type":"ground_station","status":"inactive","orbit":None,"latitude":-31.95,"longitude":115.86,"altitude_km":0.03,"connections":[],"telemetry":{"latency_ms":None,"uplink_mbps":0,"signal_db":None}},
]
LINKS = {tuple(sorted((a,b))): v for a,b,v in [("SAT-LEO-104","SAT-LEO-219",28),("SAT-LEO-104","GS-SVALBARD",15),("SAT-LEO-104","GS-MEERUT",12),("SAT-LEO-219","SAT-MEO-031",42),("SAT-LEO-408","SAT-MEO-031",35),("SAT-LEO-408","GS-SVALBARD",18),("SAT-MEO-031","GS-MEERUT",31)]}
EVENTS = [
 {"id":"evt-1001","timestamp":"2026-10-23T14:42:01Z","severity":"warning","category":"Network","description":"Conjunction warning trajectory shift for SAT-LEO-219","node_id":"SAT-LEO-219"},
 {"id":"evt-1002","timestamp":"2026-10-23T14:38:15Z","severity":"success","category":"Ground Station","description":"Svalbard downlink link re-established","node_id":"GS-SVALBARD"},
 {"id":"evt-1003","timestamp":"2026-10-23T14:30:00Z","severity":"info","category":"Security","description":"Demo key-rotation event recorded across MEO nodes","node_id":"SAT-MEO-031"},
 {"id":"evt-1004","timestamp":"2026-10-23T14:15:22Z","severity":"info","category":"Propulsion","description":"Demo station-keeping burn completed for SAT-LEO-408","node_id":"SAT-LEO-408"},
]
ALERTS = [{"id":"alt-01","severity":"warning","title":"Degraded link: SAT-LEO-219","description":"Signal strength below nominal threshold in demo telemetry.","node_id":"SAT-LEO-219","recommended_action":"Inspect alternate routes and compare link quality.","acknowledged":False,"is_demo":True}]
SIMS: dict[str,dict[str,Any]] = {}
ROUTES: dict[str,dict[str,Any]] = {}

app = FastAPI(title="PrioritySat API", version="1.0.0", description="Demo-mode orbital network exploration and simulation API")
origins=os.getenv("FRONTEND_ORIGINS","http://localhost:5173,http://localhost:8000").split(',')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in origins], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class RouteRequest(BaseModel):
 source_id: str
 destination_id: str
 max_hops: int = Field(default=8, ge=1, le=20)
 latency_weight: float = Field(default=1.0, ge=0, le=10)
 availability_weight: float = Field(default=0.2, ge=0, le=10)
 avoid_degraded: bool = True
class SimulationRequest(BaseModel):
 scenario: str = Field(pattern="^(satellite_failure|ground_station_outage|increased_traffic|high_latency|network_congestion|multi_node_failure)$")
 affected_node: str | None = None
 traffic_multiplier: float = Field(default=1.5, ge=1, le=10)
 duration_seconds: int = Field(default=20, ge=5, le=120)

@app.get("/health")
def health(): return {"status":"ok","service":"prioritysat-api","timestamp":utcnow(),"data_mode":"demo","is_demo":True}
@app.get("/api/v1/system/status")
def system_status(): return {"api":{"status":"connected"},"database":{"status":"not_required_for_demo","configured":False},"provider":{"status":"not_configured","name":None},"data_mode":"demo","is_demo":True,"message":"API connected; generated sample data only.","timestamp":utcnow()}
@app.get("/api/v1/overview/metrics")
def metrics(): return {**meta(),"network_health":94.2,"active_satellites":3,"total_satellites":4,"average_latency_ms":36.2,"availability_pct":99.92,"active_alerts":len([a for a in ALERTS if not a['acknowledged']])}
@app.get("/api/v1/overview")
def overview(): return {**meta(),"metrics":metrics(),"alerts":ALERTS,"recent_activity":EVENTS[:4],"nodes_summary":{"total":len(NODES),"satellites":4,"ground_stations":3}}
@app.get("/api/v1/nodes")
def nodes(search:str|None=None, type:str|None=None, status:str|None=None, orbit:str|None=None, limit:int=Query(50,ge=1,le=200), offset:int=Query(0,ge=0)):
 result=NODES[:]
 if search: result=[n for n in result if search.lower() in (n['id']+' '+n['name']).lower()]
 if type: result=[n for n in result if n['type']==type]
 if status: result=[n for n in result if n['status']==status]
 if orbit: result=[n for n in result if (n.get('orbit') or '').lower()==orbit.lower()]
 return {**meta(),"items":result[offset:offset+limit],"total":len(result),"limit":limit,"offset":offset}
@app.get("/api/v1/nodes/{node_id}")
def node_detail(node_id:str):
 n=next((x for x in NODES if x['id']==node_id),None)
 if not n: raise HTTPException(404,detail={"code":"NODE_NOT_FOUND","message":f"Node {node_id} was not found"})
 return {**meta(),"node":n}
@app.get("/api/v1/satellites")
def satellites(status:str|None=None): return {**meta(),"items":[n for n in NODES if n['type']=='satellite' and (not status or n['status']==status)]}
@app.get("/api/v1/ground-stations")
def ground_stations(status:str|None=None): return {**meta(),"items":[n for n in NODES if n['type']=='ground_station' and (not status or n['status']==status)]}
@app.get("/api/v1/satellites/{satellite_id}")
def satellite_detail(satellite_id:str):
 n=next((x for x in NODES if x['id']==satellite_id and x['type']=='satellite'),None)
 if not n: raise HTTPException(404,detail={"code":"SATELLITE_NOT_FOUND","message":f"Satellite {satellite_id} was not found"})
 return {**meta(),"node":n}
@app.get("/api/v1/ground-stations/{station_id}")
def ground_station_detail(station_id:str):
 n=next((x for x in NODES if x['id']==station_id and x['type']=='ground_station'),None)
 if not n: raise HTTPException(404,detail={"code":"GROUND_STATION_NOT_FOUND","message":f"Ground station {station_id} was not found"})
 return {**meta(),"node":n}

def route_path(src,dst,avoid_degraded=True,latency_weight=1.0,max_hops=20,availability_weight=0.2,blocked_nodes=None):
 byid={n['id']:n for n in NODES}
 blocked_nodes=set(blocked_nodes or ())
 if src not in byid or dst not in byid: raise HTTPException(422,detail={"code":"INVALID_NODE","message":"Select a valid source and destination node."})
 if src==dst: raise HTTPException(422,detail={"code":"SAME_ENDPOINT","message":"Source and destination must be different."})
 dist={src:0}; prev={}; heap=[(0,src)]
 while heap:
  cost,u=heapq.heappop(heap)
  if cost!=dist.get(u): continue
  if u==dst: break
  for v in byid[u]['connections']:
   if v in blocked_nodes: continue
   edge=LINKS.get(tuple(sorted((u,v))))
   if edge is None or byid[v]['status']=='inactive' or (avoid_degraded and byid[v]['status']=='degraded'): continue
   w=edge*latency_weight + (35 if byid[v]['status']=='degraded' else 0) + availability_weight*(12 if byid[v]['status']=='degraded' else 0.5)
   if cost+w<dist.get(v,float('inf')): dist[v]=cost+w; prev[v]=u; heapq.heappush(heap,(cost+w,v))
 if dst not in dist: raise HTTPException(404,detail={"code":"NO_ROUTE","message":"No feasible path exists with the selected preferences."})
 path=[dst]
 while path[-1]!=src: path.append(prev[path[-1]])
 path.reverse()
 if len(path)-1 > max_hops: raise HTTPException(422,detail={"code":"MAX_HOPS_EXCEEDED","message":f"The available path requires {len(path)-1} hops, above the configured maximum of {max_hops}."})
 hops=[]; latency=0
 for a,b in zip(path,path[1:]):
  l=LINKS[tuple(sorted((a,b)))]; latency+=l; hops.append({"from":a,"to":b,"latency_ms":l,"status":"degraded" if 'degraded' in (byid[a]['status'],byid[b]['status']) else "active"})
 return {"route_id":"route-"+uuid.uuid4().hex[:8],"node_ids":path,"hops":hops,"hop_count":len(hops),"latency_ms":round(latency,1),"availability_pct":round(max(90,99.99-len(hops)*0.035),3),"bottleneck":max(hops,key=lambda h:h['latency_ms']) if hops else None,"rationale":f"Lowest weighted path across {len(hops)} links using current demo graph costs.","is_demo":True,"data_mode":"demo","source":"generated"}
@app.post("/api/v1/routes/plan")
def plan_route(req:RouteRequest):
 primary=route_path(req.source_id,req.destination_id,req.avoid_degraded,req.latency_weight,req.max_hops,req.availability_weight)
 alternatives=[]
 # Generate valid alternatives by temporarily avoiding each primary intermediate node.
 for blocked in primary['node_ids'][1:-1]:
  try:
   alt=route_path(req.source_id,req.destination_id,req.avoid_degraded,req.latency_weight,req.max_hops,req.availability_weight,blocked_nodes={blocked})
   if alt['node_ids']!=primary['node_ids'] and all(a['node_ids']!=alt['node_ids'] for a in alternatives): alternatives.append(alt)
  except HTTPException: pass
 primary['recommended']=True
 for a in alternatives: a['recommended']=False
 ROUTES[primary['route_id']]=primary
 for a in alternatives: ROUTES[a['route_id']]=a
 return {**meta(),"recommended":primary,"alternatives":alternatives[:3],"preferences":req.model_dump()}
@app.get("/api/v1/routes")
def list_routes(): return {**meta(),"items":list(ROUTES.values())}
@app.get("/api/v1/routes/{route_id}")
def get_route(route_id:str):
 route=ROUTES.get(route_id)
 if not route: raise HTTPException(404,detail={"code":"ROUTE_NOT_FOUND","message":"Route not found. Plan a route first."})
 return {**meta(),"route":route}
@app.get("/api/v1/simulations/scenarios")
def scenarios(): return {**meta(),"items":[{"id":"satellite_failure","name":"Satellite failure","description":"Simulate loss of a satellite node."},{"id":"ground_station_outage","name":"Ground-station outage","description":"Simulate loss of a ground station."},{"id":"increased_traffic","name":"Increased traffic","description":"Increase network traffic load."},{"id":"high_latency","name":"High latency links","description":"Add latency to network links."},{"id":"network_congestion","name":"Network congestion","description":"Model congestion and throughput pressure."},{"id":"multi_node_failure","name":"Multi-node failure","description":"Simulate a multi-node disruption and recovery."}]}
async def run_sim(sim_id:str):
 sim=SIMS[sim_id]
 for i in range(1,11):
  await asyncio.sleep(sim['duration_seconds']/10)
  if sim['status']=='cancelled' or sim['status']=='reset': return
  while sim['status']=='paused': await asyncio.sleep(.2)
  if sim['status']!='running': return
  sim['progress']=i*10
  sim['series'].append({"time_s":i*sim['duration_seconds']/10,"latency_ms":round(sim['baseline_latency']*(1+(i/10)*sim['impact']),2),"availability_pct":round(99.92-(i/10)*sim['impact']*1.7,3)})
 sim['status']='completed'; sim['completed_at']=utcnow(); sim['results']={"baseline_latency_ms":sim['baseline_latency'],"final_latency_ms":sim['series'][-1]['latency_ms'],"availability_pct":sim['series'][-1]['availability_pct'],"impact_pct":round(sim['impact']*100,1),"series":sim['series'],"is_demo":True,"data_mode":"demo"}
 EVENTS.insert(0,{"id":"evt-"+uuid.uuid4().hex[:8],"timestamp":utcnow(),"severity":"success","category":"Simulation","description":f"Demo simulation {sim_id} completed.","node_id":sim.get('affected_node')})
@app.post("/api/v1/simulations")
async def create_sim(req:SimulationRequest):
 if req.affected_node and not any(n['id']==req.affected_node for n in NODES): raise HTTPException(422,detail={"code":"INVALID_NODE","message":"Affected node does not exist."})
 sid="sim-"+uuid.uuid4().hex[:8]; impact={"satellite_failure":.4,"ground_station_outage":.3,"increased_traffic":.25,"high_latency":.2,"network_congestion":.35,"multi_node_failure":.55}[req.scenario]
 SIMS[sid]={"id":sid,"scenario":req.scenario,"affected_node":req.affected_node,"traffic_multiplier":req.traffic_multiplier,"duration_seconds":req.duration_seconds,"status":"running","progress":0,"created_at":utcnow(),"generated_at":utcnow(),"completed_at":None,"baseline_latency":36.2,"impact":impact,"series":[],"results":None,"is_demo":True,"data_mode":"demo"}
 asyncio.create_task(run_sim(sid)); EVENTS.insert(0,{"id":"evt-"+uuid.uuid4().hex[:8],"timestamp":utcnow(),"severity":"info","category":"Simulation","description":f"Demo simulation {req.scenario} started.","node_id":req.affected_node})
 return SIMS[sid]
def get_sim(sim_id):
 if sim_id not in SIMS: raise HTTPException(404,detail={"code":"SIMULATION_NOT_FOUND","message":"Simulation not found."})
 return SIMS[sim_id]
@app.get("/api/v1/simulations/{simulation_id}")
def simulation_status(simulation_id:str): return get_sim(simulation_id)
@app.get("/api/v1/simulations/{simulation_id}/results")
def simulation_results(simulation_id:str):
 sim=get_sim(simulation_id)
 if sim['status']!='completed': raise HTTPException(409,detail={"code":"RESULTS_NOT_READY","message":"Results are available after the simulation completes."})
 return {**meta(),"simulation_id":simulation_id,**sim['results']}
@app.post("/api/v1/simulations/{simulation_id}/pause")
def pause_sim(simulation_id:str):
 s=get_sim(simulation_id)
 if s['status']!='running': raise HTTPException(409,detail={"code":"INVALID_STATE","message":"Only running simulations can be paused."})
 s['status']='paused'; return s
@app.post("/api/v1/simulations/{simulation_id}/resume")
def resume_sim(simulation_id:str):
 s=get_sim(simulation_id)
 if s['status']!='paused': raise HTTPException(409,detail={"code":"INVALID_STATE","message":"Only paused simulations can be resumed."})
 s['status']='running'; return s
@app.post("/api/v1/simulations/{simulation_id}/cancel")
def cancel_sim(simulation_id:str):
 s=get_sim(simulation_id)
 if s['status'] not in ('running','paused'): raise HTTPException(409,detail={"code":"INVALID_STATE","message":"This simulation cannot be cancelled."})
 s['status']='cancelled'; return s
@app.post("/api/v1/simulations/{simulation_id}/reset")
def reset_sim(simulation_id:str):
 s=get_sim(simulation_id); s['status']='reset'; s['progress']=0; s['series']=[]; s['results']=None; return {"id":s['id'],"status":"reset","progress":0,"is_demo":True,"data_mode":"demo"}
@app.get("/api/v1/activity/recent")
def recent_activity(limit:int=Query(8,ge=1,le=50)): return {**meta(),"items":EVENTS[:limit]}
@app.get("/api/v1/activity")
def activity(search:str|None=None,severity:str|None=None,category:str|None=None,node_id:str|None=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0)):
 items=EVENTS[:]
 if search: items=[e for e in items if search.lower() in (e['description']+' '+e['category']+' '+str(e.get('node_id'))).lower()]
 if severity: items=[e for e in items if e['severity']==severity]
 if category: items=[e for e in items if e['category'].lower()==category.lower()]
 if node_id: items=[e for e in items if e.get('node_id')==node_id]
 return {**meta(),"items":items[offset:offset+limit],"total":len(items),"limit":limit,"offset":offset}
@app.get("/api/v1/activity/{event_id}")
def activity_detail(event_id:str):
 e=next((e for e in EVENTS if e['id']==event_id),None)
 if not e: raise HTTPException(404,detail={"code":"EVENT_NOT_FOUND","message":"Activity event not found."})
 return {**meta(),"event":e}
@app.get("/api/v1/alerts")
def alerts(): return {**meta(),"items":ALERTS}
@app.get("/api/v1/alerts/{alert_id}")
def alert_detail(alert_id:str):
 a=next((a for a in ALERTS if a['id']==alert_id),None)
 if not a: raise HTTPException(404,detail={"code":"ALERT_NOT_FOUND","message":"Alert not found."})
 return {**meta(),"alert":a}
@app.post("/api/v1/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id:str):
 a=next((a for a in ALERTS if a['id']==alert_id),None)
 if not a: raise HTTPException(404,detail={"code":"ALERT_NOT_FOUND","message":"Alert not found."})
 a['acknowledged']=True; a['acknowledged_at']=utcnow(); return {**meta(),"alert":a}
@app.websocket("/api/v1/ws/events")
async def ws_events(ws:WebSocket):
 await ws.accept()
 try:
  last=''
  while True:
   payload={"version":1,"type":"heartbeat","event_id":"heartbeat-"+str(int(datetime.now(timezone.utc).timestamp())),"timestamp":utcnow(),"data_mode":"demo","is_demo":True,"simulations":[{"id":s['id'],"status":s['status'],"progress":s['progress']} for s in SIMS.values()],"latest_activity":EVENTS[0] if EVENTS else None}
   await ws.send_json(payload); await asyncio.sleep(1.5)
 except (WebSocketDisconnect,RuntimeError): pass

# Serve the provided original UI and integration script from the same origin.
@app.get("/")
def index(): return FileResponse(os.path.join(FRONTEND_DIR,"index.html"))
if os.path.isdir(FRONTEND_DIR): app.mount("/static",StaticFiles(directory=FRONTEND_DIR),name="static")
