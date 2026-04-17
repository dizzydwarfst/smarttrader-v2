import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

export default function PnlChart({ data }) {
  const chartData = (data || []).map((d) => ({
    ...d,
    time: d.timestamp ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '',
  }));

  return (
    <div data-testid="pnl-chart" className="rounded-xl p-5" style={{ background: '#151A24', border: '1px solid #2A3548' }}>
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-4 h-4" style={{ color: '#F59E0B' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>Cumulative P&L</h3>
      </div>
      {chartData.length === 0 ? (
        <p className="text-[12px] text-center py-12" style={{ color: '#64748B' }}>No trade data yet</p>
      ) : (
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E2532" />
              <XAxis dataKey="time" tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#2A3548' }} tickLine={false} />
              <YAxis tick={{ fill: '#64748B', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#2A3548' }} tickLine={false} tickFormatter={(v) => `$${v}`} />
              <Tooltip content={<Tip />} />
              <Area type="monotone" dataKey="cumulative_pnl" stroke="#F59E0B" strokeWidth={2.5} fill="url(#pnlGrad)" />
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
    <div className="rounded-lg p-2.5 text-[11px] font-mono" style={{ background: '#151A24', border: '1px solid #2A3548', boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
      <div style={{ color: '#F8FAFC' }}>{d.instrument} {d.direction}</div>
      <div style={{ color: d.pnl >= 0 ? '#10B981' : '#EF4444' }}>P&L: ${d.pnl?.toFixed(2)}</div>
      <div style={{ color: '#F59E0B' }}>Cum: ${d.cumulative_pnl?.toFixed(2)}</div>
    </div>
  );
}
