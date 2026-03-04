// ── API Client ──────────────────────────────────────────
const BASE = '/api';

async function request(path, opts = {}) {
  try {
    const r = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts,
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (e) {
    console.warn(`API ${path}:`, e.message);
    return null;
  }
}

export const api = {
  // Stats
  overview:    ()        => request('/stats/overview'),
  costs:       (days=30) => request(`/stats/costs?days=${days}`),
  daily:       (days=14) => request(`/stats/daily?days=${days}`),

  // Jobs
  listJobs:    (params)  => request(`/jobs/?${new URLSearchParams(params)}`),
  getJob:      (id)      => request(`/jobs/${id}`),
  jobSources:  ()        => request('/jobs/stats/sources'),

  // Applications
  listApps:    (params={}) => request(`/applications/?${new URLSearchParams(params)}`),
  getQueue:    ()        => request('/applications/queue'),
  getPipeline: ()        => request('/applications/pipeline'),
  updateStage: (id, stage) => request(`/applications/${id}/stage`, {
    method: 'PUT', body: JSON.stringify({ stage }),
  }),
  addManual:   (data)    => request('/applications/manual', {
    method: 'POST', body: JSON.stringify(data),
  }),

  // Pipeline
  trigger:     ()        => request('/pipeline/trigger', { method: 'POST' }),
  health:      ()        => request('/health'),

  // Settings
  getSettings: ()        => request('/settings/'),
};

export default api;
