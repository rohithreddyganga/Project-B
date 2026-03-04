import React, { useState, useEffect } from 'react';
import api from '../api';
import { Card, ScoreBadge, StatusPill, EmptyState } from '../components/shared';

const INTERVIEW_STAGES = [
  { key: 'applied',      label: 'Applied',       color: 'var(--text-muted)' },
  { key: 'assessment',   label: 'Assessment',    color: 'var(--amber)' },
  { key: 'phone_screen', label: 'Phone Screen',  color: 'var(--cyan)' },
  { key: 'technical',    label: 'Technical',      color: 'var(--purple)' },
  { key: 'final_round',  label: 'Final Round',   color: 'var(--blue)' },
  { key: 'offer',        label: 'Offer',          color: 'var(--green)' },
  { key: 'rejected',     label: 'Rejected',       color: 'var(--red)' },
  { key: 'withdrawn',    label: 'Withdrawn',      color: 'var(--text-muted)' },
];

export default function Applications() {
  const [apps, setApps] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [tab, setTab] = useState('list');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [a, p] = await Promise.all([api.listApps(), api.getPipeline()]);
      setApps(a);
      setPipeline(p);
      setLoading(false);
    })();
  }, []);

  const items = apps?.applications || [];

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Applications</h1>
        <div style={{ display: 'flex', gap: 4 }}>
          <TabBtn active={tab === 'list'} onClick={() => setTab('list')}>List View</TabBtn>
          <TabBtn active={tab === 'kanban'} onClick={() => setTab('kanban')}>Kanban</TabBtn>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
      ) : tab === 'list' ? (
        <ApplicationsList items={items} />
      ) : (
        <KanbanBoard pipeline={pipeline} />
      )}
    </div>
  );
}

function ApplicationsList({ items }) {
  if (items.length === 0) {
    return (
      <Card>
        <EmptyState
          icon="📭"
          title="No Applications Yet"
          message="Once the pipeline processes jobs above the scoring threshold, they'll flow through optimization and be applied to automatically. Run the pipeline to get started."
        />
      </Card>
    );
  }

  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border)',
      borderRadius: 10, overflow: 'hidden',
    }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border)' }}>
            {['Company', 'Role', 'Initial Score', 'Optimized Score', 'Iterations', 'Status', 'Stage', 'Applied', 'Confirmation'].map(h => (
              <th key={h} style={{
                padding: '10px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((a, i) => (
            <tr key={a.id} style={{ borderBottom: '1px solid var(--bg-tertiary)' }}>
              <td style={{ padding: '10px 12px', fontWeight: 600 }}>{a.company}</td>
              <td style={{ padding: '10px 12px', color: 'var(--text-secondary)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.role}</td>
              <td style={{ padding: '10px 12px' }}>
                <ScoreBadge score={a.match_score} size="sm" />
              </td>
              <td style={{ padding: '10px 12px' }}>
                <ScoreBadge score={a.ats_score} size="sm" />
                {a.match_score && a.ats_score && a.ats_score > a.match_score && (
                  <span className="mono" style={{ marginLeft: 4, fontSize: 10, color: 'var(--green)' }}>
                    +{(a.ats_score - a.match_score).toFixed(0)}
                  </span>
                )}
              </td>
              <td style={{ padding: '10px 12px' }}>
                <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {a.optimization_iterations || 0}x
                </span>
              </td>
              <td style={{ padding: '10px 12px' }}><StatusPill status={a.status} /></td>
              <td style={{ padding: '10px 12px' }}>
                <StageBadge stage={a.interview_stage} />
              </td>
              <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11 }}>
                {a.applied_date ? new Date(a.applied_date).toLocaleDateString() : '—'}
              </td>
              <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {a.confirmation_number || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KanbanBoard({ pipeline }) {
  const stages = pipeline?.pipeline || {};

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(${INTERVIEW_STAGES.length}, minmax(150px, 1fr))`,
      gap: 10, overflowX: 'auto',
    }}>
      {INTERVIEW_STAGES.map(st => {
        const items = stages[st.key] || [];
        return (
          <div key={st.key} style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 8, padding: 10, minHeight: 200,
          }}>
            <div style={{
              fontSize: 11, fontWeight: 700, color: st.color,
              marginBottom: 10, textTransform: 'uppercase',
              display: 'flex', justifyContent: 'space-between',
            }}>
              <span>{st.label}</span>
              <span className="mono">{items.length}</span>
            </div>
            {items.length === 0 ? (
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>
                No apps
              </div>
            ) : items.map((a, i) => (
              <div key={i} style={{
                padding: '8px 10px', background: 'var(--bg-primary)',
                borderRadius: 6, marginBottom: 6, border: '1px solid var(--border)',
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 2 }}>{a.company}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{a.role}</div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function StageBadge({ stage }) {
  const meta = INTERVIEW_STAGES.find(s => s.key === stage) || { label: stage, color: 'var(--text-muted)' };
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, color: meta.color,
      padding: '2px 6px', background: `${meta.color}12`,
      borderRadius: 3,
    }}>
      {meta.label}
    </span>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 12px', fontSize: 12, fontWeight: 500,
      background: active ? 'var(--cyan-bg)' : 'transparent',
      border: active ? '1px solid var(--cyan-dim)' : '1px solid transparent',
      borderRadius: 5, color: active ? 'var(--cyan)' : 'var(--text-muted)',
      cursor: 'pointer', fontFamily: 'inherit',
    }}>
      {children}
    </button>
  );
}
