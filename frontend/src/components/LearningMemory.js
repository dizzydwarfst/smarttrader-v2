import React from 'react';
import { Brain } from 'lucide-react';

export default function LearningMemory({ changes }) {
  return (
    <div data-testid="learning-memory" className="rounded-xl p-5" style={{ background: '#151A24', border: '1px solid #2A3548' }}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4" style={{ color: '#F59E0B' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#64748B' }}>Bot Memory</h3>
      </div>
      {(!changes || changes.length === 0) ? (
        <p className="text-[12px]" style={{ color: '#64748B' }}>No parameter changes yet</p>
      ) : (
        <div className="space-y-2">
          {changes.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b" style={{ borderColor: '#2A3548' }}>
              <div>
                <span className="text-[11px] font-semibold" style={{ color: '#F59E0B' }}>{c.parameter}</span>
                <span className="text-[11px] font-mono ml-2" style={{ color: '#94A3B8' }}>{c.old_value} &rarr; {c.new_value}</span>
              </div>
              <span className="text-[10px]" style={{ color: '#64748B' }}>{new Date(c.timestamp).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
