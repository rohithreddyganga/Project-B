import React from 'react';
import { Search } from 'lucide-react';

// ── Status / Visa / Source metadata ────────────────────
export const STATUS = {
  scraped:             { label: 'Scraped',         color: 'var(--text-muted)',  bg: 'var(--bg-hover)' },
  needs_review:        { label: 'Needs Review',    color: 'var(--amber)',       bg: 'var(--amber-bg)' },
  visa_blocked:        { label: 'Visa Blocked',    color: 'var(--red)',         bg: 'var(--red-bg)' },
  visa_unclear:        { label: 'Visa Unclear',    color: 'var(--amber)',       bg: 'var(--amber-bg)' },
  gate_blocked:        { label: 'Gate Blocked',    color: '#f97316',            bg: 'rgba(249,115,22,0.06)' },
  scoring:             { label: 'Scoring',         color: 'var(--purple)',      bg: 'var(--purple-bg)' },
  below_threshold:     { label: 'Below Threshold', color: '#ec4899',            bg: 'rgba(236,72,153,0.06)' },
  queued:              { label: 'Queued',           color: 'var(--cyan)',        bg: 'var(--cyan-bg)' },
  optimizing:          { label: 'Optimizing',       color: 'var(--purple)',      bg: 'var(--purple-bg)' },
  optimization_failed: { label: 'Opt. Failed',     color: 'var(--red)',         bg: 'var(--red-bg)' },
  applying:            { label: 'Applying',         color: 'var(--blue)',        bg: 'var(--blue-bg)' },
  submitted:           { label: 'Applied',          color: 'var(--green)',       bg: 'var(--green-bg)' },
  failed:              { label: 'Failed',           color: 'var(--red)',         bg: 'var(--red-bg)' },
};

export const VISA = {
  ok:        { label: 'Sponsors',  color: 'var(--green)' },
  blocked:   { label: 'No Visa',   color: 'var(--red)' },
  unclear:   { label: 'Unclear',   color: 'var(--amber)' },
  unchecked: { label: 'Unchecked', color: 'var(--text-muted)' },
};

export const SOURCES = {
  adzuna:       { label: 'Adzuna',       color: '#3b82f6' },
  jsearch:      { label: 'JSearch',      color: '#10b981' },
  remoteok:     { label: 'RemoteOK',     color: '#f59e0b' },
  linkedin_api: { label: 'LinkedIn',     color: '#0a66c2' },
  activejobs:   { label: 'ActiveJobs',   color: '#8b5cf6' },
  jobs_search:  { label: 'JobsSearch',   color: '#ec4899' },
};

// ── Score Badge ────────────────────────────────────────
export function ScoreBadge({ score, size = 'md' }) {
  if (score == null) return <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>—</span>;
  const s = Math.round(score);
  const color = s >= 80 ? 'var(--green)' : s >= 50 ? 'var(--amber)' : s >= 30 ? '#f97316' : 'var(--red)';
  const sz = size === 'sm' ? { p: '2px 8px', fs: 11 } : size === 'lg' ? { p: '4px 14px', fs: 16 } : { p: '3px 10px', fs: 12 };
  return (
    <span className="mono" style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: sz.p,
      fontSize: sz.fs,
      fontWeight: 700,
      color,
      background: `${color}10`,
      border: `1px solid ${color}25`,
      borderRadius: 6,
      letterSpacing: '-0.02em',
    }}>
      {s}%
    </span>
  );
}

// ── Status Pill ────────────────────────────────────────
export function StatusPill({ status }) {
  const m = STATUS[status] || { label: status || '—', color: 'var(--text-muted)', bg: 'var(--bg-hover)' };
  return (
    <span className="badge" style={{
      color: m.color,
      background: m.bg,
      border: `1px solid ${m.color}18`,
      fontSize: 11,
      fontWeight: 600,
    }}>
      <span style={{
        width: 5,
        height: 5,
        borderRadius: '50%',
        background: m.color,
        flexShrink: 0,
      }} />
      {m.label}
    </span>
  );
}

// ── Visa Badge ─────────────────────────────────────────
export function VisaBadge({ visa }) {
  const m = VISA[visa] || { label: visa || '—', color: 'var(--text-muted)' };
  return (
    <span style={{
      fontSize: 11,
      fontWeight: 600,
      color: m.color,
      padding: '2px 8px',
      borderRadius: 20,
      background: `${m.color}10`,
    }}>
      {m.label}
    </span>
  );
}

// ── Source Badge ───────────────────────────────────────
export function SourceBadge({ source }) {
  const m = SOURCES[source] || { label: source, color: 'var(--text-muted)' };
  return (
    <span style={{
      padding: '3px 8px',
      fontSize: 10,
      fontWeight: 600,
      color: m.color,
      background: `${m.color}12`,
      borderRadius: 20,
      letterSpacing: '0.02em',
    }}>
      {m.label}
    </span>
  );
}

// ── Card wrapper ───────────────────────────────────────
export function Card({ title, children, action, style }) {
  return (
    <div className="fade-in glass-card" style={{
      padding: '20px 22px',
      ...style,
    }}>
      {(title || action) && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}>
          {title && (
            <h3 style={{
              fontSize: 12,
              fontWeight: 700,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}>
              {title}
            </h3>
          )}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// ── Stat Card ──────────────────────────────────────────
export function StatCard({ label, value, sub, color = 'var(--cyan)', icon: Icon }) {
  return (
    <div className="glass-card" style={{
      padding: '18px 20px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 2,
        background: `linear-gradient(90deg, ${color}, ${color}00)`,
      }} />
      <div style={{
        position: 'absolute',
        top: -20,
        right: -20,
        width: 80,
        height: 80,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${color}08, transparent)`,
        pointerEvents: 'none',
      }} />
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
        {Icon && <Icon size={15} color={color} style={{ opacity: 0.5 }} />}
      </div>
      <div className="mono" style={{
        fontSize: 28,
        fontWeight: 800,
        color,
        letterSpacing: '-0.04em',
        lineHeight: 1,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>{sub}</div>
      )}
    </div>
  );
}

// ── Filter Input ───────────────────────────────────────
export function FilterInput({ placeholder, value, onChange, style, type = 'text' }) {
  return (
    <div style={{ position: 'relative', ...style }}>
      {type === 'text' && (
        <Search size={14} color="var(--text-muted)" style={{
          position: 'absolute',
          left: 10,
          top: '50%',
          transform: 'translateY(-50%)',
          pointerEvents: 'none',
        }} />
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%',
          padding: type === 'text' ? '8px 12px 8px 32px' : '8px 12px',
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          color: 'var(--text-primary)',
          fontSize: 13,
          outline: 'none',
          transition: 'border-color 0.2s, box-shadow 0.2s',
        }}
        onFocus={e => {
          e.target.style.borderColor = 'var(--border-light)';
          e.target.style.boxShadow = '0 0 0 3px rgba(6,182,212,0.08)';
        }}
        onBlur={e => {
          e.target.style.borderColor = 'var(--border)';
          e.target.style.boxShadow = 'none';
        }}
      />
    </div>
  );
}

// ── Filter Select ──────────────────────────────────────
export function FilterSelect({ value, onChange, options }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        padding: '8px 30px 8px 12px',
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        color: 'var(--text-primary)',
        fontSize: 13,
        outline: 'none',
        cursor: 'pointer',
        appearance: 'none',
        backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b6b80' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
        backgroundPosition: 'right 8px center',
        backgroundRepeat: 'no-repeat',
        backgroundSize: '16px',
        transition: 'border-color 0.2s',
      }}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ── Empty State ────────────────────────────────────────
export function EmptyState({ icon = '📭', title, message }) {
  return (
    <div style={{
      padding: '52px 24px',
      textAlign: 'center',
      color: 'var(--text-muted)',
    }}>
      <div style={{
        fontSize: 48,
        marginBottom: 16,
        filter: 'grayscale(0.2)',
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: 15,
        fontWeight: 700,
        color: 'var(--text-secondary)',
        marginBottom: 6,
      }}>
        {title}
      </div>
      {message && (
        <div style={{
          fontSize: 13,
          lineHeight: 1.7,
          maxWidth: 420,
          margin: '0 auto',
          color: 'var(--text-muted)',
        }}>
          {message}
        </div>
      )}
    </div>
  );
}

// ── Pipeline reason text ───────────────────────────────
export function getReasonShort(job) {
  switch (job.status) {
    case 'visa_blocked':        return 'No visa sponsorship';
    case 'gate_blocked':        return 'Company limit / duplicate';
    case 'below_threshold':     return `Score ${job.match_score?.toFixed(1) || 0}% below threshold`;
    case 'needs_review':        return 'Visa unclear — manual review';
    case 'optimization_failed': return 'Resume optimization failed';
    case 'failed':              return 'Form submission failed';
    case 'submitted':           return 'Successfully applied';
    case 'queued':              return 'Waiting in optimization queue';
    case 'optimizing':          return 'Resume being tailored';
    case 'applying':            return 'Browser filling form...';
    case 'scraped':             return 'Not yet processed';
    default:                    return '—';
  }
}

export function getReasonDetailed(job) {
  switch (job.status) {
    case 'visa_blocked':
      return job.visa_reason || 'Job description contained keywords indicating no visa sponsorship (e.g., "U.S. citizens only", "security clearance required", "no sponsorship"). The visa filter uses regex pattern matching first, then falls back to Claude Haiku for ambiguous cases.';
    case 'below_threshold':
      return `Scored ${job.match_score?.toFixed(1) || 0}% on ATS compatibility (below screening threshold). Score breakdown: (1) TF-IDF cosine similarity between resume and JD, (2) keyword hit-rate for technical skills, (3) Claude Haiku semantic fit assessment. Add more JD-matching keywords to your master resume to improve scores.`;
    case 'needs_review':
      return job.visa_reason || 'The visa filter could not determine sponsorship status. No explicit sponsorship language (neither positive nor negative) was found. Research this company\'s H-1B sponsorship history on h1bdata.info.';
    case 'submitted':
      return 'Processed through all pipeline stages. Resume was optimized for this JD, ATS score exceeded threshold, and browser automation submitted the form.';
    case 'scraped':
      return 'Scraped from job board but not yet processed. Will be filtered, scored, and potentially applied to on the next pipeline run.';
    case 'queued':
      return 'Passed all filters and scoring. Waiting for Claude Sonnet to tailor resume for this specific JD.';
    case 'failed':
      return job.status_reason || 'Browser automation failed. Common causes: CAPTCHA, changed form selectors, page timeout, or unexpected fields.';
    case 'optimization_failed':
      return job.status_reason || 'LaTeX compilation or AI optimization failed during resume tailoring.';
    case 'gate_blocked':
      return job.status_reason || 'Blocked by gate check: either exceeded per-company limit, URL already applied, or daily application cap reached.';
    default:
      return 'No additional information available.';
  }
}
