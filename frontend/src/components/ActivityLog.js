import React from 'react';
import { ScrollText } from 'lucide-react';

const levelColors = { info: '#94A3B8', signal: '#3B82F6', blocked: '#F59E0B', trade: '#10B981' };

export default function ActivityLog({ entries }) {
  return (
    <div data-testid="activity-log" className="rounded-xl p-5" style={{ background: '#151A24', border: '1px solid #2A3548' }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ScrollText className="w-4 h-4" style={{ color: '#F59E0B' }} />
          <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>Activity Log</h3>
        </div>
        <span className="text-[11px] font-mono" style={{ color: '#64748B' }}>{entries?.length || 0} entries</span>
      </div>
      <div className="max-h-72 overflow-y-auto font-mono text-[11px] space-y-px rounded-lg p-3"
        style={{ background: '#000000', border: '1px solid #1E2532' }}>
        {(!entries || entries.length === 0) ? (
          <p style={{ color: '#F59E0B', opacity: 0.6 }}>Waiting for bot activity...</p>
        ) : (
          [...entries].reverse().map((entry, i) => (
            <div key={i} className="py-0.5 pl-2 border-l-2"
              style={{ borderColor: levelColors[entry.level] || '#F59E0B', color: levelColors[entry.level] || '#F59E0B' }}>
              <span style={{ color: '#475569', marginRight: 8 }}>{entry.time}</span>{entry.message}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
