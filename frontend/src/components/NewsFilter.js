import React from 'react';
import { Newspaper } from 'lucide-react';

export default function NewsFilter({ news }) {
  return (
    <div data-testid="news-filter" className="rounded-2xl p-5" style={{ background: '#FFFFFF' }}>
      <div className="flex items-center gap-2 mb-4">
        <Newspaper className="w-4 h-4" style={{ color: '#2563EB' }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>News Filter</h3>
      </div>
      {!news ? (
        <p className="text-[12px]" style={{ color: '#9CA3AF' }}>News filter unavailable</p>
      ) : !news.enabled ? (
        <p className="text-[12px]" style={{ color: '#9CA3AF' }}>News filter is disabled</p>
      ) : (
        <div className="space-y-2">
          {news.is_blocked && news.block_reason && <NI text={news.block_reason} />}
          {news.advisory_reason && <NI text={news.advisory_reason} />}
          {(!news.upcoming_events || news.upcoming_events.length === 0) ? (
            <p className="text-[12px]" style={{ color: '#9CA3AF' }}>No high-impact events in next 24h</p>
          ) : (
            news.upcoming_events.map((e, i) => <NI key={i} text={`${e.currency} | ${e.title} | ${new Date(e.time).toLocaleString()}`} />)
          )}
        </div>
      )}
    </div>
  );
}

function NI({ text }) {
  return (
    <div className="flex items-start gap-2 text-[12px]" style={{ color: '#6B7280' }}>
      <span className="w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0" style={{ background: '#2563EB' }} />
      {text}
    </div>
  );
}
