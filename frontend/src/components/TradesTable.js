import React from 'react';
import { formatMoney, formatPrice } from '../lib/api';
import { CircleDot, History } from 'lucide-react';

export default function TradesTable({ title, trades, isOpen }) {
  const Icon = isOpen ? CircleDot : History;
  return (
    <div data-testid={isOpen ? 'open-positions-table' : 'recent-trades-table'}
      className="rounded-xl p-5" style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#94A3B8' }}>{title}</h3>
      </div>
      {(!trades || trades.length === 0) ? (
        <p className="text-[12px] py-4 text-center" style={{ color: '#94A3B8' }}>{isOpen ? 'No open positions' : 'No trades yet'}</p>
      ) : (
        <div className="overflow-x-auto max-h-72 overflow-y-auto">
          <table className="w-full text-[12px]">
            <thead><tr style={{ borderBottom: '1px solid #E2E8F0' }}>
              {isOpen
                ? ['Instrument', 'Dir', 'Entry', 'SL', 'TP', 'AI'].map(h => <th key={h} className="text-left py-2 px-2 font-semibold uppercase tracking-widest" style={{ color: '#94A3B8', fontSize: 10 }}>{h}</th>)
                : ['Time', 'Inst', 'Dir', 'P&L', 'Exit', 'Regime'].map(h => <th key={h} className="text-left py-2 px-2 font-semibold uppercase tracking-widest" style={{ color: '#94A3B8', fontSize: 10 }}>{h}</th>)
              }
            </tr></thead>
            <tbody>
              {(isOpen ? trades : trades.slice(0, 20)).map((t, i) => (
                <tr key={i} className="transition-colors" style={{ borderBottom: '1px solid #F1F5F9' }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#F1F5F9'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                  {isOpen ? (
                    <>
                      <td className="py-2 px-2 font-mono font-semibold" style={{ color: '#0F172A' }}>{t.instrument}</td>
                      <td className="py-2 px-2"><DirBadge dir={t.direction} /></td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#475569' }}>{formatPrice(t.entry_price)}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#DC2626' }}>{formatPrice(t.stop_loss)}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#059669' }}>{formatPrice(t.take_profit)}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#475569' }}>{t.ai_action || '--'}</td>
                    </>
                  ) : (
                    <>
                      <td className="py-2 px-2 font-mono" style={{ color: '#94A3B8' }}>{new Date(t.closed_at || t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                      <td className="py-2 px-2 font-mono font-semibold" style={{ color: '#0F172A' }}>{t.instrument}</td>
                      <td className="py-2 px-2"><DirBadge dir={t.direction} /></td>
                      <td className="py-2 px-2 font-mono font-semibold" style={{ color: (t.pnl || 0) >= 0 ? '#059669' : '#DC2626' }}>{formatMoney(t.pnl)}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#475569' }}>{t.exit_reason || 'open'}</td>
                      <td className="py-2 px-2 font-mono" style={{ color: '#94A3B8' }}>{t.market_regime || '--'}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DirBadge({ dir }) {
  const buy = dir?.toUpperCase() === 'BUY';
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
      style={{ background: buy ? 'rgba(5,150,105,0.15)' : 'rgba(220,38,38,0.15)', color: buy ? '#059669' : '#DC2626', border: `1px solid ${buy ? 'rgba(5,150,105,0.3)' : 'rgba(220,38,38,0.3)'}` }}>
      {dir}
    </span>
  );
}
