import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, formatMoney, formatPercent, formatProfitFactor } from '../lib/api';
import StatCard from '../components/StatCard';
import {
  BarChart3, TrendingUp, Target, DollarSign, Activity, Clock,
  Layers, PieChart as PieIcon, ArrowUpDown
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, PieChart, Pie, Cell
} from 'recharts';

const GOLD = '#F59E0B';
const GREEN = '#10B981';
const RED = '#EF4444';
const BLUE = '#3B82F6';
const PURPLE = '#A78BFA';
const SURFACE = '#151A24';
const BORDER = '#2A3548';
const TEXT = '#F8FAFC';
const TEXT_SECONDARY = '#94A3B8';
const TEXT_MUTED = '#64748B';

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  const [dailyData, setDailyData] = useState([]);
  const [hourlyData, setHourlyData] = useState({});
  const [instruments, setInstruments] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [distribution, setDistribution] = useState(null);
  const [activityLog, setActivityLog] = useState([]);
  const [period, setPeriod] = useState(30);
  const [controlStatus, setControlStatus] = useState(null);

  const fetchData = useCallback(async () => {
    const [ov, daily, hourly, inst, strat, dist, log, ctrl] = await Promise.all([
      fetchJSON('/api/analytics/overview'),
      fetchJSON(`/api/analytics/daily-breakdown?days=${period}`),
      fetchJSON(`/api/analytics/hourly-performance?days=${period}`),
      fetchJSON(`/api/analytics/instrument-breakdown?days=${period}`),
      fetchJSON(`/api/analytics/strategy-breakdown?days=${period}`),
      fetchJSON(`/api/analytics/trade-distribution?days=${period}`),
      fetchJSON('/api/bot/activity-log'),
      fetchJSON('/api/bot/control-status'),
    ]);
    if (ov) setOverview(ov);
    if (daily) setDailyData(daily);
    if (hourly) setHourlyData(hourly);
    if (inst) setInstruments(inst);
    if (strat) setStrategies(strat);
    if (dist) setDistribution(dist);
    if (log) setActivityLog(log);
    if (ctrl) setControlStatus(ctrl);
  }, [period]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const stats30 = overview?.stats_30d;
  const stats7 = overview?.stats_7d;

  const hourlyChartData = Object.entries(hourlyData).map(([hour, data]) => ({
    hour: `${hour}:00`,
    trades: data.trades,
    win_rate: (data.win_rate * 100).toFixed(0),
    pnl: data.total_pnl,
  }));

  const instrumentPieData = instruments.filter(i => i.trades > 0).map((inst) => ({
    name: inst.instrument,
    value: inst.trades,
  }));
  const PIE_COLORS = [GOLD, GREEN, BLUE, PURPLE, RED, '#EC4899', '#06B6D4', '#FBBF24'];

  const distChartData = distribution ? [
    { name: 'Large Loss', value: distribution.pnl_ranges.large_loss, color: RED },
    { name: 'Small Loss', value: distribution.pnl_ranges.small_loss, color: '#F87171' },
    { name: 'Breakeven', value: distribution.pnl_ranges.breakeven, color: TEXT_MUTED },
    { name: 'Small Win', value: distribution.pnl_ranges.small_win, color: '#6EE7B7' },
    { name: 'Large Win', value: distribution.pnl_ranges.large_win, color: GREEN },
  ] : [];

  return (
    <div className="space-y-6 animate-fade-in" data-testid="analytics-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-[32px] font-black tracking-tight" style={{ fontFamily: 'Outfit, sans-serif', color: TEXT }}>Analytics</h2>
          <p className="text-[15px] mt-1" style={{ color: TEXT_SECONDARY }}>Detailed performance statistics and trade analysis</p>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map((d) => {
            const act = period === d;
            return (
              <button key={d} data-testid={`period-btn-${d}`} onClick={() => setPeriod(d)}
                className="px-4 py-2 rounded-lg text-xs font-bold transition-all"
                style={{
                  background: act ? GOLD : SURFACE,
                  color: act ? '#0B0E14' : TEXT_SECONDARY,
                  border: `1px solid ${act ? GOLD : BORDER}`,
                }}
                onMouseEnter={(e) => { if (!act) { e.currentTarget.style.borderColor = GOLD; e.currentTarget.style.color = TEXT; } }}
                onMouseLeave={(e) => { if (!act) { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.color = TEXT_SECONDARY; } }}>
                {d}d
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard testId="analytics-total-pnl" icon={DollarSign} title="Total Realized P&L" tint="amber"
          value={formatMoney(overview?.total_realized_pnl)}
          valueColor={overview?.total_realized_pnl >= 0 ? GREEN : RED}
          sub={`30d: ${formatMoney(stats30?.total_pnl)} | 7d: ${formatMoney(stats7?.total_pnl)}`} />
        <StatCard testId="analytics-total-trades" icon={Activity} title={`Total Trades (${period}d)`} tint="blue"
          value={stats30?.total?.toString() || '0'}
          sub={`Wins: ${stats30?.wins || 0} | Losses: ${stats30?.losses || 0} | Noise: ${stats30?.noise || 0}`} />
        <StatCard testId="analytics-win-rate" icon={Target} title={`Win Rate (${period}d)`} tint="amber"
          value={stats30 ? `${(stats30.win_rate * 100).toFixed(1)}%` : '--%'}
          valueColor={GOLD}
          sub={`Sharpe: ${stats30?.sharpe_ratio?.toFixed(2) || '--'} | Sortino: ${stats30?.sortino_ratio?.toFixed(2) || '--'}`} />
        <StatCard testId="analytics-avg-pnl" icon={TrendingUp} title="Avg P&L / Trade" tint="green"
          value={formatMoney(stats30?.avg_pnl)}
          valueColor={stats30?.avg_pnl >= 0 ? GREEN : RED}
          sub={`Avg Hold: ${stats30?.avg_hold_mins?.toFixed(0) || '--'} min | PF: ${formatProfitFactor(stats30?.profit_factor)}`} />
      </div>

      <Card title="Daily P&L Breakdown" icon={BarChart3} testId="daily-pnl-chart">
        {dailyData.length === 0 ? <Empty text="No daily data available" /> : (
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2532" />
                <XAxis dataKey="date" tick={{ fill: TEXT_MUTED, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: BORDER }} tickLine={false} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: TEXT_MUTED, fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: BORDER }} tickLine={false} tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<DailyTooltip />} />
                <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                  {dailyData.map((entry, i) => (
                    <Cell key={i} fill={entry.pnl >= 0 ? GREEN : RED} fillOpacity={0.88} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card title="Cumulative P&L Over Time" icon={TrendingUp} testId="cumulative-pnl-chart">
        {dailyData.length === 0 ? <Empty text="No data available" /> : (
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dailyData}>
                <defs>
                  <linearGradient id="cumGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={GOLD} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={GOLD} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2532" />
                <XAxis dataKey="date" tick={{ fill: TEXT_MUTED, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: BORDER }} tickLine={false} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: TEXT_MUTED, fontSize: 11, fontFamily: 'JetBrains Mono' }}
                  axisLine={{ stroke: BORDER }} tickLine={false} tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<CumTooltip />} />
                <Area type="monotone" dataKey="cumulative_pnl" stroke={GOLD} strokeWidth={2.5} fill="url(#cumGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Hourly Performance" icon={Clock} testId="hourly-performance-chart">
          {hourlyChartData.length === 0 ? <Empty text="No hourly data" /> : (
            <div style={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={hourlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2532" />
                  <XAxis dataKey="hour" tick={{ fill: TEXT_MUTED, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                    axisLine={{ stroke: BORDER }} tickLine={false} />
                  <YAxis tick={{ fill: TEXT_MUTED, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                    axisLine={{ stroke: BORDER }} tickLine={false} tickFormatter={(v) => `$${v}`} />
                  <Tooltip content={<HourlyTooltip />} />
                  <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
                    {hourlyChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.pnl >= 0 ? GREEN : RED} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card title="Trade Distribution" icon={ArrowUpDown} testId="trade-distribution-chart">
          {distChartData.length === 0 ? <Empty text="No distribution data" /> : (
            <div style={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distChartData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E2532" />
                  <XAxis type="number" tick={{ fill: TEXT_MUTED, fontSize: 10, fontFamily: 'JetBrains Mono' }}
                    axisLine={{ stroke: BORDER }} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fill: TEXT_SECONDARY, fontSize: 10 }}
                    axisLine={{ stroke: BORDER }} tickLine={false} width={80} />
                  <Tooltip contentStyle={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12, color: TEXT }}
                    labelStyle={{ color: TEXT }} itemStyle={{ fontFamily: 'JetBrains Mono' }} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {distChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} fillOpacity={0.88} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Instrument Allocation" icon={PieIcon} testId="instrument-allocation">
          {instrumentPieData.length === 0 ? <Empty text="No instrument data" /> : (
            <div className="flex flex-col md:flex-row items-center gap-4">
              <div style={{ height: 220, width: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={instrumentPieData} cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                      paddingAngle={3} dataKey="value" stroke="none">
                      {instrumentPieData.map((entry, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12, color: TEXT }}
                      labelStyle={{ color: TEXT }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 flex-1">
                {instrumentPieData.map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span style={{ color: TEXT }}>{item.name}</span>
                    <span className="ml-auto font-mono" style={{ color: TEXT_SECONDARY }}>{item.value} trades</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card title="Instrument Performance" icon={Layers} testId="instrument-performance-table">
          {instruments.length === 0 ? <Empty text="No instrument data" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  {['Instrument', 'Trades', 'Win%', 'P&L', 'Avg'].map(h => (
                    <th key={h} className="text-left py-2 px-2 font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED, fontSize: 10 }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {instruments.map((inst, i) => (
                    <tr key={i} style={{ borderBottom: `1px solid #1E2532` }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td className="py-2 px-2 font-mono font-bold" style={{ color: TEXT }}>{inst.instrument}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: TEXT_SECONDARY }}>{inst.trades}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: GOLD }}>{formatPercent(inst.win_rate)}</td>
                      <td className="py-2 px-2 font-mono font-semibold" style={{ color: inst.pnl >= 0 ? GREEN : RED }}>{formatMoney(inst.pnl)}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: inst.avg_pnl >= 0 ? GREEN : RED }}>{formatMoney(inst.avg_pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>

      <Card title="Strategy Performance" icon={Target} testId="strategy-performance-table">
        {strategies.length === 0 ? <Empty text="No strategy data" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                {['Strategy', 'Trades', 'Wins', 'Losses', 'Win Rate', 'Total P&L', 'Avg P&L'].map(h => (
                  <th key={h} className="text-left py-2 px-3 font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED, fontSize: 10 }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {strategies.map((s, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid #1E2532` }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                    <td className="py-2 px-3 font-mono font-bold" style={{ color: GOLD }}>{s.strategy}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: TEXT_SECONDARY }}>{s.trades}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: GREEN }}>{s.wins}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: RED }}>{s.losses}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: TEXT }}>{formatPercent(s.win_rate)}</td>
                    <td className="py-2 px-3 font-mono font-semibold" style={{ color: s.pnl >= 0 ? GREEN : RED }}>{formatMoney(s.pnl)}</td>
                    <td className="py-2 px-3 font-mono" style={{ color: s.avg_pnl >= 0 ? GREEN : RED }}>{formatMoney(s.avg_pnl)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Bot Activity Log" icon={Activity} testId="analytics-activity-log">
          <div className="max-h-64 overflow-y-auto font-mono text-xs space-y-0.5 p-3 rounded-lg"
            style={{ background: '#000000', border: `1px solid #1E2532` }}>
            {(!activityLog || activityLog.length === 0) ? (
              <p style={{ color: GOLD, opacity: 0.6 }}>No activity logged yet</p>
            ) : (
              [...activityLog].reverse().map((entry, i) => {
                const levelColors = { info: '#94A3B8', signal: BLUE, blocked: GOLD, trade: GREEN };
                const color = levelColors[entry.level] || GOLD;
                return (
                  <div key={i} className="py-0.5 pl-2 border-l-2" style={{ borderColor: color, color }}>
                    <span style={{ color: '#475569', marginRight: 8 }}>{entry.time}</span>
                    {entry.message}
                  </div>
                );
              })
            )}
          </div>
        </Card>

        <Card title="Bot Uptime & Status" icon={Activity} testId="bot-uptime-status">
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <StatusItem label="Bot Status" value={controlStatus?.bot_online ? 'Online' : 'Offline'}
                color={controlStatus?.bot_online ? GREEN : RED} />
              <StatusItem label="Active Profile" value={controlStatus?.active_profile?.toUpperCase() || '--'} color={GOLD} />
              <StatusItem label="Paused" value={controlStatus?.paused ? 'Yes' : 'No'}
                color={controlStatus?.paused ? RED : GREEN} />
              <StatusItem label="Poll Interval" value={`${controlStatus?.poll_interval || '--'}s`} color={TEXT_SECONDARY} />
              <StatusItem label="Loss Limit" value={controlStatus?.daily_loss_limit_enabled ? 'Enabled' : 'Disabled'}
                color={controlStatus?.daily_loss_limit_enabled ? GREEN : GOLD} />
              <StatusItem label="Reverse Mode" value={controlStatus?.reverse_mode ? 'ON' : 'OFF'}
                color={controlStatus?.reverse_mode ? RED : GREEN} />
            </div>
            {distribution && (
              <div className="pt-3 border-t" style={{ borderColor: BORDER }}>
                <div className="flex justify-between text-xs mb-2">
                  <span style={{ color: TEXT_MUTED }}>Exit Reasons</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(distribution.exit_reasons).map(([reason, count]) => (
                    <span key={reason} className="px-2 py-1 rounded text-xs font-mono"
                      style={{ background: '#0B0E14', color: TEXT_SECONDARY, border: `1px solid ${BORDER}` }}>
                      {reason}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Card({ title, icon: Icon, testId, children }) {
  return (
    <div data-testid={testId} className="rounded-xl p-5" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4" style={{ color: GOLD }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Empty({ text }) {
  return <p className="text-xs text-center py-8" style={{ color: TEXT_MUTED }}>{text}</p>;
}

function StatusItem({ label, value, color }) {
  return (
    <div className="p-3 rounded-lg" style={{ background: '#0B0E14', border: `1px solid ${BORDER}` }}>
      <div className="text-xs mb-1" style={{ color: TEXT_MUTED }}>{label}</div>
      <div className="text-sm font-bold font-mono" style={{ color }}>{value}</div>
    </div>
  );
}

function DailyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg p-3 text-xs font-mono" style={{ background: SURFACE, border: `1px solid ${BORDER}`, boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
      <div style={{ color: TEXT }}>{d.date}</div>
      <div style={{ color: d.pnl >= 0 ? GREEN : RED }}>P&L: {formatMoney(d.pnl)}</div>
      <div style={{ color: GOLD }}>Cumulative: {formatMoney(d.cumulative_pnl)}</div>
      <div style={{ color: TEXT_SECONDARY }}>{d.trades} trades | WR: {formatPercent(d.win_rate)}</div>
    </div>
  );
}

function CumTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg p-3 text-xs font-mono" style={{ background: SURFACE, border: `1px solid ${BORDER}`, boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
      <div style={{ color: TEXT }}>{d.date}</div>
      <div style={{ color: GOLD }}>Cumulative: {formatMoney(d.cumulative_pnl)}</div>
    </div>
  );
}

function HourlyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg p-3 text-xs font-mono" style={{ background: SURFACE, border: `1px solid ${BORDER}`, boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
      <div style={{ color: TEXT }}>{d.hour}</div>
      <div style={{ color: d.pnl >= 0 ? GREEN : RED }}>P&L: ${Number(d.pnl).toFixed(2)}</div>
      <div style={{ color: TEXT_SECONDARY }}>{d.trades} trades | WR: {d.win_rate}%</div>
    </div>
  );
}
