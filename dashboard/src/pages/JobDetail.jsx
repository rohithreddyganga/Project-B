import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import {
  Card, ScoreBadge, StatusPill, VisaBadge, SourceBadge,
  getReasonDetailed, STATUS, VISA,
} from '../components/shared';

export default function JobDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const data = await api.getJob(id);
      setJob(data);
      setLoading(false);
    })();
  }, [id]);

  if (loading) return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Loading...</div>;
  if (!job || job.error) return <div style={{ padding: 40, color: 'var(--red)' }}>Job not found</div>;

  const salary = job.salary_min
    ? `$${Math.round(job.salary_min / 1000)}k${job.salary_max ? ` – $${Math.round(job.salary_max / 1000)}k` : ''}`
    : '—';

  return (
    <div className="fade-in">
      {/* Back button */}
      <button onClick={() => nav('/jobs')} style={{
        background: 'none', border: 'none', color: 'var(--cyan)', fontSize: 13,
        cursor: 'pointer', fontFamily: 'inherit', marginBottom: 14, padding: 0,
      }}>
        ← Back to Jobs
      </button>

      {/* Header */}
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border)',
        borderRadius: 10, padding: '22px 24px', marginBottom: 16,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 6 }}>{job.title}</h1>
            <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 12 }}>
              {job.company} · {job.location || 'Unknown location'}
              {job.remote && <span style={{ marginLeft: 8, color: 'var(--cyan)', fontSize: 12 }}>🌐 Remote</span>}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <StatusPill status={job.status} />
              <VisaBadge visa={job.visa_status} />
              <SourceBadge source={job.source} />
              {job.ats_platform && (
                <span style={{
                  padding: '2px 8px', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)',
                  background: 'var(--bg-hover)', borderRadius: 4, textTransform: 'uppercase',
                }}>
                  {job.ats_platform}
                </span>
              )}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>ATS Match Score</div>
            <ScoreBadge score={job.match_score} />
          </div>
        </div>
      </div>

      {/* Detail grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>

        {/* Left column — Key details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Info card */}
          <Card title="Job Details">
            <InfoGrid items={[
              { label: 'Company', value: job.company },
              { label: 'Location', value: job.location || '—' },
              { label: 'Salary', value: salary },
              { label: 'Remote', value: job.remote ? 'Yes' : 'No' },
              { label: 'Source', value: job.source },
              { label: 'ATS Platform', value: job.ats_platform || 'Unknown' },
              { label: 'Posted', value: job.posted_date ? new Date(job.posted_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '—' },
              { label: 'Tier', value: job.tier || 'Not classified' },
            ]} />
          </Card>

          {/* Apply URL */}
          <Card title="Job URL">
            <div style={{
              padding: '10px 14px', background: 'var(--bg-primary)', borderRadius: 6,
              fontSize: 12, wordBreak: 'break-all',
            }}>
              <a href={job.apply_url} target="_blank" rel="noopener noreferrer"
                style={{ color: 'var(--cyan)' }}>
                {job.apply_url}
              </a>
            </div>
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer" style={{
              display: 'inline-block', marginTop: 10, padding: '8px 18px',
              background: 'linear-gradient(135deg, var(--cyan-dim), #1d4ed8)',
              borderRadius: 6, color: '#fff', fontSize: 12, fontWeight: 600,
              textDecoration: 'none',
            }}>
              Open Job Posting →
            </a>
          </Card>
        </div>

        {/* Right column — Pipeline reasoning */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Pipeline Decision */}
          <Card title="Pipeline Decision">
            <div style={{
              padding: '14px 16px', borderRadius: 8,
              background: STATUS[job.status]?.bg || 'var(--bg-primary)',
              border: `1px solid ${STATUS[job.status]?.color || 'var(--border)'}30`,
            }}>
              <div style={{
                fontSize: 12, fontWeight: 700, marginBottom: 8,
                color: STATUS[job.status]?.color || 'var(--text-muted)',
              }}>
                Current Status: {STATUS[job.status]?.label || job.status}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-primary)', lineHeight: 1.7 }}>
                {getReasonDetailed(job)}
              </div>
              {job.status_reason && (
                <div style={{
                  marginTop: 10, padding: '8px 10px', background: 'var(--bg-primary)',
                  borderRadius: 4, fontSize: 11, color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                }}>
                  Engine note: {job.status_reason}
                </div>
              )}
            </div>
          </Card>

          {/* Visa Analysis */}
          <Card title="Visa / Sponsorship Analysis">
            <div style={{
              padding: '14px 16px', borderRadius: 8,
              background: VISA[job.visa_status]?.color ? `${VISA[job.visa_status].color}08` : 'var(--bg-primary)',
              border: `1px solid ${VISA[job.visa_status]?.color || 'var(--border)'}30`,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{
                  fontSize: 16,
                  color: job.visa_status === 'ok' ? 'var(--green)' :
                         job.visa_status === 'blocked' ? 'var(--red)' :
                         job.visa_status === 'unclear' ? 'var(--amber)' : 'var(--text-muted)',
                }}>
                  {job.visa_status === 'ok' ? '✅' : job.visa_status === 'blocked' ? '🚫' : job.visa_status === 'unclear' ? '❓' : '⏳'}
                </span>
                <span style={{
                  fontSize: 13, fontWeight: 700,
                  color: VISA[job.visa_status]?.color || 'var(--text-muted)',
                }}>
                  {VISA[job.visa_status]?.label || 'Unchecked'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {job.visa_reason || getVisaExplanation(job.visa_status)}
              </div>
            </div>
          </Card>

          {/* Scoring Breakdown */}
          {job.match_score != null && (
            <Card title="Score Breakdown">
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 10 }}>
                The ATS match score is computed from three weighted components:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <ScoreBar label="Keyword Match" weight="45%" color="var(--cyan)" />
                <ScoreBar label="Cosine Similarity" weight="30%" color="var(--purple)" />
                <ScoreBar label="LLM Semantic Fit" weight="25%" color="var(--green)" />
              </div>
              <div className="mono" style={{
                marginTop: 10, padding: '8px 12px', background: 'var(--bg-primary)',
                borderRadius: 4, fontSize: 12, textAlign: 'center',
              }}>
                Combined Score: <span style={{ fontWeight: 800, color: 'var(--cyan)' }}>{job.match_score?.toFixed(1)}%</span>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Job Description — full width */}
      {job.jd_text && (
        <Card title="Job Description" style={{ marginBottom: 16 }}>
          <div style={{
            padding: '14px 16px', background: 'var(--bg-primary)', borderRadius: 8,
            fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.8,
            maxHeight: 500, overflow: 'auto', whiteSpace: 'pre-wrap',
          }}>
            {job.jd_text}
          </div>
        </Card>
      )}
    </div>
  );
}

function InfoGrid({ items }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
      {items.map((item, i) => (
        <div key={i} style={{ padding: '8px 10px', background: 'var(--bg-primary)', borderRadius: 6 }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{item.label}</div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}

function ScoreBar({ label, weight, color }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 10px', background: 'var(--bg-primary)', borderRadius: 4,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
      <span style={{ fontSize: 12, flex: 1 }}>{label}</span>
      <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{weight}</span>
    </div>
  );
}

function getVisaExplanation(status) {
  switch (status) {
    case 'ok':
      return 'Job description explicitly mentions visa sponsorship, OPT/CPT welcome, or similar positive signals. Safe to apply.';
    case 'blocked':
      return 'Job description contains disqualifying signals: "no sponsorship", "US citizens only", "security clearance required", "ITAR", or similar restrictions. Automatically skipped.';
    case 'unclear':
      return 'No explicit sponsorship language found (neither positive nor negative). The company may or may not sponsor. Check h1bdata.info for their sponsorship history. Flagged for manual review.';
    case 'unchecked':
      return 'Visa filter has not yet processed this job. It will be checked on the next pipeline run.';
    default:
      return 'Unknown visa status.';
  }
}
