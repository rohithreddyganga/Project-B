import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, AreaChart, Area } from 'recharts';
import { TrendingUp, Target, Send, Award, Brain, BarChart3, ExternalLink, ArrowRight, Layers } from 'lucide-react';
import api from '../api';
import { StatCard, Card, ScoreBadge, StatusPill, SourceBadge, STATUS, SOURCES } from '../components/shared';

export default function Dashboard({ stats, refresh }) {
  const [funnelData, setFunnelData] = useState(null);
  const [topJobs, setTopJobs] = useState([]);
  const [dailyData, setDailyData] = useState([]);
  const [sourceCounts, setSourceCounts] = useState({});
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      const [daily, sources, jobs] = await Promise.all([
        api.daily(14),
        api.jobSources(),
        api.listJobs({ per_page: 200, min_score: 1 }),
      ]);
      setDailyData(daily?.daily || []);
      setSourceCounts(sources?.sources || {});
      const sorted = (jobs?.jobs || []).sort((a, b) => (b.match_score || 0) - (a.match_score || 0));
      setTopJobs(sorted.slice(0, 10));

      const allStatuses = Object.keys(STATUS);
      const counts = {};
      for (const st of allStatuses) {
        const d = await api.listJobs({ status: st, per_page: 1 });
        counts[st] = d?.total || 0;
      }
      counts._total = jobs?.total || 0;
      setFunnelData(counts);
    })();
  }, []);

  const s = stats || { total_applications: 0, today_applications: 0, success_rate: 0, total_interviews: 0, scraped_today: 0, avg_ats_score: 0 };

  return (
    <div className="fade-in">
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{
          fontSize: 24,
          fontWeight: 800,
          letterSpacing: '-0.03em',
          marginBottom: 4,
        }}>
          Dashboard
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
          Real-time overview of your automated job application pipeline
        </p>
      </div>

      {/* Stat cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(185px, 1fr))',
        gap: 14,
        marginBottom: 24,
      }}>
        <StatCard label="Jobs Scraped" value={s.scraped_today || '—'} color="var(--cyan)" icon={Layers} />
        <StatCard label="Applied Today" value={s.today_applications} color="var(--green)" icon={Send} />
        <StatCard label="Total Applied" value={s.total_applications} color="var(--purple)" icon={Target} />
        <StatCard label="Success Rate" value={`${s.success_rate}%`} color="var(--amber)" icon={TrendingUp} />
        <StatCard label="Interviews" value={s.total_interviews} color="#ec4899" icon={Award} />
        <StatCard label="Avg ATS Score" value={s.avg_ats_score ? `${s.avg_ats_score}%` : '—'} color="var(--blue)" icon={Brain} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Pipeline Funnel */}
        <Card title="Pipeline Funnel">
          {funnelData ? <FunnelViz data={funnelData} /> : <Shimmer lines={5} />}
        </Card>

        {/* Top Jobs */}
        <Card title="Top Scoring Jobs" action={
          <button onClick={() => nav('/jobs')} className="btn btn-ghost" style={{ padding: '4px 12px', fontSize: 11 }}>
            View All <ArrowRight size={12} />
          </button>
        }>
          {topJobs.length === 0 ? <Shimmer lines={6} /> : (
            <div>
              {topJobs.map((j, i) => (
                <div key={j.id} onClick={() => nav(`/jobs/${j.id}`)} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '9px 8px',
                  borderRadius: 8,
                  marginBottom: 2,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span className="mono" style={{
                    fontSize: 10,
                    color: 'var(--text-muted)',
                    width: 18,
                    textAlign: 'right',
                    flexShrink: 0,
                  }}>
                    {i + 1}
                  </span>
                  <ScoreBadge score={j.match_score} size="sm" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 12,
                      fontWeight: 600,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {j.title}
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{j.company}</div>
                  </div>
                  <StatusPill status={j.status} />
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Daily applications chart */}
        <Card title="Daily Applications (14 days)">
          {dailyData.length === 0 ? (
            <div style={{
              color: 'var(--text-muted)',
              fontSize: 12,
              padding: 30,
              textAlign: 'center',
              lineHeight: 1.7,
            }}>
              No application data yet — run the pipeline to start applying
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={dailyData}>
                <defs>
                  <linearGradient id="gradCyan" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10, fill: '#6b6b80' }}
                  tickFormatter={d => new Date(d).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                  axisLine={{ stroke: 'rgba(255,255,255,0.06)' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#6b6b80' }}
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(18,18,26,0.95)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 8,
                    fontSize: 12,
                    backdropFilter: 'blur(8px)',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fill="url(#gradCyan)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Source breakdown */}
        <Card title="Jobs by Source">
          {Object.keys(sourceCounts).length === 0 ? <Shimmer lines={4} /> : (
            <div>
              {Object.entries(sourceCounts).sort((a, b) => b[1] - a[1]).map(([src, count], i) => {
                const total = Object.values(sourceCounts).reduce((a, b) => a + b, 0) || 1;
                const pct = (count / total) * 100;
                return (
                  <div key={src} style={{ marginBottom: 10 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 4,
                    }}>
                      <SourceBadge source={src} />
                      <div className="mono" style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                      }}>
                        {count}
                      </div>
                    </div>
                    <div style={{
                      height: 4,
                      borderRadius: 10,
                      background: 'var(--bg-primary)',
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${pct}%`,
                        borderRadius: 10,
                        background: `linear-gradient(90deg, ${(SOURCES[src] || {}).color || 'var(--cyan)'}cc, ${(SOURCES[src] || {}).color || 'var(--cyan)'}44)`,
                        transition: 'width 0.6s ease',
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function FunnelViz({ data }) {
  const total = data._total || 1;
  const visaPass = total - (data.visa_blocked || 0);
  const gatePass = visaPass - (data.gate_blocked || 0);
  const scorePass = (data.queued || 0) + (data.optimizing || 0) + (data.submitted || 0) + (data.failed || 0) + (data.applying || 0);
  const applied = data.submitted || 0;

  const stages = [
    { label: 'Total Scraped', value: total, color: 'var(--text-muted)', gradient: 'linear-gradient(90deg, #6b6b80, #6b6b8066)' },
    { label: 'Visa Passed', value: visaPass, color: 'var(--cyan)', gradient: 'linear-gradient(90deg, #06b6d4, #06b6d466)' },
    { label: 'Gate Passed', value: gatePass, color: 'var(--blue)', gradient: 'linear-gradient(90deg, #60a5fa, #60a5fa66)' },
    { label: 'Score Passed', value: scorePass, color: 'var(--purple)', gradient: 'linear-gradient(90deg, #a78bfa, #a78bfa66)' },
    { label: 'Applied', value: applied, color: 'var(--green)', gradient: 'linear-gradient(90deg, #34d399, #34d39966)' },
  ];

  return (
    <div>
      {stages.map((st, i) => {
        const pct = Math.max((st.value / total) * 100, 3);
        return (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 11,
              color: 'var(--text-muted)',
              marginBottom: 4,
            }}>
              <span style={{ fontWeight: 500 }}>{st.label}</span>
              <span className="mono" style={{ color: st.color, fontWeight: 700 }}>{st.value}</span>
            </div>
            <div style={{
              height: 22,
              background: 'var(--bg-primary)',
              borderRadius: 6,
              overflow: 'hidden',
              border: '1px solid var(--border)',
            }}>
              <div style={{
                width: `${pct}%`,
                height: '100%',
                borderRadius: 5,
                background: st.gradient,
                transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                paddingRight: 6,
              }}>
                {pct > 12 && (
                  <span className="mono" style={{ fontSize: 9, color: '#fff', fontWeight: 700 }}>
                    {Math.round(pct)}%
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Drop-off breakdown */}
      <div style={{
        marginTop: 14,
        padding: '12px 14px',
        background: 'var(--bg-primary)',
        borderRadius: 8,
        border: '1px solid var(--border)',
        fontSize: 11,
      }}>
        <div style={{
          color: 'var(--text-muted)',
          fontWeight: 700,
          marginBottom: 6,
          fontSize: 10,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          Drop-off Points
        </div>
        {[
          { label: 'Visa Blocked', c: data.visa_blocked, color: 'var(--red)' },
          { label: 'Gate Blocked', c: data.gate_blocked, color: '#f97316' },
          { label: 'Below Threshold', c: data.below_threshold, color: '#ec4899' },
          { label: 'Opt. Failed', c: data.optimization_failed, color: 'var(--red)' },
          { label: 'Apply Failed', c: data.failed, color: 'var(--red)' },
        ].filter(r => r.c > 0).map((r, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '3px 0',
            color: r.color,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 4, height: 4, borderRadius: '50%', background: r.color }} />
              <span>{r.label}</span>
            </div>
            <span className="mono" style={{ fontWeight: 700 }}>{r.c}</span>
          </div>
        ))}
        {[data.visa_blocked, data.gate_blocked, data.below_threshold, data.optimization_failed, data.failed].every(v => !v || v === 0) && (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 4 }}>No drop-offs recorded</div>
        )}
      </div>
    </div>
  );
}

function Shimmer({ lines = 3 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="shimmer" style={{
          height: 20,
          width: `${85 - i * 8}%`,
          opacity: 1 - i * 0.1,
        }} />
      ))}
    </div>
  );
}
