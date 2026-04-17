import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, formatMoney, formatPercent, formatProfitFactor } from '../lib/api';
import ControlPanel from '../components/ControlPanel';

const GOLD = '#F59E0B';
const GREEN = '#10B981';
const RED = '#EF4444';
const SURFACE = '#151A24';
const BORDER = '#2A3548';
const TEXT = '#F8FAFC';
const TEXT_SECONDARY = '#94A3B8';
const TEXT_MUTED = '#64748B';

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
        <h1 className="text-[32px] font-black tracking-tight" style={{ color: TEXT, fontFamily: 'Outfit, sans-serif' }}>Trades</h1>
        <p className="text-[15px] mt-1" style={{ color: TEXT_SECONDARY }}>Transaction history, open positions, and strategy performance</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map(t => {
          const active = tab === t.id;
          return (
            <button key={t.id} data-testid={`tab-${t.id}`} onClick={() => setTab(t.id)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[14px] font-semibold transition-all"
              style={{
                background: active ? GOLD : SURFACE,
                color: active ? '#0B0E14' : TEXT_SECONDARY,
                border: `1px solid ${active ? GOLD : BORDER}`
              }}
              onMouseEnter={(e) => { if (!active) { e.currentTarget.style.borderColor = GOLD; e.currentTarget.style.color = TEXT; } }}
              onMouseLeave={(e) => { if (!active) { e.currentTarget.style.borderColor = BORDER; e.currentTarget.style.color = TEXT_SECONDARY; } }}>
              {t.label}
              <span className="text-[12px] font-mono px-1.5 py-0.5 rounded"
                style={{ background: active ? 'rgba(11,14,20,0.25)' : '#1E2532', color: active ? '#0B0E14' : TEXT_SECONDARY }}>{t.count}</span>
            </button>
          );
        })}
      </div>

      {tab === 'recent' && (
        <Card>
          {recentTrades.length === 0 ? <Empty text="No recent trades yet" /> : (
            <div className="overflow-x-auto">
              <table className="w-full text-[14px]">
                <thead><tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  {['Time', 'Instrument', 'Direction', 'P&L', 'Exit Reason', 'Strategy', 'Status'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED, fontSize: 11 }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {recentTrades.slice(0, 25).map((t, i) => {
                    const pnl = t.pnl || 0;
                    return (
                      <tr key={i} className="transition-colors" style={{ borderBottom: `1px solid #1E2532` }}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                        <td className="py-3.5 px-4 font-mono" style={{ color: TEXT_SECONDARY }}>{new Date(t.closed_at || t.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
                        <td className="py-3.5 px-4 font-mono font-bold" style={{ color: TEXT }}>{t.instrument}</td>
                        <td className="py-3.5 px-4"><DirPill dir={t.direction} /></td>
                        <td className="py-3.5 px-4 font-mono font-bold" style={{ color: pnl >= 0 ? GREEN : RED }}>{formatMoney(pnl)}</td>
                        <td className="py-3.5 px-4" style={{ color: TEXT_SECONDARY }}>{t.exit_reason || '--'}</td>
                        <td className="py-3.5 px-4 font-mono" style={{ color: TEXT_SECONDARY }}>{t.strategy_name || '--'}</td>
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
                <thead><tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  {['Instrument', 'Direction', 'Entry Price', 'Stop Loss', 'Take Profit', 'AI Action'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED, fontSize: 11 }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {openTrades.map((t, i) => (
                    <tr key={i} className="transition-colors" style={{ borderBottom: `1px solid #1E2532` }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: TEXT }}>{t.instrument}</td>
                      <td className="py-3.5 px-4"><DirPill dir={t.direction} /></td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: TEXT_SECONDARY }}>{Number(t.entry_price).toFixed(3)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: RED }}>{Number(t.stop_loss).toFixed(3)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: GREEN }}>{Number(t.take_profit).toFixed(3)}</td>
                      <td className="py-3.5 px-4" style={{ color: TEXT_SECONDARY }}>{t.ai_action || '--'}</td>
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
                <thead><tr style={{ borderBottom: `1px solid ${BORDER}` }}>
                  {['Strategy', 'Trades', 'Win Rate', 'Profit Factor', 'Total P&L', 'Status'].map(h => (
                    <th key={h} className="text-left py-3.5 px-4 font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED, fontSize: 11 }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {scorecard.strategies.map((r, i) => (
                    <tr key={i} className="transition-colors" style={{ borderBottom: `1px solid #1E2532` }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: TEXT }}>{r.strategy_name}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: TEXT_SECONDARY }}>{r.trades}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: GOLD }}>{formatPercent(r.win_rate)}</td>
                      <td className="py-3.5 px-4 font-mono" style={{ color: TEXT }}>{formatProfitFactor(r.profit_factor)}</td>
                      <td className="py-3.5 px-4 font-mono font-bold" style={{ color: r.total_pnl >= 0 ? GREEN : RED }}>{formatMoney(r.total_pnl)}</td>
                      <td className="py-3.5 px-4">
                        <span className="px-3 py-1 rounded-full text-[12px] font-bold"
                          style={{ background: r.eligible ? 'rgba(16,185,129,0.12)' : '#1E2532', color: r.eligible ? GREEN : TEXT_SECONDARY, border: `1px solid ${r.eligible ? 'rgba(16,185,129,0.3)' : BORDER}` }}>
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
            <div className="max-h-[500px] overflow-y-auto font-mono text-[13px] space-y-1 p-4 rounded-lg"
              style={{ background: '#000000', border: `1px solid #1E2532` }}>
              {[...activityLog].reverse().map((e, i) => {
                const colors = { info: '#94A3B8', signal: '#3B82F6', blocked: GOLD, trade: GREEN };
                return (
                  <div key={i} className="py-1.5 pl-4" style={{ borderLeft: `3px solid ${colors[e.level] || GOLD}`, color: colors[e.level] || GOLD }}>
                    <span style={{ color: '#475569', marginRight: 10 }}>{e.time}</span>{e.message}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      <ControlPanel controlStatus={controlStatus} onRefresh={fetchData} />
    </div>
  );
}

function Card({ children }) {
  return <div className="rounded-xl p-6" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}>{children}</div>;
}
function Empty({ text }) {
  return <p className="text-[15px] text-center py-16" style={{ color: TEXT_MUTED }}>{text}</p>;
}
function DirPill({ dir }) {
  const buy = dir?.toUpperCase() === 'BUY';
  return <span className="px-3 py-1 rounded-full text-[12px] font-bold"
    style={{ background: buy ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: buy ? GREEN : RED, border: `1px solid ${buy ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}` }}>{dir}</span>;
}
function StatusPill({ reason, pnl }) {
  const base = "px-3 py-1 rounded-full text-[12px] font-bold";
  if (reason === 'take_profit') return <span className={base} style={{ background: 'rgba(16,185,129,0.12)', color: GREEN, border: `1px solid rgba(16,185,129,0.3)` }}>Completed</span>;
  if (reason === 'stop_loss') return <span className={base} style={{ background: 'rgba(239,68,68,0.12)', color: RED, border: `1px solid rgba(239,68,68,0.3)` }}>Stopped</span>;
  if (pnl >= 0) return <span className={base} style={{ background: 'rgba(245,158,11,0.12)', color: GOLD, border: `1px solid rgba(245,158,11,0.3)` }}>Closed</span>;
  return <span className={base} style={{ background: '#1E2532', color: TEXT_SECONDARY, border: `1px solid ${BORDER}` }}>Pending</span>;
}
