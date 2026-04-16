import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, formatMoney, formatPercent, formatProfitFactor } from '../lib/api';
import ControlPanel from '../components/ControlPanel';
import { ArrowLeftRight } from 'lucide-react';

export default function Trades() {
  const [recentTrades, setRecentTrades] = useState([]);
  const [openTrades, setOpenTrades] = useState([]);
  const [scorecard, setScorecard] = useState(null);
  const [controlStatus, setControlStatus] = useState(null);
  const [tab, setTab] = useState('recent');
  const [activityLog, setActivityLog] = useState([]);

  const fetchData = useCallback(async () => {
    const [rt, ot, sc, ctrl, log] = await Promise.all([
      fetchJSON('/api/trades/recent?days=14'),
      fetchJSON('/api/trades/open'),
      fetchJSON('/api/strategies/scorecard?days=30&min_trades=2'),
      fetchJSON('/api/bot/control-status'),
      fetchJSON('/api/bot/activity-log'),
    ]);
    if (rt) setRecentTrades(rt);
    if (ot) setOpenTrades(ot);
    if (sc) setScorecard(sc);
    if (ctrl) setControlStatus(ctrl);
    if (log) setActivityLog(log);
  }, []);

  useEffect(() => { fetchData(); const i = setInterval(fetchData, 5000); return () => clearInterval(i); }, [fetchData]);

  const tabs = [
    { id: 'recent', label: 'Recent Trades', count: recentTrades.length },
    { id: 'open', label: 'Open Positions', count: openTrades.length },
    { id: 'strategies', label: 'Strategies', count: scorecard?.strategies?.length || 0 },
    { id: 'activity', label: 'Activity Log', count: activityLog.length },
  ];

  return (
    <div className="space-y-7 animate-fade-in" data-testid="trades-page">
      <div>
        <h1 className="text-[28px] font-bold" style={{ color: '#111827' }}>Trades</h1>
        <p className="text-[15px] mt-1" style={{ color: '#6B7280' }}>Transaction history, open positions, and strategy performance</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => (
          <button key={t.id} data-testid={`tab-${t.id}`} onClick={() => setTab(t.id)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[14px] font-medium transition-all"
            style={{ background: tab === t.id ? '#2563EB' : '#fff', color: tab === t.id ? '#fff' : '#6B7280', border: `1px solid ${tab === t.id ? '#2563EB' : '#E5E7EB'}` }}>
            {t.label}
            <span className="text-[12px] font-mono px-1.5 py-0.5 rounded-lg"
              style={{ background: tab === t.id ? 'rgba(255,255,255,0.2)' : '#F0F2F5' }}>{t.count}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'recent' && (
        <Card>
          {recentTrades.length === 0 ? <Empty text="No recent trades yet" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead><tr style={{ borderBottom: '2px solid #F0F2F5' }}>
                  {['Time', 'Instrument', 'Direction', 'P&L', 'Exit Reason', 'Strategy', 'Status'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-medium" style={{ color: '#9CA3AF' }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {recentTrades.slice(0, 25).map((t, i) => {
                    const pnl = t.pnl || 0;
                    return (
                      <tr key={i} className="hover:bg-gray-50 transition-colors" style={{ borderBottom: '1px solid #F0F2F5' }}>
                        <td className="py-3.5 px-4 font-mono" style={{ color: '#6B7280' }}>{new Date(t.closed_at || t.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                        <td className="py-3.5 px-4 font-mono font-bold" style={{ color: '#111827' }}>{t.instrument}</td>
                        <td className="py-3.5 px-4"><DirPill dir={t.direction} /></td>
                        <td className="py-3.5 px-4 font-mono font-bold" style={{ color: pnl >= 0 ? '#059669' : '#DC2626' }}>{formatMoney(pnl)}</td>
                        <td className="py-3.5 px-4" style={{ color: '#6B7280' }}>{t.exit_reason || '--'}</td>
                        <td className="py-3.5 px-4 font-mono" style={{ color: '#6B7280' }}>{t.strategy_name || '--'}</td>
                        <td className="py-3.5 px-4"><StatusPill reason={t.exit_reason} pnl={pnl} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'open' && (
        <Card>
          {openTrades.length === 0 ? <Empty text="No open positions — bot is watching for signals" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead><tr style={{ borderBottom: '2px solid #F0F2F5' }}>
                  {['Instrument', 'Direction', 'Entry Price', 'Stop Loss', 'Take Profit', 'AI Action'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-medium" style={{ color: '#9CA3AF' }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {openTrades.map((t, i) => (
                    <tr key={i} className="hover:bg-gray-50" style={{ borderBottom: '1px solid #F0F2F5' }}>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: '#111827' }}>{t.instrument}</td>
                      <td className="py-3.5 px-4"><DirPill dir={t.direction} /></td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#374151' }}>{Number(t.entry_price).toFixed(3)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#DC2626' }}>{Number(t.stop_loss).toFixed(3)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#059669' }}>{Number(t.take_profit).toFixed(3)}</td>
                      <td className="py-3.5 px-4" style={{ color: '#6B7280' }}>{t.ai_action || '--'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'strategies' && (
        <Card>
          {(!scorecard?.strategies || scorecard.strategies.length === 0) ? <Empty text="No strategy data yet" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead><tr style={{ borderBottom: '2px solid #F0F2F5' }}>
                  {['Strategy', 'Trades', 'Win Rate', 'Profit Factor', 'Total P&L', 'Status'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-medium" style={{ color: '#9CA3AF' }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {scorecard.strategies.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50" style={{ borderBottom: '1px solid #F0F2F5' }}>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: '#111827' }}>{r.strategy_name}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#6B7280' }}>{r.trades}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#D97706' }}>{formatPercent(r.win_rate)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: '#374151' }}>{formatProfitFactor(r.profit_factor)}</td>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: r.total_pnl >= 0 ? '#059669' : '#DC2626' }}>{formatMoney(r.total_pnl)}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-3 py-1 rounded-full text-[12px] font-bold"
                          style={{ background: r.eligible ? '#ECFDF5' : '#F0F2F5', color: r.eligible ? '#059669' : '#9CA3AF' }}>
                          {r.eligible ? 'Active' : 'Learning'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'activity' && (
        <Card>
          {(!activityLog || activityLog.length === 0) ? <Empty text="No activity logged yet" /> : (
            <div className="max-h-[500px] overflow-y-auto font-mono text-[13px] space-y-1 p-4 rounded-xl" style={{ background: '#F9FAFB' }}>
              {[...activityLog].reverse().map((e, i) => {
                const colors = { info: '#9CA3AF', signal: '#2563EB', blocked: '#D97706', trade: '#059669' };
                return (
                  <div key={i} className="py-1.5 pl-4 border-l-3" style={{ borderLeft: `3px solid ${colors[e.level] || '#D1D5DB'}`, color: colors[e.level] || '#6B7280' }}>
                    <span style={{ color: '#9CA3AF', marginRight: 10 }}>{e.time}</span>{e.message}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* Control Panel at bottom */}
      <ControlPanel controlStatus={controlStatus} onRefresh={fetchData} />
    </div>
  );
}

function Card({ children }) {
  return <div className="rounded-2xl p-6 shadow-sm" style={{ background: '#fff', border: '1px solid #E5E7EB' }}>{children}</div>;
}
function Empty({ text }) {
  return <p className="text-[15px] text-center py-16" style={{ color: '#9CA3AF' }}>{text}</p>;
}
function DirPill({ dir }) {
  const buy = dir?.toUpperCase() === 'BUY';
  return <span className="px-3 py-1 rounded-full text-[12px] font-bold" style={{ background: buy ? '#ECFDF5' : '#FEF2F2', color: buy ? '#059669' : '#DC2626' }}>{dir}</span>;
}
function StatusPill({ reason, pnl }) {
  if (reason === 'take_profit') return <span className="px-3 py-1 rounded-full text-[12px] font-bold" style={{ background: '#ECFDF5', color: '#059669' }}>Completed</span>;
  if (reason === 'stop_loss') return <span className="px-3 py-1 rounded-full text-[12px] font-bold" style={{ background: '#FEF2F2', color: '#DC2626' }}>Stopped</span>;
  if (pnl >= 0) return <span className="px-3 py-1 rounded-full text-[12px] font-bold" style={{ background: '#EFF6FF', color: '#2563EB' }}>Closed</span>;
  return <span className="px-3 py-1 rounded-full text-[12px] font-bold" style={{ background: '#FFFBEB', color: '#D97706' }}>Pending</span>;
}
