import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, postJSON, formatMoney, formatCurrency, formatProfitFactor } from '../lib/api';
import { DollarSign, TrendingUp, Target, BarChart3, ArrowUpRight, ArrowDownRight, Pause, Play, XCircle, Zap } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [controlStatus, setControlStatus] = useState(null);
  const [instruments, setInstruments] = useState([]);

  const fetchData = useCallback(async () => {
    const [s, st, cd, inst] = await Promise.all([
      fetchJSON('/api/status'),
      fetchJSON('/api/trades/stats?days=14'),
      fetchJSON('/api/chart/pnl?days=14'),
      fetchJSON('/api/analytics/instrument-breakdown?days=30'),
    ]);
    if (s) setStatus(s);
    if (st) setStats(st);
    if (cd) setChartData(cd);
    if (inst) setInstruments(inst);
  }, []);

  const fetchControl = useCallback(async () => {
    const ctrl = await fetchJSON('/api/bot/control-status');
    if (ctrl) setControlStatus(ctrl);
  }, []);

  useEffect(() => {
    fetchData(); fetchControl();
    const a = setInterval(fetchData, 5000);
    const b = setInterval(fetchControl, 3000);
    return () => { clearInterval(a); clearInterval(b); };
  }, [fetchData, fetchControl]);

  const winRate = stats ? (stats.win_rate * 100) : 0;
  const pieData = [{ name: 'Wins', value: stats?.wins || 0 }, { name: 'Losses', value: stats?.losses || 0 }];
  const instPie = instruments.filter(i => i.trades > 0).slice(0, 6).map(i => ({ name: i.instrument, value: i.trades }));
  const INST_COLORS = ['#2563EB', '#059669', '#D97706', '#DC2626', '#7C3AED', '#0891B2'];
  const pnlData = (chartData || []).map(d => ({
    time: d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
    pnl: d.cumulative_pnl,
  }));

  return (
    <div className="space-y-7 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-[28px] font-bold" style={{ color: '#111827' }}>Dashboard</h1>
          <p className="text-[15px] mt-1" style={{ color: '#6B7280' }}>Your trading bot at a glance</p>
        </div>
        <StatusPill status={status} />
      </div>

      {/* Stat Cards - big and clean */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <BigStat icon={DollarSign} label="Account NAV" value={formatCurrency(status?.account_nav)} color="#2563EB" bg="#EFF6FF" />
        <BigStat icon={TrendingUp} label="Today's P&L" value={formatMoney(status?.daily_pnl)}
          color={status?.daily_pnl >= 0 ? '#059669' : '#DC2626'}
          bg={status?.daily_pnl >= 0 ? '#ECFDF5' : '#FEF2F2'}
          trend={status?.daily_pnl >= 0 ? 'up' : 'down'} />
        <BigStat icon={Target} label="Win Rate (14d)" value={stats ? `${winRate.toFixed(1)}%` : '--%'} color="#D97706" bg="#FFFBEB" />
        <BigStat icon={BarChart3} label="Profit Factor" value={stats ? formatProfitFactor(stats.profit_factor) : '--'} color="#7C3AED" bg="#F5F3FF" />
      </div>

      {/* Main grid: P&L chart + controls */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* P&L Chart */}
        <div className="lg:col-span-2">
          <Card title="Cumulative P&L" large>
            {pnlData.length === 0 ? (
              <p className="text-[15px] text-center py-16" style={{ color: '#9CA3AF' }}>No trade data yet</p>
            ) : (
              <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={pnlData}>
                    <defs>
                      <linearGradient id="blueGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2563EB" stopOpacity={0.15} />
                        <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F0F2F5" />
                    <XAxis dataKey="time" tick={{ fill: '#9CA3AF', fontSize: 12 }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
                    <YAxis tick={{ fill: '#9CA3AF', fontSize: 12, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} tickFormatter={v => `$${v}`} />
                    <Tooltip contentStyle={{ background: '#fff', border: '1px solid #E5E7EB', borderRadius: 12, fontSize: 13 }} />
                    <Area type="monotone" dataKey="pnl" stroke="#2563EB" strokeWidth={2.5} fill="url(#blueGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Quick controls */}
          <Card title="Bot Controls">
            <div className="space-y-3">
              <div className="flex gap-3">
                <button data-testid="quick-pause-btn"
                  onClick={async () => { await postJSON(controlStatus?.paused ? '/api/bot/resume' : '/api/bot/pause', {}); fetchControl(); }}
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[14px] font-bold text-white transition-all"
                  style={{ background: controlStatus?.paused ? '#059669' : '#2563EB' }}>
                  {controlStatus?.paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                  {controlStatus?.paused ? 'Resume' : 'Pause'}
                </button>
                <button data-testid="quick-close-btn"
                  onClick={async () => { if (window.confirm('Close ALL positions?')) { await postJSON('/api/bot/close-all', {}); } }}
                  className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-[14px] font-bold text-white transition-all"
                  style={{ background: '#DC2626' }}>
                  <XCircle className="w-4 h-4" /> Close All
                </button>
              </div>
              <InfoRow label="Profile" value={controlStatus?.active_profile?.toUpperCase() || 'ROUTINE'} valueColor="#2563EB" />
              <InfoRow label="Status" value={controlStatus?.bot_online ? 'Online' : 'Offline'} valueColor={controlStatus?.bot_online ? '#059669' : '#DC2626'} />
              <InfoRow label="Open Positions" value={status?.open_positions || 0} />
              <InfoRow label="Poll Interval" value={`${controlStatus?.poll_interval || 30}s`} />
            </div>
          </Card>

          {/* Win rate donut */}
          <Card title="Win Rate">
            <div className="flex items-center gap-5">
              <div style={{ width: 110, height: 110, flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={35} outerRadius={50} paddingAngle={4} dataKey="value" stroke="none">
                      <Cell fill="#2563EB" />
                      <Cell fill="#E5E7EB" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div>
                <div className="text-[32px] font-bold font-mono" style={{ color: '#2563EB' }}>{winRate.toFixed(1)}%</div>
                <div className="text-[14px] mt-1" style={{ color: '#6B7280' }}>
                  <span style={{ color: '#059669' }}>{stats?.wins || 0} wins</span>
                  {' / '}
                  <span style={{ color: '#DC2626' }}>{stats?.losses || 0} losses</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Performance metrics + Instrument allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Performance */}
        <Card title="Performance Metrics" large>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricBox label="Total Trades" value={stats?.total || 0} />
            <MetricBox label="Total P&L" value={formatMoney(stats?.total_pnl)} color={stats?.total_pnl >= 0 ? '#059669' : '#DC2626'} />
            <MetricBox label="Avg P&L" value={formatMoney(stats?.avg_pnl)} color={stats?.avg_pnl >= 0 ? '#059669' : '#DC2626'} />
            <MetricBox label="Avg Hold" value={`${stats?.avg_hold_mins?.toFixed(0) || '--'} min`} />
            <MetricBox label="Largest Win" value={formatMoney(stats?.largest_win)} color="#059669" />
            <MetricBox label="Largest Loss" value={formatMoney(stats?.largest_loss)} color="#DC2626" />
            <MetricBox label="Sharpe" value={stats?.sharpe_ratio?.toFixed(2) || '--'} color="#2563EB" />
            <MetricBox label="Sortino" value={stats?.sortino_ratio?.toFixed(2) || '--'} color="#2563EB" />
          </div>
        </Card>

        {/* Instrument allocation */}
        <Card title="Instrument Allocation" large>
          {instPie.length === 0 ? (
            <p className="text-[15px] text-center py-12" style={{ color: '#9CA3AF' }}>No instrument data yet</p>
          ) : (
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div style={{ width: 180, height: 180, flexShrink: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={instPie} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value" stroke="none">
                      {instPie.map((_, i) => <Cell key={i} fill={INST_COLORS[i % INST_COLORS.length]} />)}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2.5 flex-1">
                {instPie.map((item, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="w-3 h-3 rounded" style={{ background: INST_COLORS[i % INST_COLORS.length] }} />
                      <span className="text-[14px] font-medium" style={{ color: '#374151' }}>{item.name}</span>
                    </div>
                    <span className="text-[14px] font-mono font-bold" style={{ color: '#111827' }}>{item.value} trades</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Card({ title, large, children }) {
  return (
    <div className="rounded-2xl shadow-sm" style={{ background: '#fff', border: '1px solid #E5E7EB' }}>
      {title && (
        <div className="px-6 pt-5 pb-0">
          <h3 className={`font-bold ${large ? 'text-[18px]' : 'text-[16px]'}`} style={{ color: '#111827' }}>{title}</h3>
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}

function BigStat({ icon: Icon, label, value, color, bg, trend }) {
  return (
    <div data-testid={`stat-${label.toLowerCase().replace(/[^a-z]/g, '-')}`}
      className="rounded-2xl p-6 shadow-sm" style={{ background: '#fff', border: '1px solid #E5E7EB' }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-medium" style={{ color: '#6B7280' }}>{label}</span>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: bg }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[28px] font-bold font-mono" style={{ color: '#111827' }}>{value}</span>
        {trend && (trend === 'up'
          ? <ArrowUpRight className="w-5 h-5" style={{ color: '#059669' }} />
          : <ArrowDownRight className="w-5 h-5" style={{ color: '#DC2626' }} />
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value, valueColor }) {
  return (
    <div className="flex items-center justify-between py-3 px-4 rounded-xl" style={{ background: '#F0F2F5' }}>
      <span className="text-[14px]" style={{ color: '#6B7280' }}>{label}</span>
      <span className="text-[14px] font-mono font-bold" style={{ color: valueColor || '#111827' }}>{value}</span>
    </div>
  );
}

function MetricBox({ label, value, color }) {
  return (
    <div className="p-4 rounded-xl" style={{ background: '#F0F2F5' }}>
      <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color: '#9CA3AF' }}>{label}</div>
      <div className="text-[20px] font-bold font-mono mt-1" style={{ color: color || '#111827' }}>{value}</div>
    </div>
  );
}

function StatusPill({ status }) {
  const isPractice = status?.trading_mode === 'practice';
  const online = status?.bot_online;
  return (
    <div data-testid="status-pill" className="flex items-center gap-2 px-4 py-2 rounded-full text-[13px] font-semibold shadow-sm"
      style={{ background: '#fff', color: online ? '#059669' : '#DC2626', border: '1px solid #E5E7EB' }}>
      <span className="w-2.5 h-2.5 rounded-full" style={{ background: online ? '#059669' : '#DC2626' }} />
      {status ? `${isPractice ? 'Practice' : 'Live'} ${online ? '- Online' : '- Offline'}` : 'Connecting...'}
    </div>
  );
}
