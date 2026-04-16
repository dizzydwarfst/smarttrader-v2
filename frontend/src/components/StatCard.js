import React from 'react';

const tints = {
  green: { bg: '#1A2A1E', iconBg: '#1B3A26', iconColor: '#059669' },
  red: { bg: '#2A1A1A', iconBg: '#3A1B1B', iconColor: '#DC2626' },
  amber: { bg: '#2A2518', iconBg: '#3A3020', iconColor: '#D97706' },
  blue: { bg: '#1A1E2A', iconBg: '#1B2A3A', iconColor: '#2563EB' },
  purple: { bg: '#201A2E', iconBg: '#2A1E3E', iconColor: '#2563EB' },
  orange: { bg: '#2A1E18', iconBg: '#3A2A1E', iconColor: '#DC2626' },
  neutral: { bg: '#FFFFFF', iconBg: '#E5E7EB', iconColor: '#6B7280' },
};

export default function StatCard({ testId, icon: Icon, title, value, valueColor, sub, subColor, tint = 'neutral' }) {
  const t = tints[tint] || tints.neutral;
  return (
    <div data-testid={testId} className="rounded-2xl p-5 transition-all duration-200" style={{ background: t.bg }}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: '#9CA3AF' }}>{title}</span>
        <div className="w-9 h-9 rounded-2xl flex items-center justify-center" style={{ background: t.iconBg }}>
          <Icon className="w-4 h-4" style={{ color: t.iconColor }} />
        </div>
      </div>
      <div className="text-[26px] font-bold tracking-tight" style={{ color: valueColor || '#fff', fontFamily: 'JetBrains Mono, monospace' }}>{value}</div>
      <div className="text-[11px] mt-1.5" style={{ color: subColor || '#9CA3AF' }}>{sub}</div>
    </div>
  );
}
