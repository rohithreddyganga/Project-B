import React, { useState, useEffect } from 'react';
import { List, Columns } from 'lucide-react';
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
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
      }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 4 }}>
            Applications
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Track submitted applications and interview progress
          </p>
        </div>
        <div style={{
          display: 'flex',
          gap: 2,
          background: 'var(--bg-tertiary)',
          borderRadius: 8,
          padding: 3,
          border: '1px solid var(--border)',
        }}>
          <TabBtn active={tab === 'list'} onClick={() => setTab('list')}>
            <List size={13} /> List
          </TabBtn>
          <TabBtn active={tab === 'kanban'} onClick={() => setTab('kanban')}>
            <Columns size={13} /> Kanban
          </TabBtn>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 50, textAlign: 'center', color: 'var(--text-muted)' }}>
          <div className="shimmer" style={{ width: 200, height: 14, margin: '0 auto 12px' }} />
          <div style={{ fontSize: 13 }}>Loading applications...</div>
        </div>
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
    <div className="glass-card" style={{ overflow: 'hidden', padding: 0 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{
            background: 'var(--bg-primary)',
            borderBottom: '1px solid var(--border)',
          }}>
            {['Company', 'Role', 'Initial Score', 'Optimized Score', 'Iterations', 'Status', 'Stage', 'Applied', 'Confirmation'].map(h => (
              <th key={h} style={{
                padding: '11px 14px',
                textAlign: 'left',
                fontSize: 10,
                fontWeight: 700,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={a.id} className="hoverable" style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '11px 14px', fontWeight: 600 }}>{a.company}</td>
              <td style={{
                padding: '11px 14px',
                color: 'var(--text-secondary)',
                maxWidth: 220,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>{a.role}</td>
              <td style={{ padding: '11px 14px' }}>
                <ScoreBadge score={a.match_score} size="sm" />
              </td>
              <td style={{ padding: '11px 14px' }}>
                <ScoreBadge score={a.ats_score} size="sm" />
                {a.match_score && a.ats_score && a.ats_score > a.match_score && (
                  <span className="mono" style={{ marginLeft: 4, fontSize: 10, color: 'var(--green)', fontWeight: 700 }}>
                    +{(a.ats_score - a.match_score).toFixed(0)}
                  </span>
                )}
              </td>
              <td style={{ padding: '11px 14px' }}>
                <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {a.optimization_iterations || 0}x
                </span>
              </td>
              <td style={{ padding: '11px 14px' }}><StatusPill status={a.status} /></td>
              <td style={{ padding: '11px 14px' }}><StageBadge stage={a.interview_stage} /></td>
              <td style={{ padding: '11px 14px', color: 'var(--text-muted)', fontSize: 11 }}>
                {a.applied_date ? new Date(a.applied_date).toLocaleDateString() : '—'}
              </td>
              <td style={{
                padding: '11px 14px',
                color: 'var(--text-muted)',
                fontSize: 11,
                maxWidth: 120,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}>
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
      gridTemplateColumns: `repeat(${INTERVIEW_STAGES.length}, minmax(155px, 1fr))`,
      gap: 10,
      overflowX: 'auto',
      paddingBottom: 4,
    }}>
      {INTERVIEW_STAGES.map(st => {
        const items = stages[st.key] || [];
        return (
          <div key={st.key} className="glass-card" style={{
            padding: 12,
            minHeight: 220,
          }}>
            <div style={{
              fontSize: 10,
              fontWeight: 700,
              color: st.color,
              marginBottom: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingBottom: 8,
              borderBottom: `2px solid ${st.color}25`,
            }}>
              <span>{st.label}</span>
              <span className="mono" style={{
                padding: '2px 6px',
                background: `${st.color}10`,
                borderRadius: 10,
                fontSize: 10,
              }}>
                {items.length}
              </span>
            </div>
            {items.length === 0 ? (
              <div style={{
                fontSize: 10,
                color: 'var(--text-muted)',
                textAlign: 'center',
                padding: 20,
                opacity: 0.6,
              }}>
                No apps
              </div>
            ) : items.map((a, i) => (
              <div key={i} style={{
                padding: '9px 11px',
                background: 'var(--bg-primary)',
                borderRadius: 8,
                marginBottom: 6,
                border: '1px solid var(--border)',
                transition: 'border-color 0.2s, transform 0.15s',
                cursor: 'default',
              }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = `${st.color}30`;
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 3 }}>{a.company}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', lineHeight: 1.4 }}>{a.role}</div>
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
    <span className="badge" style={{
      color: meta.color,
      background: `${meta.color}10`,
      border: `1px solid ${meta.color}18`,
      fontSize: 10,
    }}>
      {meta.label}
    </span>
  );
}

function TabBtn({ active, onClick, children }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex',
      alignItems: 'center',
      gap: 5,
      padding: '6px 14px',
      fontSize: 12,
      fontWeight: 600,
      background: active ? 'var(--bg-elevated)' : 'transparent',
      border: 'none',
      borderRadius: 6,
      color: active ? 'var(--text-primary)' : 'var(--text-muted)',
      cursor: 'pointer',
      fontFamily: 'inherit',
      transition: 'all 0.15s',
    }}>
      {children}
    </button>
  );
}
