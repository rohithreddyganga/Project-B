import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ExternalLink, MapPin, Building2, DollarSign, Globe, Calendar, Tag, Shield, CheckCircle2, XCircle, AlertCircle, Clock } from 'lucide-react';
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

  if (loading) return (
    <div style={{ padding: 60, textAlign: 'center' }}>
      <div className="shimmer" style={{ width: 240, height: 16, margin: '0 auto 12px' }} />
      <div className="shimmer" style={{ width: 180, height: 12, margin: '0 auto' }} />
    </div>
  );
  if (!job || job.error) return (
    <div style={{ padding: 60, textAlign: 'center', color: 'var(--red)' }}>
      <XCircle size={32} style={{ marginBottom: 8 }} />
      <div style={{ fontSize: 15, fontWeight: 600 }}>Job not found</div>
    </div>
  );

  const salary = job.salary_min
    ? `$${Math.round(job.salary_min / 1000)}k${job.salary_max ? ` – $${Math.round(job.salary_max / 1000)}k` : ''}`
    : '—';

  const visaIcon = job.visa_status === 'ok' ? CheckCircle2
    : job.visa_status === 'blocked' ? XCircle
    : job.visa_status === 'unclear' ? AlertCircle : Clock;
  const VisaIcon = visaIcon;

  return (
    <div className="fade-in">
      {/* Back button */}
      <button onClick={() => nav('/jobs')} className="btn btn-ghost" style={{
        marginBottom: 18,
        padding: '6px 14px',
      }}>
        <ArrowLeft size={14} />
        Back to Jobs
      </button>

      {/* Header */}
      <div className="glass-card" style={{
        padding: '24px 28px',
        marginBottom: 18,
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Gradient accent */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          background: 'linear-gradient(90deg, var(--cyan), var(--purple), var(--green))',
        }} />
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}>
          <div style={{ flex: 1 }}>
            <h1 style={{
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: '-0.02em',
              marginBottom: 8,
            }}>
              {job.title}
            </h1>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              fontSize: 13,
              color: 'var(--text-secondary)',
              marginBottom: 14,
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Building2 size={13} color="var(--text-muted)" />
                {job.company}
              </span>
              <span style={{ color: 'var(--border-light)' }}>|</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <MapPin size={13} color="var(--text-muted)" />
                {job.location || 'Unknown'}
              </span>
              {job.remote && (
                <>
                  <span style={{ color: 'var(--border-light)' }}>|</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--cyan)' }}>
                    <Globe size={13} />
                    Remote
                  </span>
                </>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <StatusPill status={job.status} />
              <VisaBadge visa={job.visa_status} />
              <SourceBadge source={job.source} />
              {job.ats_platform && (
                <span style={{
                  padding: '3px 10px',
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                  background: 'var(--bg-hover)',
                  borderRadius: 20,
                  textTransform: 'uppercase',
                  letterSpacing: '0.02em',
                }}>
                  {job.ats_platform}
                </span>
              )}
            </div>
          </div>
          <div style={{
            textAlign: 'right',
            padding: '12px 16px',
            background: 'var(--bg-primary)',
            borderRadius: 12,
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              ATS Match
            </div>
            <ScoreBadge score={job.match_score} size="lg" />
          </div>
        </div>
      </div>

      {/* Detail grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 18 }}>

        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Card title="Job Details">
            <InfoGrid items={[
              { label: 'Company', value: job.company, icon: Building2 },
              { label: 'Location', value: job.location || '—', icon: MapPin },
              { label: 'Salary', value: salary, icon: DollarSign },
              { label: 'Remote', value: job.remote ? 'Yes' : 'No', icon: Globe },
              { label: 'Source', value: job.source },
              { label: 'ATS Platform', value: job.ats_platform || 'Unknown' },
              { label: 'Posted', value: job.posted_date ? new Date(job.posted_date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '—', icon: Calendar },
              { label: 'Tier', value: job.tier || 'Not classified', icon: Tag },
            ]} />
          </Card>

          <Card title="Job URL">
            <div style={{
              padding: '12px 16px',
              background: 'var(--bg-primary)',
              borderRadius: 8,
              border: '1px solid var(--border)',
              fontSize: 12,
              wordBreak: 'break-all',
              marginBottom: 12,
            }}>
              <a href={job.apply_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--cyan)' }}>
                {job.apply_url}
              </a>
            </div>
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer"
              className="btn btn-primary" style={{ textDecoration: 'none' }}>
              <ExternalLink size={14} />
              Open Job Posting
            </a>
          </Card>
        </div>

        {/* Right column — Pipeline reasoning */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <Card title="Pipeline Decision">
            <div style={{
              padding: '16px 18px',
              borderRadius: 10,
              background: STATUS[job.status]?.bg || 'var(--bg-primary)',
              border: `1px solid ${STATUS[job.status]?.color || 'var(--border)'}18`,
            }}>
              <div style={{
                fontSize: 12,
                fontWeight: 700,
                marginBottom: 10,
                color: STATUS[job.status]?.color || 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}>
                <span style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: STATUS[job.status]?.color || 'var(--text-muted)',
                }} />
                Current Status: {STATUS[job.status]?.label || job.status}
              </div>
              <div style={{
                fontSize: 12,
                color: 'var(--text-primary)',
                lineHeight: 1.8,
              }}>
                {getReasonDetailed(job)}
              </div>
              {job.status_reason && (
                <div style={{
                  marginTop: 12,
                  padding: '10px 12px',
                  background: 'var(--bg-primary)',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  fontSize: 11,
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                }}>
                  Engine note: {job.status_reason}
                </div>
              )}
            </div>
          </Card>

          <Card title="Visa / Sponsorship Analysis">
            <div style={{
              padding: '16px 18px',
              borderRadius: 10,
              background: VISA[job.visa_status]?.color ? `${VISA[job.visa_status].color}06` : 'var(--bg-primary)',
              border: `1px solid ${VISA[job.visa_status]?.color || 'var(--border)'}18`,
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 10,
              }}>
                <VisaIcon
                  size={18}
                  color={
                    job.visa_status === 'ok' ? 'var(--green)' :
                    job.visa_status === 'blocked' ? 'var(--red)' :
                    job.visa_status === 'unclear' ? 'var(--amber)' : 'var(--text-muted)'
                  }
                />
                <span style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: VISA[job.visa_status]?.color || 'var(--text-muted)',
                }}>
                  {VISA[job.visa_status]?.label || 'Unchecked'}
                </span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                {job.visa_reason || getVisaExplanation(job.visa_status)}
              </div>
            </div>
          </Card>

          {job.match_score != null && (
            <Card title="Score Breakdown">
              <div style={{
                fontSize: 12,
                color: 'var(--text-secondary)',
                lineHeight: 1.7,
                marginBottom: 12,
              }}>
                The ATS match score is computed from three weighted components:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <ScoreBar label="Keyword Match" weight="45%" color="var(--cyan)" />
                <ScoreBar label="Cosine Similarity" weight="30%" color="var(--purple)" />
                <ScoreBar label="LLM Semantic Fit" weight="25%" color="var(--green)" />
              </div>
              <div className="mono" style={{
                marginTop: 12,
                padding: '10px 14px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                fontSize: 13,
                textAlign: 'center',
              }}>
                Combined Score: <span style={{ fontWeight: 800, color: 'var(--cyan)' }}>{job.match_score?.toFixed(1)}%</span>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Job Description */}
      {job.jd_text && (
        <Card title="Job Description" style={{ marginBottom: 18 }}>
          <div style={{
            padding: '16px 18px',
            background: 'var(--bg-primary)',
            borderRadius: 10,
            border: '1px solid var(--border)',
            fontSize: 13,
            color: 'var(--text-secondary)',
            lineHeight: 1.9,
            maxHeight: 500,
            overflow: 'auto',
            whiteSpace: 'pre-wrap',
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
        <div key={i} style={{
          padding: '10px 12px',
          background: 'var(--bg-primary)',
          borderRadius: 8,
          border: '1px solid var(--border)',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 10,
            color: 'var(--text-muted)',
            marginBottom: 3,
          }}>
            {item.icon && <item.icon size={10} />}
            {item.label}
          </div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>{item.value}</div>
        </div>
      ))}
    </div>
  );
}

function ScoreBar({ label, weight, color }) {
  const pct = parseInt(weight);
  return (
    <div style={{
      padding: '8px 12px',
      background: 'var(--bg-primary)',
      borderRadius: 8,
      border: '1px solid var(--border)',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: 2, background: color, flexShrink: 0 }} />
          <span style={{ fontSize: 12 }}>{label}</span>
        </div>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>{weight}</span>
      </div>
      <div style={{
        height: 4,
        borderRadius: 10,
        background: 'var(--bg-tertiary)',
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          borderRadius: 10,
          background: `linear-gradient(90deg, ${color}, ${color}88)`,
          transition: 'width 0.5s ease',
        }} />
      </div>
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
