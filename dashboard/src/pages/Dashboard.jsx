import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import api from '../api';
import { StatCard, Card, ScoreBadge, StatusPill, SourceBadge, STATUS } from '../components/shared';

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

      // Build funnel
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
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Dashboard</h1>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard label="Jobs Scraped" value={s.scraped_today || '—'} color="var(--cyan)" />
        <StatCard label="Applied Today" value={s.today_applications} color="var(--green)" />
        <StatCard label="Total Applied" value={s.total_applications} color="var(--purple)" />
        <StatCard label="Success Rate" value={`${s.success_rate}%`} color="var(--amber)" />
        <StatCard label="Interviews" value={s.total_interviews} color="#ec4899" />
        <StatCard label="Avg ATS Score" value={s.avg_ats_score ? `${s.avg_ats_score}%` : '—'} color="var(--blue)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Pipeline Funnel */}
        <Card title="Pipeline Funnel">
          {funnelData ? <FunnelViz data={funnelData} /> : <Loading />}
        </Card>

        {/* Top Jobs */}
        <Card title="Top Scoring Jobs" action={
          <button onClick={() => nav('/jobs')} style={linkBtnStyle}>View All →</button>
        }>
          {topJobs.length === 0 ? <Loading /> : (
            <div>
              {topJobs.map((j, i) => (
                <div key={j.id} onClick={() => nav(`/jobs/${j.id}`)} style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
                  borderBottom: i < topJobs.length - 1 ? '1px solid var(--border)' : 'none',
                  cursor: 'pointer',
                }}>
                  <ScoreBadge score={j.match_score} size="sm" />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{j.title}</div>
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
            <div style={{ color: 'var(--text-muted)', fontSize: 12, padding: 20, textAlign: 'center' }}>
              No application data yet — run the pipeline to start applying
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={dailyData}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#71717a' }}
                  tickFormatter={d => new Date(d).toLocaleDateString('en', { month: 'short', day: 'numeric' })} />
                <YAxis tick={{ fontSize: 10, fill: '#71717a' }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1c1c21', border: '1px solid #27272a', borderRadius: 6, fontSize: 12 }} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {dailyData.map((_, i) => <Cell key={i} fill="var(--cyan)" fillOpacity={0.7} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Source breakdown */}
        <Card title="Jobs by Source">
          {Object.keys(sourceCounts).length === 0 ? <Loading /> : (
            <div>
              {Object.entries(sourceCounts).sort((a, b) => b[1] - a[1]).map(([src, count], i) => (
                <div key={src} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: i < Object.keys(sourceCounts).length - 1 ? '1px solid var(--border)' : 'none',
                }}>
                  <SourceBadge source={src} />
                  <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{count}</div>
                </div>
              ))}
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
    { label: 'Total Scraped', value: total, color: 'var(--text-muted)' },
    { label: 'Visa Passed', value: visaPass, color: 'var(--cyan)' },
    { label: 'Gate Passed', value: gatePass, color: 'var(--blue)' },
    { label: 'Score Passed', value: scorePass, color: 'var(--purple)' },
    { label: 'Applied', value: applied, color: 'var(--green)' },
  ];

  return (
    <div>
      {stages.map((st, i) => {
        const pct = Math.max((st.value / total) * 100, 2);
        return (
          <div key={i} style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>
              <span>{st.label}</span>
              <span className="mono" style={{ color: st.color, fontWeight: 700 }}>{st.value}</span>
            </div>
            <div style={{ height: 20, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                width: `${pct}%`, height: '100%', borderRadius: 4,
                background: `linear-gradient(90deg, ${st.color}, ${st.color}88)`,
                transition: 'width 0.6s ease',
              }} />
            </div>
          </div>
        );
      })}

      {/* Drop-off breakdown */}
      <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--bg-primary)', borderRadius: 6, fontSize: 11 }}>
        <div style={{ color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>Drop-off Points</div>
        {[
          { label: 'Visa Blocked', c: data.visa_blocked, color: 'var(--red)' },
          { label: 'Gate Blocked', c: data.gate_blocked, color: '#f97316' },
          { label: 'Below Threshold', c: data.below_threshold, color: '#ec4899' },
          { label: 'Opt. Failed', c: data.optimization_failed, color: 'var(--red)' },
          { label: 'Apply Failed', c: data.failed, color: 'var(--red)' },
        ].filter(r => r.c > 0).map((r, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0', color: r.color }}>
            <span>{r.label}</span>
            <span className="mono" style={{ fontWeight: 700 }}>{r.c}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Loading() {
  return <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>Loading...</div>;
}

const linkBtnStyle = {
  background: 'none', border: '1px solid var(--border)', borderRadius: 5,
  padding: '3px 10px', fontSize: 11, color: 'var(--cyan)', cursor: 'pointer', fontFamily: 'inherit',
};
