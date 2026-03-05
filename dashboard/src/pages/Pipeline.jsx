import React, { useState, useEffect } from 'react';
import { Satellite, Link2, Shield, ShieldAlert, BarChart3, Tag, Wrench, MousePointer, Archive, Server, Wifi, DollarSign, ArrowDown } from 'lucide-react';
import api from '../api';
import { Card, StatCard, EmptyState } from '../components/shared';

const STAGES = [
  { name: 'Job Scrapers', sub: 'Adzuna, JSearch, RemoteOK, LinkedIn API, ActiveJobs, JobsSearch', icon: Satellite, color: 'var(--cyan)' },
  { name: 'Deduplicator', sub: 'SHA256 fingerprint — cross-source dedup', icon: Link2, color: 'var(--text-muted)' },
  { name: 'Visa Filter', sub: 'Regex pattern match + Claude Haiku fallback', icon: Shield, color: 'var(--amber)' },
  { name: 'Gate Check', sub: 'Per-company limits, URL dedup, daily cap', icon: ShieldAlert, color: '#f97316' },
  { name: 'ATS Scorer', sub: 'TF-IDF cosine + keyword matching + LLM semantic', icon: BarChart3, color: 'var(--purple)' },
  { name: 'Tier Classifier', sub: 'Top Tier companies get higher optimization', icon: Tag, color: '#ec4899' },
  { name: 'Resume Optimizer', sub: 'Claude Sonnet iterates LaTeX to 85%+ ATS score', icon: Wrench, color: 'var(--blue)' },
  { name: 'Browser Engine', sub: 'Playwright + stealth patches for ATS form fill', icon: MousePointer, color: 'var(--green)' },
  { name: 'Archive & Report', sub: 'B2 cloud backup, screenshot, Telegram alert', icon: Archive, color: 'var(--text-muted)' },
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
  { name: 'Adzuna', type: 'REST API', limit: '10k/mo', color: '#3b82f6' },
  { name: 'JSearch', type: 'RapidAPI', limit: '200/day', color: '#10b981' },
  { name: 'RemoteOK', type: 'Public JSON', limit: 'Unlimited', color: '#f59e0b' },
  { name: 'LinkedIn API', type: 'RapidAPI', limit: '500/day', color: '#0a66c2' },
  { name: 'Active Jobs DB', type: 'RapidAPI', limit: '1k/day', color: '#8b5cf6' },
  { name: 'Jobs Search API', type: 'RapidAPI', limit: '500/day', color: '#ec4899' },
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

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 4 }}>
          Pipeline
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Architecture overview and system health
        </p>
      </div>

      {/* Quick stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 14,
        marginBottom: 24,
      }}>
        <StatCard label="In Queue" value={queue?.total || 0} color="var(--cyan)" icon={Wrench} />
        <StatCard label="Total Cost (30d)" value={costs ? `$${costs.total_cost}` : '—'} color="var(--amber)" icon={DollarSign} />
        <StatCard label="Cost / Application" value={costs ? `$${costs.per_application}` : '—'} color="var(--purple)" icon={BarChart3} />
        <StatCard label="Handlers Active" value={HANDLERS.filter(h => h.status === 'active').length} color="var(--green)" icon={Server} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 18 }}>
        {/* Pipeline Architecture */}
        <Card title="Pipeline Architecture">
          {STAGES.map((st, i) => {
            const Icon = st.icon;
            return (
              <div key={i}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '11px 14px',
                  background: 'var(--bg-primary)',
                  borderRadius: 10,
                  marginBottom: 2,
                  border: '1px solid var(--border)',
                  transition: 'border-color 0.2s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = `${st.color}30`}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                  <div style={{
                    width: 34,
                    height: 34,
                    borderRadius: 8,
                    background: `${st.color}10`,
                    border: `1px solid ${st.color}18`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Icon size={16} color={st.color} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: st.color }}>{st.name}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.4 }}>{st.sub}</div>
                  </div>
                  <div className="mono" style={{
                    fontSize: 9,
                    color: 'var(--text-muted)',
                    padding: '2px 6px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 4,
                    letterSpacing: '0.04em',
                  }}>
                    {i + 1}
                  </div>
                </div>
                {i < STAGES.length - 1 && (
                  <div style={{
                    display: 'flex',
                    justifyContent: 'center',
                    padding: '2px 0',
                  }}>
                    <ArrowDown size={12} color="var(--text-muted)" style={{ opacity: 0.3 }} />
                  </div>
                )}
              </div>
            );
          })}
        </Card>

        {/* Right side */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* ATS Handlers */}
          <Card title="ATS Handlers">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {HANDLERS.map((h, i) => (
                <div key={i} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 14px',
                  background: 'var(--bg-primary)',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  transition: 'border-color 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-light)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Server size={13} color="var(--text-muted)" />
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{h.name}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{h.url}</span>
                  </div>
                  <span className="badge" style={{
                    fontSize: 9,
                    color: h.status === 'active' ? 'var(--green)' : 'var(--amber)',
                    background: h.status === 'active' ? 'var(--green-bg)' : 'var(--amber-bg)',
                    border: `1px solid ${h.status === 'active' ? 'var(--green)' : 'var(--amber)'}18`,
                  }}>
                    <span style={{
                      width: 5,
                      height: 5,
                      borderRadius: '50%',
                      background: h.status === 'active' ? 'var(--green)' : 'var(--amber)',
                    }} />
                    {h.status === 'active' ? 'Active' : 'Fallback'}
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
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 14px',
                  background: 'var(--bg-primary)',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  fontSize: 12,
                  transition: 'border-color 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = `${sc.color}30`}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="status-dot live" style={{
                      background: sc.color,
                      boxShadow: `0 0 6px ${sc.color}`,
                      width: 6,
                      height: 6,
                    }} />
                    <span style={{ fontWeight: 600 }}>{sc.name}</span>
                    <span style={{
                      fontSize: 9,
                      color: 'var(--text-muted)',
                      padding: '1px 6px',
                      background: 'var(--bg-tertiary)',
                      borderRadius: 4,
                    }}>
                      {sc.type}
                    </span>
                  </div>
                  <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>{sc.limit}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Cost breakdown */}
      {costs && costs.total_cost > 0 && (
        <Card title="Cost Breakdown (30 days)">
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 10,
          }}>
            {Object.entries(costs.by_category || {}).map(([cat, amount]) => (
              <div key={cat} style={{
                padding: '12px 14px',
                background: 'var(--bg-primary)',
                borderRadius: 8,
                border: '1px solid var(--border)',
              }}>
                <div style={{
                  fontSize: 10,
                  color: 'var(--text-muted)',
                  marginBottom: 4,
                  textTransform: 'capitalize',
                }}>
                  {cat}
                </div>
                <div className="mono" style={{
                  fontSize: 18,
                  fontWeight: 800,
                  color: 'var(--amber)',
                  letterSpacing: '-0.03em',
                }}>
                  ${amount}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
