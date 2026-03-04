import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import {
  Card, ScoreBadge, StatusPill, VisaBadge, SourceBadge,
  FilterInput, FilterSelect, EmptyState, getReasonShort, STATUS, VISA, SOURCES,
} from '../components/shared';

export default function Jobs() {
  const [jobs, setJobs] = useState(null);
  const [filters, setFilters] = useState({ status: '', visa: '', search: '', source: '', min_score: '' });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    const params = { page, per_page: 40 };
    if (filters.status) params.status = filters.status;
    if (filters.visa) params.visa = filters.visa;
    if (filters.search) params.search = filters.search;
    if (filters.source) params.source = filters.source;
    if (filters.min_score) params.min_score = filters.min_score;
    const data = await api.listJobs(params);
    setJobs(data);
    setLoading(false);
  }, [filters, page]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  // Reset page when filters change
  const updateFilter = (key, value) => {
    setPage(1);
    setFilters(p => ({ ...p, [key]: value }));
  };

  const data = jobs || { total: 0, page: 1, per_page: 40, jobs: [] };
  const totalPages = Math.ceil(data.total / (data.per_page || 40)) || 1;

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>
          Scraped Jobs
          <span className="mono" style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500, marginLeft: 10 }}>
            {data.total} total
          </span>
        </h1>
        <button onClick={fetchJobs} style={{
          padding: '6px 14px', background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
          borderRadius: 6, color: 'var(--text-secondary)', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit',
        }}>
          ↻ Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <FilterInput placeholder="Search title or company..." value={filters.search}
          onChange={v => updateFilter('search', v)} style={{ minWidth: 230 }} />
        <FilterSelect value={filters.status} onChange={v => updateFilter('status', v)}
          options={[
            { value: '', label: 'All Statuses' },
            ...Object.entries(STATUS).map(([k, v]) => ({ value: k, label: v.label })),
          ]} />
        <FilterSelect value={filters.visa} onChange={v => updateFilter('visa', v)}
          options={[
            { value: '', label: 'All Visa' },
            ...Object.entries(VISA).map(([k, v]) => ({ value: k, label: v.label })),
          ]} />
        <FilterSelect value={filters.source} onChange={v => updateFilter('source', v)}
          options={[
            { value: '', label: 'All Sources' },
            ...Object.entries(SOURCES).map(([k, v]) => ({ value: k, label: v.label })),
          ]} />
        <FilterInput placeholder="Min %" value={filters.min_score}
          onChange={v => updateFilter('min_score', v)} type="number" style={{ width: 72 }} />
      </div>

      {/* Table */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border)',
        borderRadius: 10, overflow: 'hidden',
      }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading jobs...</div>
        ) : data.jobs.length === 0 ? (
          <EmptyState icon="🔍" title="No jobs found" message="Try adjusting your filters or run the pipeline to scrape new jobs." />
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: 'var(--bg-primary)', borderBottom: '1px solid var(--border)' }}>
                {['Score', 'Title', 'Company', 'Location', 'Source', 'Visa', 'Status', 'Reason'].map(h => (
                  <th key={h} style={{
                    padding: '10px 12px', textAlign: 'left', fontSize: 10, fontWeight: 700,
                    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.jobs.map((j, i) => (
                <tr key={j.id} onClick={() => nav(`/jobs/${j.id}`)}
                  style={{
                    borderBottom: '1px solid var(--bg-tertiary)', cursor: 'pointer',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <td style={{ padding: '10px 12px' }}><ScoreBadge score={j.match_score} /></td>
                  <td style={{ padding: '10px 12px', fontWeight: 600, maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {j.title}
                    {j.ats_platform && (
                      <span style={{
                        marginLeft: 6, padding: '1px 5px', background: 'var(--bg-hover)',
                        borderRadius: 3, fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase',
                      }}>{j.ats_platform}</span>
                    )}
                  </td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{j.company}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11 }}>
                    {j.location?.split(',')[0] || '—'}
                    {j.remote && <span style={{ marginLeft: 4, color: 'var(--cyan)' }}>🌐</span>}
                  </td>
                  <td style={{ padding: '10px 12px' }}><SourceBadge source={j.source} /></td>
                  <td style={{ padding: '10px 12px' }}><VisaBadge visa={j.visa_status} /></td>
                  <td style={{ padding: '10px 12px' }}><StatusPill status={j.status} /></td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: 11, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {getReasonShort(j)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data.jobs.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, marginTop: 14 }}>
          <PgBtn disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</PgBtn>
          <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)', padding: '0 6px' }}>
            {page} / {totalPages}
          </span>
          <PgBtn disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</PgBtn>
        </div>
      )}
    </div>
  );
}

function PgBtn({ disabled, onClick, children }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: '6px 14px', background: disabled ? 'var(--bg-primary)' : 'var(--bg-tertiary)',
      border: '1px solid var(--border)', borderRadius: 6,
      color: disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
      fontSize: 12, cursor: disabled ? 'default' : 'pointer', fontFamily: 'inherit',
    }}>
      {children}
    </button>
  );
}
