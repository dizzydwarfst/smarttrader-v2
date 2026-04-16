import React from 'react';
import { formatPrice } from '../lib/api';
import { Radio } from 'lucide-react';

const badgeColors = {
  armed: '#059669', ready_now: '#059669', submitted: '#059669',
  blocked: '#DC2626', cooldown: '#DC2626',
  mixed: '#D97706', starting: '#D97706', warming_up: '#D97706',
};
const badgeLabels = {
  armed: 'Armed', ready_now: 'Ready', submitted: 'Submitted',
  blocked: 'Blocked', cooldown: 'Cooldown', mixed: 'Mixed',
  starting: 'Starting', warming_up: 'Warming',
};

export default function TradeReadiness({ readiness, factors }) {
  if (!readiness || !Object.keys(readiness).length) {
    return (
      <Section title="Trade Readiness" icon={Radio}>
        <p className="text-[12px]" style={{ color: '#9CA3AF' }}>Waiting for bot to publish readiness data...</p>
      </Section>
    );
  }
  const topStatus = readiness.status || 'starting';
  const topColor = badgeColors[topStatus] || '#D97706';
  const instrumentOrder = readiness.scanned_instruments || Object.keys(factors || {});

  return (
    <Section title="Trade Readiness" icon={Radio}>
      <div className="flex flex-col sm:flex-row justify-between gap-2 mb-4">
        <p className="text-[12px]" style={{ color: '#6B7280' }}>{readiness.summary || 'Waiting...'}</p>
        <Badge status={topStatus} color={topColor} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {instrumentOrder.map((instrument) => {
          const snap = factors?.[instrument];
          if (!snap) return null;
          const st = snap.trade_readiness_status || 'starting';
          const cl = badgeColors[st] || '#D97706';
          return (
            <div key={instrument} data-testid={`readiness-${instrument}`}
              className="p-3 rounded-xl" style={{ background: '#F0F2F5' }}>
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-[12px] font-mono font-semibold" style={{ color: '#111827' }}>{instrument}</span>
                <Badge status={st} color={cl} />
              </div>
              <p className="text-[11px]" style={{ color: '#9CA3AF' }}>
                {snap.trade_readiness_summary || snap.reason || 'No status'}
              </p>
              {snap.reverse_mode_applied && snap.effective_signal && snap.effective_signal !== snap.final_signal && (
                <div className="mt-2 pt-2 border-t text-[11px] space-y-0.5" style={{ borderColor: '#E5E7EB', color: '#9CA3AF' }}>
                  <div><strong style={{ color: '#111827' }}>Strategy:</strong> {snap.final_signal}</div>
                  <div><strong style={{ color: '#111827' }}>Execute:</strong> {snap.effective_signal}</div>
                  <div><strong style={{ color: '#111827' }}>Entry:</strong> {formatPrice(snap.planned_entry_price)}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <div className="rounded-2xl p-5" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

function Badge({ status, color }) {
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
      style={{ color, background: `${color}12`, border: `1px solid ${color}30` }}>
      {badgeLabels[status] || status?.replace(/_/g, ' ')}
    </span>
  );
}
