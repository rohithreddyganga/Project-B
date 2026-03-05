import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, ChevronLeft, ChevronRight, Globe } from 'lucide-react';
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

  const updateFilter = (key, value) => {
    setPage(1);
    setFilters(p => ({ ...p, [key]: value }));
  };

  const data = jobs || { total: 0, page: 1, per_page: 40, jobs: [] };
  const totalPages = Math.ceil(data.total / (data.per_page || 40)) || 1;

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
            Scraped Jobs
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            <span className="mono" style={{ color: 'var(--cyan)', fontWeight: 600 }}>{data.total}</span> jobs across all sources
          </p>
        </div>
        <button onClick={fetchJobs} className="btn btn-ghost">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{
        display: 'flex',
        gap: 8,
        marginBottom: 16,
        flexWrap: 'wrap',
        alignItems: 'center',
        padding: '14px 16px',
        background: 'var(--bg-secondary)',
        borderRadius: 12,
        border: '1px solid var(--border)',
      }}>
        <FilterInput
          placeholder="Search title or company..."
          value={filters.search}
          onChange={v => updateFilter('search', v)}
          style={{ minWidth: 250, flex: 1 }}
        />
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
        <FilterInput
          placeholder="Min %"
          value={filters.min_score}
          onChange={v => updateFilter('min_score', v)}
          type="number"
          style={{ width: 80 }}
        />
      </div>

      {/* Table */}
      <div className="glass-card" style={{
        overflow: 'hidden',
        padding: 0,
      }}>
        {loading ? (
          <div style={{ padding: 50, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div className="shimmer" style={{ width: 200, height: 14, margin: '0 auto 12px' }} />
            <div style={{ fontSize: 13 }}>Loading jobs...</div>
          </div>
        ) : data.jobs.length === 0 ? (
          <EmptyState icon="🔍" title="No jobs found" message="Try adjusting your filters or run the pipeline to scrape new jobs." />
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{
                background: 'var(--bg-primary)',
                borderBottom: '1px solid var(--border)',
              }}>
                {['Score', 'Title', 'Company', 'Location', 'Source', 'Visa', 'Status', 'Reason'].map(h => (
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
              {data.jobs.map((j) => (
                <tr
                  key={j.id}
                  onClick={() => nav(`/jobs/${j.id}`)}
                  className="hoverable"
                  style={{
                    borderBottom: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                >
                  <td style={{ padding: '11px 14px' }}><ScoreBadge score={j.match_score} /></td>
                  <td style={{
                    padding: '11px 14px',
                    fontWeight: 600,
                    maxWidth: 260,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {j.title}
                    {j.ats_platform && (
                      <span style={{
                        marginLeft: 6,
                        padding: '1px 6px',
                        background: 'var(--bg-hover)',
                        borderRadius: 4,
                        fontSize: 9,
                        color: 'var(--text-muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.02em',
                      }}>{j.ats_platform}</span>
                    )}
                  </td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-secondary)' }}>{j.company}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)', fontSize: 11 }}>
                    {j.location?.split(',')[0] || '—'}
                    {j.remote && (
                      <Globe size={11} color="var(--cyan)" style={{ marginLeft: 4, verticalAlign: 'middle' }} />
                    )}
                  </td>
                  <td style={{ padding: '11px 14px' }}><SourceBadge source={j.source} /></td>
                  <td style={{ padding: '11px 14px' }}><VisaBadge visa={j.visa_status} /></td>
                  <td style={{ padding: '11px 14px' }}><StatusPill status={j.status} /></td>
                  <td style={{
                    padding: '11px 14px',
                    color: 'var(--text-muted)',
                    fontSize: 11,
                    maxWidth: 200,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
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
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: 10,
          marginTop: 16,
        }}>
          <button
            className="btn btn-ghost"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            style={{ padding: '6px 12px', opacity: page <= 1 ? 0.4 : 1 }}
          >
            <ChevronLeft size={14} /> Prev
          </button>
          <span className="mono" style={{
            fontSize: 12,
            color: 'var(--text-muted)',
            padding: '4px 12px',
            background: 'var(--bg-tertiary)',
            borderRadius: 6,
            border: '1px solid var(--border)',
          }}>
            {page} / {totalPages}
          </span>
          <button
            className="btn btn-ghost"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            style={{ padding: '6px 12px', opacity: page >= totalPages ? 0.4 : 1 }}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
