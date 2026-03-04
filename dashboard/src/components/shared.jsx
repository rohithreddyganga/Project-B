import React from 'react';

// ── Status / Visa / Source metadata ────────────────────
export const STATUS = {
  scraped:             { label: 'Scraped',        color: 'var(--text-muted)',  bg: 'var(--bg-hover)' },
  needs_review:        { label: 'Needs Review',   color: 'var(--amber)',       bg: 'var(--amber-bg)' },
  visa_blocked:        { label: 'Visa Blocked',   color: 'var(--red)',         bg: 'var(--red-bg)' },
  visa_unclear:        { label: 'Visa Unclear',   color: 'var(--amber)',       bg: 'var(--amber-bg)' },
  gate_blocked:        { label: 'Gate Blocked',   color: '#f97316',            bg: 'rgba(249,115,22,0.08)' },
  scoring:             { label: 'Scoring',        color: 'var(--purple)',      bg: 'var(--purple-bg)' },
  below_threshold:     { label: 'Below Threshold',color: '#ec4899',            bg: 'rgba(236,72,153,0.08)' },
  queued:              { label: 'Queued',          color: 'var(--cyan)',        bg: 'var(--cyan-bg)' },
  optimizing:          { label: 'Optimizing',      color: 'var(--purple)',      bg: 'var(--purple-bg)' },
  optimization_failed: { label: 'Opt. Failed',    color: 'var(--red)',         bg: 'var(--red-bg)' },
  applying:            { label: 'Applying',        color: 'var(--blue)',        bg: 'var(--blue-bg)' },
  submitted:           { label: 'Applied',         color: 'var(--green)',       bg: 'var(--green-bg)' },
  failed:              { label: 'Failed',          color: 'var(--red)',         bg: 'var(--red-bg)' },
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
  const sz = size === 'sm' ? { p: '1px 6px', fs: 11 } : { p: '2px 8px', fs: 12 };
  return (
    <span className="mono" style={{
      display: 'inline-block', padding: sz.p, fontSize: sz.fs,
      fontWeight: 700, color, background: `${color}12`,
      border: `1px solid ${color}30`, borderRadius: 4,
    }}>
      {s}%
    </span>
  );
}

// ── Status Pill ────────────────────────────────────────
export function StatusPill({ status }) {
  const m = STATUS[status] || { label: status || '—', color: 'var(--text-muted)', bg: 'var(--bg-hover)' };
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', fontSize: 11,
      fontWeight: 600, color: m.color, background: m.bg,
      borderRadius: 4, whiteSpace: 'nowrap',
    }}>
      {m.label}
    </span>
  );
}

// ── Visa Badge ─────────────────────────────────────────
export function VisaBadge({ visa }) {
  const m = VISA[visa] || { label: visa || '—', color: 'var(--text-muted)' };
  return <span style={{ fontSize: 11, fontWeight: 600, color: m.color }}>{m.label}</span>;
}

// ── Source Badge ───────────────────────────────────────
export function SourceBadge({ source }) {
  const m = SOURCES[source] || { label: source, color: 'var(--text-muted)' };
  return (
    <span style={{
      padding: '2px 6px', fontSize: 10, fontWeight: 600,
      color: m.color, background: `${m.color}15`, borderRadius: 3,
    }}>
      {m.label}
    </span>
  );
}

// ── Card wrapper ───────────────────────────────────────
export function Card({ title, children, action, style }) {
  return (
    <div className="fade-in" style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '18px 20px', ...style,
    }}>
      {(title || action) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          {title && <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{title}</h3>}
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// ── Stat Card ──────────────────────────────────────────
export function StatCard({ label, value, sub, color = 'var(--cyan)' }) {
  return (
    <div style={{
      background: 'var(--bg-secondary)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '16px 18px', position: 'relative', overflow: 'hidden',
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${color}, transparent)` }} />
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      <div className="mono" style={{ fontSize: 28, fontWeight: 800, color, letterSpacing: '-0.03em' }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Filter Input ───────────────────────────────────────
export function FilterInput({ placeholder, value, onChange, style, type = 'text' }) {
  return (
    <input type={type} placeholder={placeholder} value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        padding: '7px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border)',
        borderRadius: 6, color: 'var(--text-primary)', fontSize: 13, outline: 'none', ...style,
      }}
    />
  );
}

// ── Filter Select ──────────────────────────────────────
export function FilterSelect({ value, onChange, options }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{
        padding: '7px 12px', background: 'var(--bg-primary)', border: '1px solid var(--border)',
        borderRadius: 6, color: 'var(--text-primary)', fontSize: 13, outline: 'none', cursor: 'pointer',
      }}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ── Empty State ────────────────────────────────────────
export function EmptyState({ icon = '📭', title, message }) {
  return (
    <div style={{ padding: 48, textAlign: 'center', color: 'var(--text-muted)' }}>
      <div style={{ fontSize: 48, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)' }}>{title}</div>
      {message && <div style={{ fontSize: 13, marginTop: 8, lineHeight: 1.6, maxWidth: 420, margin: '8px auto 0' }}>{message}</div>}
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
