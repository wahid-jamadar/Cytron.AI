import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Users, FolderKanban, Cpu, Flag, Scroll,
  ShieldCheck, RefreshCw, Download, ChevronDown, LayoutGrid, ArrowLeft,
  Activity, TrendingUp, DollarSign, UserCheck
} from 'lucide-react';
import cytronLogo from '../assets/Cytron.AI-Logo.png';
import { apiFetch } from '../store/apiClient';
import useAuthStore from '../store/authStore';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend
} from 'recharts';

/* â”€â”€â”€ Shared style helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const S = {
  layout: {
    display: 'grid' as const,
    gridTemplateColumns: '240px 1fr',
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
    background: 'var(--bg)',
    color: 'var(--text)',
    fontFamily: 'var(--font)',
  },
  sidebar: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    height: '100vh',
    overflowY: 'auto' as const,
    background: 'var(--sidebar-bg)',
    borderRight: '1px solid var(--border)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
  },
  workspaceSwitcher: {
    padding: '24px 20px 20px',
    borderBottom: '1px solid var(--border)',
  },
  workspaceLabel: {
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: '0.12em',
    textTransform: 'uppercase' as const,
    color: 'var(--text-dim)',
    marginBottom: 10,
  },
  workspaceBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    padding: '10px 12px',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text)',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  workspaceDropdown: {
    position: 'absolute' as const,
    left: 0,
    right: 0,
    top: 'calc(100% + 4px)',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 12,
    boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
    zIndex: 50,
    overflow: 'hidden',
  },
  workspaceDropdownItemBase: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 10,
    padding: '10px 14px',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
    width: '100%',
    textAlign: 'left' as const,
    border: 'none',
    textDecoration: 'none',
  },
  nav: {
    flexGrow: 1,
    padding: '12px 10px',
  },
  sidebarFooter: {
    padding: '16px 20px',
    borderTop: '1px solid var(--border)',
  },
  exitBtn: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-dim)',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    transition: 'color 0.15s',
    width: '100%',
  },
  main: {
    height: '100vh',
    overflowY: 'auto' as const,
    minWidth: 0,
    background: 'var(--bg)',
  },
  mainInner: {
    padding: '28px 28px',
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 24,
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    boxShadow: '0 2px 8px rgba(0,0,0,0.25)',
  },
  pageHeader: {
    display: 'flex' as const,
    alignItems: 'flex-start' as const,
    justifyContent: 'space-between' as const,
    gap: 16,
    paddingBottom: 20,
    marginBottom: 8,
    borderBottom: '1px solid var(--border)',
  },
  pageTitle: {
    fontSize: 22,
    fontWeight: 800,
    letterSpacing: '-0.02em',
    color: 'var(--text)',
    lineHeight: 1.2,
  },
  pageSubtitle: {
    marginTop: 4,
    fontSize: 12,
    color: 'var(--text-dim)',
    fontWeight: 500,
  },
  kpiGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 18,
  },
  kpiCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '22px 24px',
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 10,
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
    position: 'relative' as const,
    overflow: 'hidden' as const,
  },
  kpiLabel: {
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: 'var(--text-muted)',
  },
  kpiValue: {
    fontSize: 32,
    fontWeight: 800,
    letterSpacing: '-0.02em',
    color: 'var(--text)',
    lineHeight: 1,
  },
  kpiSub: {
    fontSize: 11,
    color: 'var(--text-dim)',
    fontWeight: 500,
  },
  chartsGrid: {
    display: 'grid' as const,
    gridTemplateColumns: '1fr 1fr',
    gap: 18,
  },
  chartCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '22px 24px',
    display: 'flex' as const,
    flexDirection: 'column' as const,
    height: 340,
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
  },
  chartTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: 'var(--text)',
    marginBottom: 16,
  },
  sysCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '22px 24px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
  },
  sysGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 32,
    marginTop: 16,
  },
  sysBarTrack: {
    height: 8,
    width: '100%',
    borderRadius: 8,
    background: 'var(--surface-3)',
    border: '1px solid var(--border)',
    overflow: 'hidden' as const,
    marginTop: 8,
  },
  tableCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    overflow: 'hidden' as const,
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
  },
  tableInner: {
    overflowX: 'auto' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    textAlign: 'left' as const,
    fontSize: 13,
  },
  th: {
    padding: '14px 18px',
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase' as const,
    color: 'var(--text-dim)',
    background: 'var(--surface-2)',
    borderBottom: '1px solid var(--border)',
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '13px 18px',
    color: 'var(--text-muted)',
    verticalAlign: 'middle' as const,
    borderBottom: '1px solid rgba(255,255,255,0.03)',
  },
  refreshBtn: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    padding: 8,
    borderRadius: 10,
    border: '1px solid var(--border)',
    background: 'var(--surface-2)',
    cursor: 'pointer',
    transition: 'all 0.15s',
    color: 'var(--text-muted)',
  },
  exportBtn: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 6,
    padding: '8px 16px',
    background: 'var(--accent)',
    color: '#fff',
    fontSize: 12,
    fontWeight: 700,
    borderRadius: 10,
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.15s',
    boxShadow: '0 2px 8px rgba(139,92,246,0.3)',
  },
  roleSelect: {
    width: '100%',
    fontSize: 12,
    background: 'var(--surface-2)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: '7px 28px 7px 10px',
    color: 'var(--text)',
    cursor: 'pointer',
    fontWeight: 600,
    outline: 'none',
    appearance: 'none' as const,
    WebkitAppearance: 'none' as const,
  },
  agentGrid: {
    display: 'grid' as const,
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 18,
  },
  agentCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '20px',
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 16,
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
  },
  agentRestartBtn: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
    gap: 6,
    padding: '9px',
    borderRadius: 10,
    border: '1px solid var(--border)',
    background: 'var(--surface-2)',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text)',
    cursor: 'pointer',
    transition: 'all 0.15s',
    width: '100%',
  },
  flagGrid: {
    display: 'grid' as const,
    gridTemplateColumns: '1fr 1fr',
    gap: 14,
  },
  flagCard: {
    background: 'var(--surface)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 16,
    padding: '18px 20px',
    display: 'flex' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    gap: 20,
    boxShadow: '0 2px 10px rgba(0,0,0,0.3)',
  },
  errorBanner: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 8,
    padding: '12px 16px',
    background: 'rgba(239,68,68,0.08)',
    border: '1px solid rgba(239,68,68,0.2)',
    borderRadius: 12,
    color: '#f87171',
    fontSize: 13,
  },
};

/* â”€â”€â”€ Status badge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const STATUS_MAP: Record<string, { bg: string; text: string; border: string }> = {
  active:    { bg: 'rgba(16,185,129,0.1)',  text: '#34d399', border: 'rgba(16,185,129,0.25)' },
  suspended: { bg: 'rgba(239,68,68,0.08)',  text: '#f87171', border: 'rgba(239,68,68,0.2)'  },
  completed: { bg: 'rgba(16,185,129,0.1)',  text: '#34d399', border: 'rgba(16,185,129,0.25)' },
  running:   { bg: 'rgba(79,139,255,0.1)',  text: '#60a5fa', border: 'rgba(79,139,255,0.25)' },
  failed:    { bg: 'rgba(239,68,68,0.08)',  text: '#f87171', border: 'rgba(239,68,68,0.2)'  },
  error:     { bg: 'rgba(239,68,68,0.08)',  text: '#f87171', border: 'rgba(239,68,68,0.2)'  },
  success:   { bg: 'rgba(16,185,129,0.1)',  text: '#34d399', border: 'rgba(16,185,129,0.25)' },
  pending:   { bg: 'rgba(245,158,11,0.1)',  text: '#fbbf24', border: 'rgba(245,158,11,0.25)' },
  none:      { bg: 'rgba(100,116,139,0.1)', text: '#94a3b8', border: 'rgba(100,116,139,0.2)' },
};

function StatusBadge({ status }: { status: string }) {
  const s = (status ?? '').toLowerCase();
  const c = STATUS_MAP[s] ?? { bg: 'rgba(100,116,139,0.1)', text: '#94a3b8', border: 'rgba(100,116,139,0.2)' };
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '3px 9px',
      borderRadius: 20,
      fontSize: 10,
      fontWeight: 700,
      letterSpacing: '0.08em',
      textTransform: 'uppercase' as const,
      background: c.bg,
      color: c.text,
      border: `1px solid ${c.border}`,
      whiteSpace: 'nowrap' as const,
    }}>
      {status || 'â€”'}
    </span>
  );
}

/* â”€â”€â”€ Tooltip style â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const tooltipStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  color: 'var(--text)',
  fontSize: 11,
  boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
};

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
export default function AdminPanel() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [metrics,  setMetrics]  = useState<any>(null);
  const [charts,   setCharts]   = useState<any>(null);
  const [users,    setUsers]    = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [agents,   setAgents]   = useState<any[]>([]);
  const [flags,    setFlags]    = useState<any[]>([]);
  const [audits,   setAudits]   = useState<any[]>([]);
  const [error,    setError]    = useState('');
  const [switcherOpen, setSwitcherOpen] = useState(false);

  const { user, startImpersonation } = useAuthStore();
  const navigate = useNavigate();

  const load = async (path: string, setter: (d: any) => void) => {
    try { setter(await apiFetch(path)); } catch {}
  };

  const loadTabContent = () => {
    setError('');
    if (activeTab === 'dashboard') {
      load('/api/admin/dashboard/metrics', setMetrics);
      load('/api/admin/dashboard/charts', setCharts);
    } else if (activeTab === 'users')    load('/api/admin/users',          setUsers);
    else if (activeTab === 'projects')   load('/api/admin/projects',       setProjects);
    else if (activeTab === 'agents')     load('/api/admin/agents/status',  setAgents);
    else if (activeTab === 'flags')      load('/api/admin/feature-flags',  setFlags);
    else if (activeTab === 'audit')      load('/api/admin/audit-logs',     setAudits);
  };

  useEffect(() => { loadTabContent(); }, [activeTab]);

  const handleUserStatusToggle = async (userId: number, currentStatus: string) => {
    const targetStatus = currentStatus === 'active' ? 'suspended' : 'active';
    try { await apiFetch(`/api/admin/users/${userId}/status`, { method: 'PUT', json: { status: targetStatus } }); loadTabContent(); } catch {}
  };

  const handleImpersonate = async (userId: number) => {
    try {
      const data = await apiFetch(`/api/admin/users/${userId}/impersonate`, { method: 'POST' });
      const targetUser = users.find((u) => u.id === userId);
      if (targetUser) {
        startImpersonation({ id: targetUser.id, email: targetUser.email, first_name: targetUser.first_name, last_name: targetUser.last_name, roles: targetUser.roles }, data.access_token);
        window.location.href = '/hub';
      }
    } catch {}
  };

  const handleDeleteUser = async (userId: number) => {
    if (confirm("Are you sure you want to delete this user?")) {
      try { await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' }); loadTabContent(); } catch {}
    }
  };

  const handleRoleChange = async (userId: number, roleName: string) => {
    try { await apiFetch(`/api/admin/users/${userId}/role`, { method: 'PUT', json: { role_name: roleName } }); loadTabContent(); } catch (err: any) { setError(err.message || 'Failed to update role'); }
  };

  const handleFlagToggle = async (flagId: number, currentVal: boolean) => {
    try { await apiFetch(`/api/admin/feature-flags/${flagId}`, { method: 'PUT', json: { is_enabled: !currentVal } }); loadTabContent(); } catch {}
  };

  const handleRestartAgent = async (taskId: number) => {
    try { await apiFetch(`/api/admin/agents/${taskId}/restart`, { method: 'POST' }); loadTabContent(); } catch {}
  };

  const kpiIcons = [UserCheck, Activity, TrendingUp, DollarSign];
  const kpiColors = ['var(--accent)', 'var(--accent-2)', '#10b981', '#f59e0b'];

  const navItems = [
    { id: 'dashboard', label: 'Dashboard',         icon: LayoutDashboard },
    { id: 'users',     label: 'Users',             icon: Users           },
    { id: 'projects',  label: 'Projects',          icon: FolderKanban    },
    { id: 'agents',    label: 'AI Agents Monitor', icon: Cpu             },
    { id: 'flags',     label: 'Feature Flags',     icon: Flag            },
    { id: 'audit',     label: 'Audit Logs',        icon: Scroll          },
  ];

  return (
    <div style={S.layout}>

      {/* â•â• SIDEBAR â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
      <aside style={S.sidebar}>

        {/* Workspace switcher */}
        <div style={S.workspaceSwitcher}>
          <img src={cytronLogo} alt="Cytron.AI" style={{ height: '36px', width: 'auto', marginBottom: '24px', display: 'block' }} className="object-contain" />
          <p style={S.workspaceLabel}>Current Workspace</p>
          <div style={{ position: 'relative' }}>
            <button onClick={() => setSwitcherOpen(!switcherOpen)} style={S.workspaceBtn}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ShieldCheck style={{ width: 15, height: 15, color: 'var(--accent)', flexShrink: 0 }} />
                Admin Console
              </span>
              <ChevronDown style={{
                width: 13, height: 13, color: 'var(--text-dim)',
                transform: switcherOpen ? 'rotate(180deg)' : 'none',
                transition: 'transform 0.2s',
              }} />
            </button>

            {switcherOpen && (
              <div style={S.workspaceDropdown}>
                <a href="/hub" onClick={() => setSwitcherOpen(false)}
                  style={{ ...S.workspaceDropdownItemBase, color: 'var(--text-muted)', background: 'transparent', borderLeft: '2px solid transparent' }}>
                  <LayoutGrid style={{ width: 15, height: 15, color: 'var(--accent-2)', flexShrink: 0 }} />
                  System Dashboard
                </a>
                <button onClick={() => { setSwitcherOpen(false); navigate('/admin'); }}
                  style={{ ...S.workspaceDropdownItemBase, color: 'var(--text)', background: 'var(--surface-2)', borderLeft: '2px solid var(--accent)' }}>
                  <ShieldCheck style={{ width: 15, height: 15, color: 'var(--accent)', flexShrink: 0 }} />
                  Admin Console
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav style={S.nav}>
          {navItems.map(({ id, label, icon: Icon }) => {
            const active = activeTab === id;
            return (
              <button key={id} onClick={() => setActiveTab(id)} style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 14px',
                borderRadius: 12,
                fontSize: 13,
                fontWeight: 600,
                color: active ? 'var(--text)' : 'var(--text-muted)',
                background: active ? 'rgba(139,92,246,0.12)' : 'transparent',
                border: active ? '1px solid rgba(139,92,246,0.22)' : '1px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s',
                textAlign: 'left' as const,
                marginBottom: 2,
              }}>
                <Icon style={{ width: 16, height: 16, flexShrink: 0, color: active ? 'var(--accent)' : 'var(--text-dim)' }} />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        {/* Exit */}
        <div style={S.sidebarFooter}>
          <button onClick={() => { window.location.href = '/hub'; }} style={S.exitBtn}>
            <ArrowLeft style={{ width: 15, height: 15, flexShrink: 0 }} />
            Exit to Dashboard
          </button>
        </div>
      </aside>

      {/* â•â• MAIN CONTENT â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
      <main style={S.main}>
        <div style={S.mainInner}>

          {/* Error banner */}
          {error && (
            <div style={S.errorBanner}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#ef4444', flexShrink: 0 }} />
              {error}
            </div>
          )}

          {/* â”€â”€ DASHBOARD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'dashboard' && metrics && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>Admin Dashboard</h1>
                  <p style={S.pageSubtitle}>Platform administration and operations monitoring</p>
                </div>
                <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                  <RefreshCw style={{ width: 15, height: 15 }} />
                </button>
              </div>

              {/* KPI cards */}
              <div style={S.kpiGrid}>
                {[
                  { label: 'Total Registered Users',  value: metrics.users.total,             sub: `${metrics.users.online} active online` },
                  { label: 'Active Projects Today',   value: metrics.projects.running,         sub: `${metrics.projects.total} total projects` },
                  { label: 'Total LLM Requests',      value: metrics.ai.total_requests,        sub: `${metrics.ai.requests_today} today` },
                  { label: 'Operational AI Cost',     value: `$${metrics.ai.estimated_costs}`, sub: `${metrics.ai.tokens_consumed} total tokens` },
                ].map((c, i) => {
                  const KpiIcon = kpiIcons[i];
                  return (
                    <div key={i} style={S.kpiCard}>
                      <div style={{ position: 'absolute', top: 0, right: 0, width: 80, height: 80, borderRadius: '50%', background: kpiColors[i], opacity: 0.06, filter: 'blur(30px)', transform: 'translate(20px,-20px)' }} />
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <p style={S.kpiLabel}>{c.label}</p>
                        <div style={{ padding: 8, borderRadius: 10, background: `rgba(139,92,246,0.1)`, border: `1px solid rgba(139,92,246,0.2)` }}>
                          <KpiIcon style={{ width: 14, height: 14, color: kpiColors[i] }} />
                        </div>
                      </div>
                      <p style={S.kpiValue}>{c.value}</p>
                      <p style={S.kpiSub}>{c.sub}</p>
                    </div>
                  );
                })}
              </div>

              {/* Charts */}
              {charts && (
                <div style={S.chartsGrid}>
                  <div style={S.chartCard}>
                    <p style={S.chartTitle}>Total Users Growth</p>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={charts.user_growth} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.6} />
                        <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Line type="monotone" dataKey="users" stroke="var(--accent)" strokeWidth={2.5} dot={{ r: 3.5, fill: 'var(--accent)', strokeWidth: 0 }} activeDot={{ r: 5 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={S.chartCard}>
                    <p style={S.chartTitle}>Token &amp; Cost Trends</p>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={charts.ai_trends} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.6} />
                        <XAxis dataKey="date" stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                        <YAxis stroke="var(--text-dim)" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} />
                        <Bar dataKey="cost" name="Cost ($)" fill="var(--accent-2)" radius={[4, 4, 0, 0]} barSize={22} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* System resources */}
              <div style={S.sysCard}>
                <p style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>System Resource Observability</p>
                <div style={S.sysGrid}>
                  {[
                    { label: 'CPU Utilization', pct: metrics.system.cpu_util,  color: 'var(--accent)'      },
                    { label: 'RAM Utilization', pct: metrics.system.ram_util,  color: 'var(--accent-2)'    },
                    { label: 'File Storage',    pct: metrics.system.disk_util, color: 'var(--pastel-peach)'},
                  ].map((s, i) => (
                    <div key={i}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>{s.label}</span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>{s.pct}%</span>
                      </div>
                      <div style={S.sysBarTrack}>
                        <div style={{ height: '100%', background: s.color, width: `${s.pct}%`, borderRadius: 8, transition: 'width 0.5s ease' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* â”€â”€ USERS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'users' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>Users</h1>
                  <p style={S.pageSubtitle}>Manage platform users, roles, access and account status</p>
                </div>
                <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                  <RefreshCw style={{ width: 15, height: 15 }} />
                </button>
              </div>
              <div style={S.tableCard}>
                <div style={S.tableInner}>
                  <table style={{ ...S.table, width: '100%' }}>
                    <colgroup>
                      <col style={{ width: '18%' }} /><col style={{ width: '24%' }} /><col style={{ width: '11%' }} />
                      <col style={{ width: '20%' }} /><col style={{ width: '27%' }} />
                    </colgroup>
                    <thead>
                      <tr>
                        {['Name','Email','Status','Role','Actions'].map((h, i) => (
                          <th key={h} style={{ ...S.th, textAlign: i === 4 ? 'right' : 'left' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((u) => (
                        <tr key={u.id}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                          <td style={{ ...S.td, fontWeight: 600, color: 'var(--text)' }}>{u.first_name} {u.last_name}</td>
                          <td style={{ ...S.td, maxWidth: 230, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{u.email}</td>
                          <td style={S.td}><StatusBadge status={u.status} /></td>
                          <td style={S.td}>
                            <div style={{ position: 'relative' }}>
                              <select
                                value={u.roles[0] || 'USER'}
                                onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                disabled={!user?.roles.includes('SUPER_ADMIN') && u.roles.includes('SUPER_ADMIN')}
                                style={S.roleSelect}
                              >
                                <option value="USER">USER</option>
                                <option value="ADMIN">ADMIN</option>
                                <option value="SUPPORT">SUPPORT</option>
                                <option value="READ_ONLY_ADMIN">READ_ONLY_ADMIN</option>
                                <option value="SUPER_ADMIN" disabled={!user?.roles.includes('SUPER_ADMIN')}>SUPER_ADMIN</option>
                              </select>
                              <ChevronDown style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', width: 12, height: 12, color: 'var(--text-dim)', pointerEvents: 'none' }} />
                            </div>
                          </td>
                          <td style={{ ...S.td, textAlign: 'right' }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                              <button
                                onClick={() => handleUserStatusToggle(u.id, u.status)}
                                style={{
                                  fontSize: 11, padding: '6px 12px', fontWeight: 600, borderRadius: 8, cursor: 'pointer', transition: 'all 0.15s',
                                  border: `1px solid ${u.status === 'active' ? 'rgba(239,68,68,0.25)' : 'rgba(16,185,129,0.25)'}`,
                                  color: u.status === 'active' ? '#f87171' : '#34d399',
                                  background: u.status === 'active' ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                                }}>
                                {u.status === 'active' ? 'Suspend' : 'Activate'}
                              </button>
                              <button onClick={() => handleImpersonate(u.id)} style={{
                                fontSize: 11, padding: '6px 12px', fontWeight: 600, borderRadius: 8,
                                border: '1px solid rgba(139,92,246,0.25)', color: 'var(--accent)',
                                background: 'rgba(139,92,246,0.08)', cursor: 'pointer', transition: 'all 0.15s',
                              }}>
                                Impersonate
                              </button>
                              <button onClick={() => handleDeleteUser(u.id)} style={{
                                fontSize: 11, padding: '6px 12px', fontWeight: 600, borderRadius: 8,
                                border: '1px solid rgba(239,68,68,0.25)', color: '#ef4444',
                                background: 'rgba(239,68,68,0.08)', cursor: 'pointer', transition: 'all 0.15s',
                                marginLeft: '6px'
                              }}>
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* â”€â”€ PROJECTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'projects' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>Projects</h1>
                  <p style={S.pageSubtitle}>Monitor projects, ownership, status and deployments</p>
                </div>
                <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                  <RefreshCw style={{ width: 15, height: 15 }} />
                </button>
              </div>
              <div style={S.tableCard}>
                <div style={S.tableInner}>
                  <table style={{ ...S.table, minWidth: 780 }}>
                    <colgroup>
                      <col style={{ width: 220 }} /><col style={{ width: 220 }} /><col style={{ width: 130 }} />
                      <col style={{ width: 130 }} /><col style={{ width: 140 }} />
                    </colgroup>
                    <thead>
                      <tr>
                        {['Project Name','Owner','Status','Deployment','Created'].map((h) => (
                          <th key={h} style={S.th}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {projects.map((p) => (
                        <tr key={p.id}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                          <td style={{ ...S.td, fontWeight: 600, color: 'var(--text)', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</td>
                          <td style={{ ...S.td, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.owner_email || 'â€”'}</td>
                          <td style={S.td}><StatusBadge status={p.status} /></td>
                          <td style={S.td}><StatusBadge status={p.deployment_status} /></td>
                          <td style={{ ...S.td, fontSize: 12, color: 'var(--text-dim)' }}>{new Date(p.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* â”€â”€ AI AGENTS MONITOR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'agents' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>AI Agents Monitor</h1>
                  <p style={S.pageSubtitle}>Monitor agent execution, resource usage and operational status</p>
                </div>
                <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                  <RefreshCw style={{ width: 15, height: 15 }} />
                </button>
              </div>
              <div style={S.agentGrid}>
                {agents.map((a) => (
                  <div key={a.id} style={S.agentCard}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                      <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', lineHeight: 1.3 }}>{a.agent_name}</p>
                      <StatusBadge status={a.status} />
                    </div>
                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {[
                        ['Duration',    `${a.execution_duration_ms} ms`],
                        ['CPU Load',    `${a.cpu_usage}%`],
                        ['Memory Load', `${a.memory_usage}%`],
                      ].map(([label, val]) => (
                        <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                          <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                          <span style={{ fontFamily: 'var(--mono)', fontWeight: 600, color: 'var(--text)' }}>{val}</span>
                        </div>
                      ))}
                    </div>
                    <button onClick={() => handleRestartAgent(a.id)} style={S.agentRestartBtn}>
                      <RefreshCw style={{ width: 13, height: 13, color: 'var(--text-dim)' }} />
                      Restart Agent
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* â”€â”€ FEATURE FLAGS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'flags' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>Feature Flags</h1>
                  <p style={S.pageSubtitle}>Manage platform feature availability and experimental capabilities</p>
                </div>
                <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                  <RefreshCw style={{ width: 15, height: 15 }} />
                </button>
              </div>
              <div style={S.flagGrid}>
                {flags.map((f) => (
                  <div key={f.id} style={S.flagCard}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</p>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{f.description}</p>
                    </div>
                    <button
                      onClick={() => handleFlagToggle(f.id, f.is_enabled)}
                      role="switch"
                      aria-checked={f.is_enabled}
                      style={{
                        flexShrink: 0,
                        position: 'relative' as const,
                        display: 'inline-flex',
                        alignItems: 'center',
                        width: 46,
                        height: 26,
                        borderRadius: 26,
                        background: f.is_enabled ? 'var(--accent)' : 'var(--surface-3)',
                        border: '1px solid var(--border)',
                        cursor: 'pointer',
                        transition: 'background 0.25s',
                        padding: 0,
                      }}
                    >
                      <span style={{
                        position: 'absolute' as const,
                        width: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: '#fff',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                        transition: 'transform 0.25s',
                        transform: f.is_enabled ? 'translateX(22px)' : 'translateX(4px)',
                      }} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* â”€â”€ AUDIT LOGS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
          {activeTab === 'audit' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={S.pageHeader}>
                <div>
                  <h1 style={S.pageTitle}>Audit Logs</h1>
                  <p style={S.pageSubtitle}>Review administrative actions and platform activity</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <button onClick={() => window.open('/api/admin/reports/export?format=csv', '_blank')} style={S.exportBtn}>
                    <Download style={{ width: 13, height: 13 }} />
                    Export Logs (CSV)
                  </button>
                  <button style={S.refreshBtn} onClick={loadTabContent} title="Refresh">
                    <RefreshCw style={{ width: 15, height: 15 }} />
                  </button>
                </div>
              </div>
              <div style={S.tableCard}>
                <div style={S.tableInner}>
                  <table style={{ ...S.table, minWidth: 820 }}>
                    <colgroup>
                      <col style={{ width: 200 }} /><col style={{ width: 180 }} /><col />
                      <col style={{ width: 110 }} /><col style={{ width: 200 }} />
                    </colgroup>
                    <thead>
                      <tr>
                        {['User','Action','Resource','Result','Timestamp'].map((h, i) => (
                          <th key={h} style={{ ...S.th, textAlign: i === 4 ? 'right' : 'left' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {audits.map((a) => (
                        <tr key={a.id}
                          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.02)')}
                          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                          <td style={{ ...S.td, fontWeight: 600, color: 'var(--text)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.user}</td>
                          <td style={{ ...S.td, fontFamily: 'var(--mono)', fontSize: 11, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.action}</td>
                          <td style={{ ...S.td, fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.resource || 'â€”'}</td>
                          <td style={S.td}><StatusBadge status={a.result} /></td>
                          <td style={{ ...S.td, textAlign: 'right', fontSize: 11, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{new Date(a.created_at).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
