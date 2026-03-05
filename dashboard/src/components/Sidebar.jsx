import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Send, GitBranch, Zap, Activity } from 'lucide-react';

const NAV = [
  { path: '/',             label: 'Dashboard',    icon: LayoutDashboard },
  { path: '/jobs',         label: 'Jobs',         icon: Briefcase },
  { path: '/applications', label: 'Applications', icon: Send },
  { path: '/pipeline',     label: 'Pipeline',     icon: GitBranch },
];

export default function Sidebar({ isLive, lastRefresh, onTrigger, pipelineRunning }) {
  const loc = useLocation();

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      height: '100vh',
      position: 'fixed',
      top: 0,
      left: 0,
      background: 'linear-gradient(180deg, rgba(12,12,20,0.98) 0%, rgba(10,10,18,0.95) 100%)',
      backdropFilter: 'blur(20px)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      zIndex: 100,
      overflow: 'hidden',
    }}>
      {/* Ambient glow inside sidebar */}
      <div style={{
        position: 'absolute',
        top: -60,
        left: -40,
        width: 200,
        height: 200,
        background: 'radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Logo */}
      <div style={{ padding: '22px 20px 18px', borderBottom: '1px solid var(--border)', position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 38,
            height: 38,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #06b6d4, #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 15px rgba(6,182,212,0.3)',
          }}>
            <Zap size={18} color="#fff" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{
              fontSize: 15,
              fontWeight: 800,
              letterSpacing: '-0.02em',
              background: 'linear-gradient(135deg, #f0f0f5, #a0a0b5)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>AutoApply</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: 500 }}>
              COMMAND CENTER
            </div>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div style={{
        padding: '14px 20px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '8px 12px',
          borderRadius: 8,
          background: isLive
            ? 'rgba(52,211,153,0.06)'
            : 'rgba(248,113,113,0.06)',
          border: `1px solid ${isLive ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.12)'}`,
        }}>
          <div className={`status-dot ${isLive ? 'live' : 'offline'}`} />
          <div style={{ flex: 1 }}>
            <div style={{
              fontSize: 12,
              fontWeight: 600,
              color: isLive ? 'var(--green)' : 'var(--red)',
            }}>
              {isLive ? 'API Connected' : 'API Offline'}
            </div>
            {lastRefresh && (
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 1 }}>
                {lastRefresh.toLocaleTimeString()}
              </div>
            )}
          </div>
          <Activity
            size={14}
            color={isLive ? 'var(--green)' : 'var(--red)'}
            style={{ opacity: 0.6 }}
          />
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '16px 12px', flex: 1 }}>
        <div style={{
          fontSize: 10,
          fontWeight: 600,
          color: 'var(--text-muted)',
          letterSpacing: '0.08em',
          padding: '0 10px 10px',
          textTransform: 'uppercase',
        }}>
          Navigation
        </div>
        {NAV.map(n => {
          const active = loc.pathname === n.path || (n.path !== '/' && loc.pathname.startsWith(n.path));
          const Icon = n.icon;
          return (
            <NavLink key={n.path} to={n.path} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '10px 14px',
              borderRadius: 9,
              marginBottom: 3,
              fontSize: 13,
              fontWeight: active ? 600 : 500,
              color: active ? '#fff' : 'var(--text-secondary)',
              background: active
                ? 'linear-gradient(135deg, rgba(6,182,212,0.12), rgba(139,92,246,0.08))'
                : 'transparent',
              border: active
                ? '1px solid rgba(6,182,212,0.15)'
                : '1px solid transparent',
              textDecoration: 'none',
              transition: 'all 0.2s ease',
              position: 'relative',
              overflow: 'hidden',
            }}>
              {active && (
                <div style={{
                  position: 'absolute',
                  left: 0,
                  top: '20%',
                  bottom: '20%',
                  width: 3,
                  borderRadius: '0 3px 3px 0',
                  background: 'linear-gradient(180deg, var(--cyan), var(--purple))',
                }} />
              )}
              <Icon
                size={17}
                strokeWidth={active ? 2.2 : 1.8}
                color={active ? 'var(--cyan)' : 'var(--text-muted)'}
                style={{ transition: 'color 0.2s' }}
              />
              {n.label}
            </NavLink>
          );
        })}
      </nav>

      {/* Pipeline trigger */}
      <div style={{ padding: '16px 16px 20px' }}>
        <button
          onClick={onTrigger}
          disabled={pipelineRunning}
          className="btn"
          style={{
            width: '100%',
            padding: '12px 0',
            justifyContent: 'center',
            borderRadius: 10,
            background: pipelineRunning
              ? 'var(--bg-tertiary)'
              : 'linear-gradient(135deg, #06b6d4, #6366f1)',
            color: '#fff',
            fontSize: 13,
            fontWeight: 700,
            cursor: pipelineRunning ? 'wait' : 'pointer',
            border: 'none',
            boxShadow: pipelineRunning ? 'none' : '0 4px 15px rgba(6,182,212,0.25)',
            transition: 'all 0.3s ease',
            letterSpacing: '0.01em',
          }}
        >
          {pipelineRunning ? (
            <>
              <span style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>Running Pipeline...</span>
            </>
          ) : (
            <>
              <Zap size={14} />
              Run Pipeline
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
