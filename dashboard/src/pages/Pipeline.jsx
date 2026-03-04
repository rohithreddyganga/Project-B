import React, { useState, useEffect } from 'react';
import api from '../api';
import { Card, StatCard, EmptyState } from '../components/shared';

const STAGES = [
  { name: 'Job Scrapers', sub: 'Adzuna · JSearch · RemoteOK · LinkedIn API · ActiveJobs · JobsSearch', icon: '📡', color: 'var(--cyan)' },
  { name: 'Deduplicator', sub: 'SHA256 fingerprint — cross-source dedup', icon: '🔗', color: 'var(--text-muted)' },
  { name: 'Visa Filter', sub: 'Regex pattern match + Claude Haiku fallback', icon: '🛂', color: 'var(--amber)' },
  { name: 'Gate Check', sub: 'Per-company limits · URL dedup · Daily cap', icon: '🚧', color: '#f97316' },
  { name: 'ATS Scorer', sub: 'TF-IDF cosine + keyword matching + LLM semantic', icon: '📊', color: 'var(--purple)' },
  { name: 'Tier Classifier', sub: 'Top Tier companies get higher optimization', icon: '🏷️', color: '#ec4899' },
  { name: 'Resume Optimizer', sub: 'Claude Sonnet iterates LaTeX to 85%+ ATS score', icon: '🔧', color: 'var(--blue)' },
  { name: 'Browser Engine', sub: 'Playwright + stealth patches → ATS form fill', icon: '🖱️', color: 'var(--green)' },
  { name: 'Archive & Report', sub: 'B2 cloud backup · screenshot · Telegram alert', icon: '📦', color: 'var(--text-muted)' },
];

const HANDLERS = [
  { name: 'Greenhouse', url: 'boards.greenhouse.io', status: 'active' },
  { name: 'Lever', url: 'jobs.lever.co', status: 'active' },
  { name: 'Workday', url: 'myworkdayjobs.com', status: 'active' },
  { name: 'iCIMS', url: 'careers-*.icims.com', status: 'active' },
  { name: 'SmartRecruiters', url: 'jobs.smartrecruiters.com', status: 'active' },
  { name: 'Taleo', url: '*.taleo.net', status: 'active' },
  { name: 'Generic AI', url: 'Any other portal', status: 'fallback' },
];

const SCRAPERS = [
  { name: 'Adzuna', type: 'REST API', key: 'ADZUNA_APP_ID + ADZUNA_API_KEY', limit: '10k/mo', status: 'active' },
  { name: 'JSearch', type: 'RapidAPI', key: 'JSEARCH_API_KEY', limit: '200/day', status: 'active' },
  { name: 'RemoteOK', type: 'Public JSON', key: 'None', limit: '∞', status: 'active' },
  { name: 'LinkedIn API', type: 'RapidAPI', key: 'JSEARCH_API_KEY (shared)', limit: '500/day', status: 'active' },
  { name: 'Active Jobs DB', type: 'RapidAPI', key: 'JSEARCH_API_KEY (shared)', limit: '1k/day', status: 'active' },
  { name: 'Jobs Search API', type: 'RapidAPI', key: 'JSEARCH_API_KEY (shared)', limit: '500/day', status: 'active' },
];

export default function Pipeline({ stats }) {
  const [queue, setQueue] = useState(null);
  const [costs, setCosts] = useState(null);

  useEffect(() => {
    (async () => {
      const [q, c] = await Promise.all([api.getQueue(), api.costs(30)]);
      setQueue(q);
      setCosts(c);
    })();
  }, []);

  const s = stats || {};

  return (
    <div className="fade-in">
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Pipeline</h1>

      {/* Quick stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        <StatCard label="In Queue" value={queue?.total || 0} color="var(--cyan)" />
        <StatCard label="Total Cost (30d)" value={costs ? `$${costs.total_cost}` : '—'} color="var(--amber)" />
        <StatCard label="Cost / Application" value={costs ? `$${costs.per_application}` : '—'} color="var(--purple)" />
        <StatCard label="Handlers Active" value={HANDLERS.filter(h => h.status === 'active').length} color="var(--green)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Pipeline Architecture */}
        <Card title="Pipeline Architecture">
          {STAGES.map((st, i) => (
            <div key={i}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', background: 'var(--bg-primary)',
                borderRadius: 8, marginBottom: 2,
                border: '1px solid var(--border)',
              }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 6,
                  background: `${st.color}12`, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                  fontSize: 16, flexShrink: 0,
                }}>{st.icon}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: st.color }}>{st.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{st.sub}</div>
                </div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  Stage {i + 1}
                </div>
              </div>
              {i < STAGES.length - 1 && (
                <div style={{ width: 2, height: 4, background: 'var(--border)', margin: '0 auto' }} />
              )}
            </div>
          ))}
        </Card>

        {/* Right side */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* ATS Handlers */}
          <Card title="ATS Handlers">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {HANDLERS.map((h, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px', background: 'var(--bg-primary)',
                  borderRadius: 6, border: '1px solid var(--border)',
                }}>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{h.name}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 8 }}>{h.url}</span>
                  </div>
                  <span style={{
                    fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 3,
                    color: h.status === 'active' ? 'var(--green)' : 'var(--amber)',
                    background: h.status === 'active' ? 'var(--green-bg)' : 'var(--amber-bg)',
                  }}>
                    {h.status === 'active' ? '● Active' : '○ Fallback'}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Scrapers */}
          <Card title="Job Sources (6 APIs)">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {SCRAPERS.map((sc, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 12px', background: 'var(--bg-primary)',
                  borderRadius: 6, border: '1px solid var(--border)', fontSize: 12,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                      width: 7, height: 7, borderRadius: '50%', background: 'var(--green)',
                      boxShadow: '0 0 4px var(--green)',
                    }} />
                    <span style={{ fontWeight: 600 }}>{sc.name}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{sc.type}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>{sc.limit}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Cost breakdown */}
      {costs && costs.total_cost > 0 && (
        <Card title="Cost Breakdown (30 days)">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
            {Object.entries(costs.by_category || {}).map(([cat, amount]) => (
              <div key={cat} style={{
                padding: '10px 12px', background: 'var(--bg-primary)',
                borderRadius: 6, border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{cat}</div>
                <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--amber)' }}>${amount}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
