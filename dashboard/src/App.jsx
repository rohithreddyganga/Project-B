import React, { useState, useEffect, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import api from './api';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Jobs from './pages/Jobs';
import JobDetail from './pages/JobDetail';
import Applications from './pages/Applications';
import Pipeline from './pages/Pipeline';

export default function App() {
  const [stats, setStats] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const refresh = useCallback(async () => {
    const s = await api.overview();
    setStats(s);
    setIsLive(!!s);
    setLastRefresh(new Date());
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    const t = setInterval(refresh, 20000);
    return () => clearInterval(t);
  }, [refresh]);

  const triggerPipeline = async () => {
    setPipelineRunning(true);
    await api.trigger();
    setTimeout(() => { setPipelineRunning(false); refresh(); }, 4000);
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar
        isLive={isLive}
        lastRefresh={lastRefresh}
        onTrigger={triggerPipeline}
        pipelineRunning={pipelineRunning}
      />
      <main style={{ marginLeft: 'var(--sidebar-w)', flex: 1, padding: '24px 28px', maxWidth: 1280 }}>
        <Routes>
          <Route path="/" element={<Dashboard stats={stats} refresh={refresh} />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/pipeline" element={<Pipeline stats={stats} />} />
        </Routes>
      </main>
    </div>
  );
}
