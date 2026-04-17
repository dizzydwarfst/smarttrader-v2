import React from 'react';

const tints = {
  green:   { iconBg: 'rgba(5,150,105,0.12)',  iconColor: '#059669' },
  red:     { iconBg: 'rgba(220,38,38,0.12)',   iconColor: '#DC2626' },
  amber:   { iconBg: 'rgba(37,99,235,0.12)',  iconColor: '#2563EB' },
  blue:    { iconBg: 'rgba(59,130,246,0.12)',  iconColor: '#3B82F6' },
  purple:  { iconBg: 'rgba(167,139,250,0.12)', iconColor: '#A78BFA' },
  orange:  { iconBg: 'rgba(37,99,235,0.12)',  iconColor: '#2563EB' },
  neutral: { iconBg: '#F1F5F9',                iconColor: '#475569' },
};

export default function StatCard({ testId, icon: Icon, title, value, valueColor, sub, subColor, tint = 'amber' }) {
  const t = tints[tint] || tints.neutral;
  return (
    <div data-testid={testId}
      className="rounded-xl p-5 transition-all duration-200"
      style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = '#3B4A63'}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = '#E2E8F0'}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#94A3B8' }}>{title}</span>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: t.iconBg }}>
          <Icon className="w-4 h-4" style={{ color: t.iconColor }} />
        </div>
      </div>
      <div className="text-[26px] font-bold tracking-tight" style={{ color: valueColor || '#0F172A', fontFamily: 'JetBrains Mono, monospace' }}>{value}</div>
      <div className="text-[11px] mt-1.5" style={{ color: subColor || '#94A3B8' }}>{sub}</div>
    </div>
  );
}
