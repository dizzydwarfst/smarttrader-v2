import React from 'react';

const tints = {
  green:   { iconBg: 'rgba(16,185,129,0.12)',  iconColor: '#10B981' },
  red:     { iconBg: 'rgba(239,68,68,0.12)',   iconColor: '#EF4444' },
  amber:   { iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B' },
  blue:    { iconBg: 'rgba(59,130,246,0.12)',  iconColor: '#3B82F6' },
  purple:  { iconBg: 'rgba(167,139,250,0.12)', iconColor: '#A78BFA' },
  orange:  { iconBg: 'rgba(245,158,11,0.12)',  iconColor: '#F59E0B' },
  neutral: { iconBg: '#1E2532',                iconColor: '#94A3B8' },
};

export default function StatCard({ testId, icon: Icon, title, value, valueColor, sub, subColor, tint = 'amber' }) {
  const t = tints[tint] || tints.neutral;
  return (
    <div data-testid={testId}
      className="rounded-xl p-5 transition-all duration-200"
      style={{ background: '#151A24', border: '1px solid #2A3548' }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = '#3B4A63'}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = '#2A3548'}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>{title}</span>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: t.iconBg }}>
          <Icon className="w-4 h-4" style={{ color: t.iconColor }} />
        </div>
      </div>
      <div className="text-[26px] font-bold tracking-tight" style={{ color: valueColor || '#F8FAFC', fontFamily: 'JetBrains Mono, monospace' }}>{value}</div>
      <div className="text-[11px] mt-1.5" style={{ color: subColor || '#64748B' }}>{sub}</div>
    </div>
  );
}
