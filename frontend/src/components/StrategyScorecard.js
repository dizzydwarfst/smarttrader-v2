import React from 'react';
import { formatMoney, formatPercent, formatProfitFactor } from '../lib/api';
import { Trophy } from 'lucide-react';

export default function StrategyScorecard({ scorecard }) {
  const strategies = scorecard?.strategies || [];
  const leaders = scorecard?.leaders?.by_instrument_regime || [];
  const overall = scorecard?.leaders?.overall;

  return (
    <div data-testid="strategy-scorecard" className="rounded-xl p-5" style={{ background: '#151A24', border: '1px solid #2A3548' }}>
      <div className="flex items-center gap-2 mb-4">
        <Trophy className="w-4 h-4" style={{ color: '#F59E0B' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>Strategy Scorecard</h3>
      </div>
      {strategies.length === 0 ? (
        <p className="text-[12px]" style={{ color: '#64748B' }}>No closed trades with strategy labels yet</p>
      ) : (
        <>
          <div className="flex flex-wrap justify-between gap-2 mb-4">
            <span className="text-[11px]" style={{ color: '#64748B' }}>
              {scorecard.window_days}d window | Min: {scorecard.min_trades} trades
            </span>
            {overall && <span className="text-[11px] font-semibold" style={{ color: '#F59E0B' }}>Leader: {overall.strategy_name}</span>}
          </div>
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-[12px]">
              <thead><tr style={{ borderBottom: '1px solid #2A3548' }}>
                {['Strategy', 'Trades', 'Win Rate', 'PF', 'P&L', 'Status'].map((h) => (
                  <th key={h} className="text-left py-2.5 px-3 font-semibold uppercase tracking-widest" style={{ color: '#64748B', fontSize: 10 }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>
                {strategies.slice(0, 6).map((row, i) => (
                  <tr key={i} className="transition-colors" style={{ borderBottom: '1px solid #1E2532' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                    <td className="py-2.5 px-3 font-mono" style={{ color: '#F8FAFC' }}>{row.strategy_name}</td>
                    <td className="py-2.5 px-3 font-mono" style={{ color: '#94A3B8' }}>{row.trades}</td>
                    <td className="py-2.5 px-3 font-mono" style={{ color: '#F8FAFC' }}>{formatPercent(row.win_rate)}</td>
                    <td className="py-2.5 px-3 font-mono" style={{ color: '#F8FAFC' }}>{formatProfitFactor(row.profit_factor)}</td>
                    <td className="py-2.5 px-3 font-mono font-semibold" style={{ color: row.total_pnl >= 0 ? '#10B981' : '#EF4444' }}>{formatMoney(row.total_pnl)}</td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                        style={{ background: row.eligible ? 'rgba(16,185,129,0.15)' : 'rgba(100,116,139,0.15)', color: row.eligible ? '#10B981' : '#94A3B8', border: `1px solid ${row.eligible ? 'rgba(16,185,129,0.3)' : 'rgba(100,116,139,0.3)'}` }}>
                        {row.eligible ? 'Ready' : 'Learning'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {leaders.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-[12px]">
                <thead><tr style={{ borderBottom: '1px solid #2A3548' }}>
                  {['Instrument', 'Regime', 'Leader', 'Trades', 'P&L'].map((h) => (
                    <th key={h} className="text-left py-2.5 px-3 font-semibold uppercase tracking-widest" style={{ color: '#64748B', fontSize: 10 }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {leaders.slice(0, 8).map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #1E2532' }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#1E2532'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                      <td className="py-2.5 px-3 font-mono" style={{ color: '#F8FAFC' }}>{row.instrument}</td>
                      <td className="py-2.5 px-3 font-mono" style={{ color: '#94A3B8' }}>{row.market_regime}</td>
                      <td className="py-2.5 px-3 font-mono font-semibold" style={{ color: '#F59E0B' }}>{row.strategy_name}</td>
                      <td className="py-2.5 px-3 font-mono" style={{ color: '#94A3B8' }}>{row.trades}</td>
                      <td className="py-2.5 px-3 font-mono font-semibold" style={{ color: row.total_pnl >= 0 ? '#10B981' : '#EF4444' }}>{formatMoney(row.total_pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
