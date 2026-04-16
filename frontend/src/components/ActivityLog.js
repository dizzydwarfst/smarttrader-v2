import React from 'react';
import { ScrollText } from 'lucide-react';

const levelColors = { info: '#9CA3AF', signal: '#2563EB', blocked: '#D97706', trade: '#059669' };

export default function ActivityLog({ entries }) {
  return (
    <div data-testid="activity-log" className="rounded-2xl p-5" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ScrollText className="w-4 h-4" style={{ color: '#2563EB' }} />
          <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>Activity Log</h3>
        </div>
        <span className="text-[11px] font-mono" style={{ color: '#9CA3AF' }}>{entries?.length || 0} entries</span>
      </div>
      <div className="max-h-72 overflow-y-auto font-mono text-[11px] space-y-px rounded-xl p-3" style={{ background: '#F9FAFB' }}>
        {(!entries || entries.length === 0) ? (
          <p style={{ color: '#9CA3AF' }}>Waiting for bot activity...</p>
        ) : (
          [...entries].reverse().map((entry, i) => (
            <div key={i} className="py-0.5 pl-2 border-l-2"
              style={{ borderColor: levelColors[entry.level] || '#9CA3AF', color: levelColors[entry.level] || '#9CA3AF' }}>
              <span style={{ color: '#D1D5DB', marginRight: 8 }}>{entry.time}</span>{entry.message}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
