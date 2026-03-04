import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';

const NAV = [
  { path: '/',             label: 'Dashboard',    icon: '◈' },
  { path: '/jobs',         label: 'Jobs',         icon: '◉' },
  { path: '/applications', label: 'Applications', icon: '◎' },
  { path: '/pipeline',     label: 'Pipeline',     icon: '◆' },
];

export default function Sidebar({ isLive, lastRefresh, onTrigger, pipelineRunning }) {
  const loc = useLocation();

  return (
    <aside style={{
      width: 'var(--sidebar-w)', height: '100vh', position: 'fixed', top: 0, left: 0,
      background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 18px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: 'linear-gradient(135deg, var(--cyan), var(--purple))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 900, color: '#fff',
          }}>A</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '-0.01em' }}>AutoApply</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Command Center v2.1</div>
          </div>
        </div>
      </div>

      {/* Status */}
      <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: isLive ? 'var(--green)' : 'var(--red)',
            boxShadow: isLive ? '0 0 6px var(--green)' : 'none',
          }} />
          <span style={{ color: isLive ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
            {isLive ? 'API Connected' : 'API Offline'}
          </span>
        </div>
        {lastRefresh && (
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
            Updated {lastRefresh.toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav style={{ padding: '12px 10px', flex: 1 }}>
        {NAV.map(n => {
          const active = loc.pathname === n.path || (n.path !== '/' && loc.pathname.startsWith(n.path));
          return (
            <NavLink key={n.path} to={n.path} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 12px', borderRadius: 7, marginBottom: 2,
              fontSize: 13, fontWeight: active ? 600 : 500,
              color: active ? 'var(--cyan)' : 'var(--text-secondary)',
              background: active ? 'var(--cyan-bg)' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.15s',
            }}>
              <span style={{ fontSize: 14, opacity: active ? 1 : 0.6 }}>{n.icon}</span>
              {n.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Pipeline trigger */}
      <div style={{ padding: '14px 14px 18px' }}>
        <button onClick={onTrigger} disabled={pipelineRunning} style={{
          width: '100%', padding: '10px 0', border: 'none', borderRadius: 7,
          background: pipelineRunning ? 'var(--bg-hover)' : 'linear-gradient(135deg, var(--cyan-dim), #1d4ed8)',
          color: '#fff', fontSize: 13, fontWeight: 600,
          cursor: pipelineRunning ? 'wait' : 'pointer',
          transition: 'all 0.2s',
        }}>
          {pipelineRunning ? '⏳ Running...' : '▶ Run Pipeline'}
        </button>
      </div>
    </aside>
  );
}
