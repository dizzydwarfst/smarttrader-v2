import React from 'react';
import { Brain } from 'lucide-react';

export default function LearningMemory({ changes }) {
  return (
    <div data-testid="learning-memory" className="rounded-xl p-5" style={{ background: '#FFFFFF', border: '1px solid #E2E8F0' }}>
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: '#94A3B8' }}>Bot Memory</h3>
      </div>
      {(!changes || changes.length === 0) ? (
        <p className="text-[12px]" style={{ color: '#94A3B8' }}>No parameter changes yet</p>
      ) : (
        <div className="space-y-2">
          {changes.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b" style={{ borderColor: '#E2E8F0' }}>
              <div>
                <span className="text-[11px] font-semibold" style={{ color: '#2563EB' }}>{c.parameter}</span>
                <span className="text-[11px] font-mono ml-2" style={{ color: '#475569' }}>{c.old_value} &rarr; {c.new_value}</span>
              </div>
              <span className="text-[10px]" style={{ color: '#94A3B8' }}>{new Date(c.timestamp).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
