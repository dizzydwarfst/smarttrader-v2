import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

export default function PnlChart({ data }) {
  const chartData = (data || []).map((d) => ({
    ...d,
    time: d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
  }));

  return (
    <div data-testid="pnl-chart" className="rounded-2xl p-5" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>Cumulative P&L</h3>
      </div>
      {chartData.length === 0 ? (
        <p className="text-[12px] text-center py-12" style={{ color: '#9CA3AF' }}>No trade data yet</p>
      ) : (
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2563EB" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#FFFFFF" />
              <XAxis dataKey="time" tick={{ fill: '#D1D5DB', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} />
              <YAxis tick={{ fill: '#D1D5DB', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#E5E7EB' }} tickLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip content={<Tip />} />
              <Area type="monotone" dataKey="cumulative_pnl" stroke="#2563EB" strokeWidth={2} fill="url(#pnlGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function Tip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl p-2.5 text-[11px] font-mono" style={{ background: '#FFFFFF', border: '1px solid #E5E7EB' }}>
      <div style={{ color: '#111827' }}>{d.instrument} {d.direction}</div>
      <div style={{ color: d.pnl >= 0 ? '#059669' : '#DC2626' }}>P&L: ${d.pnl?.toFixed(2)}</div>
      <div style={{ color: '#2563EB' }}>Cum: ${d.cumulative_pnl?.toFixed(2)}</div>
    </div>
  );
}
