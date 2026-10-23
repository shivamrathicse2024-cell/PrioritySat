/* PrioritySat API client — all operational values are demo-generated until a verified provider is configured. */
(() => {
  'use strict';
  const base = (window.PRIORITYSAT_API_BASE || `${location.origin}/api/v1`).replace(/\/$/, '');
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeout || 10000);
    try {
      const response = await fetch(`${base}${path}`, { ...options, signal: options.signal || controller.signal, headers: { Accept: 'application/json', ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {}) } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload?.detail?.message || (typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`));
      return payload;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Request timed out. Check whether the FastAPI backend is running.');
      throw error;
    } finally { clearTimeout(timer); }
  }
  window.PrioritySatAPI = {
    base,
    health: () => fetch('/health', {cache:'no-store'}).then(async r => { if(!r.ok) throw new Error(`Health check failed (${r.status})`); return r.json(); }),
    status: () => request('/system/status'), overview: () => request('/overview'), metrics: () => request('/overview/metrics'),
    nodes: (filters={}) => request('/nodes?' + new URLSearchParams(Object.entries(filters).filter(([,v]) => v !== '' && v != null))),
    node: id => request(`/nodes/${encodeURIComponent(id)}`),
    planRoute: body => request('/routes/plan', {method:'POST',body:JSON.stringify(body)}),
    scenarios: () => request('/simulations/scenarios'),
    startSimulation: body => request('/simulations',{method:'POST',body:JSON.stringify(body)}),
    simulation: id => request(`/simulations/${encodeURIComponent(id)}`),
    simulationAction: (id,action) => request(`/simulations/${encodeURIComponent(id)}/${action}`,{method:'POST'}),
    simulationResults: id => request(`/simulations/${encodeURIComponent(id)}/results`),
    activity: filters => request('/activity?' + new URLSearchParams(Object.entries(filters || {}).filter(([,v]) => v !== '' && v != null))),
    recentActivity: (limit=6) => request(`/activity/recent?limit=${limit}`),
    alerts: () => request('/alerts'), acknowledgeAlert: id => request(`/alerts/${encodeURIComponent(id)}/acknowledge`,{method:'POST'})
  };
})();
