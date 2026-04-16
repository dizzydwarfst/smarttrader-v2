import React from 'react';
import { Brain } from 'lucide-react';

export default function LearningMemory({ changes }) {
  return (
    <div data-testid="learning-memory" className="rounded-2xl p-5" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>Bot Memory</h3>
      </div>
      {(!changes || changes.length === 0) ? (
        <p className="text-[12px]" style={{ color: '#9CA3AF' }}>No parameter changes yet</p>
      ) : (
        <div className="space-y-2">
          {changes.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b" style={{ borderColor: '#E5E7EB' }}>
              <div>
                <span className="text-[11px] font-semibold" style={{ color: '#2563EB' }}>{c.parameter}</span>
                <span className="text-[11px] font-mono ml-2" style={{ color: '#6B7280' }}>{c.old_value} &rarr; {c.new_value}</span>
              </div>
              <span className="text-[10px]" style={{ color: '#9CA3AF' }}>{new Date(c.timestamp).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
