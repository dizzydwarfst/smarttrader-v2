import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON } from '../lib/api';
import AiAdvisor from '../components/AiAdvisor';
import NewsFilter from '../components/NewsFilter';
import LearningMemory from '../components/LearningMemory';
import { Bot, Newspaper, Brain, Shield, Cpu, Zap } from 'lucide-react';

const GOLD = '#2563EB';

export default function AiHub() {
  const [news, setNews] = useState(null);
  const [learning, setLearning] = useState([]);
  const [aiStatus, setAiStatus] = useState(null);
  const [memorySnapshot, setMemorySnapshot] = useState(null);
  const [stratLib, setStratLib] = useState(null);

  const fetchData = useCallback(async () => {
    const [nw, lr, ai, mem, sl] = await Promise.all([
      fetchJSON('/api/news/status'),
      fetchJSON('/api/learning/history?limit=20'),
      fetchJSON('/api/ai/status'),
      fetchJSON('/api/memory'),
      fetchJSON('/api/strategy-library'),
    ]);
    if (nw) setNews(nw);
    if (lr) setLearning(lr);
    if (ai) setAiStatus(ai);
    if (mem) setMemorySnapshot(mem);
    if (sl) setStratLib(sl);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="space-y-6 animate-fade-in" data-testid="ai-hub-page">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'Roboto, sans-serif', color: '#111827' }}>
          AI & News Hub
        </h2>
        <p className="text-sm mt-1" style={{ color: '#6B7280' }}>
          AI trading advisor, market news, and bot intelligence
        </p>
      </div>

      {/* AI Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <AiStatusCard
          icon={Cpu}
          label="AI Mode"
          value={aiStatus?.ai_mode?.toUpperCase() || '--'}
          sub={aiStatus?.ai_model || '--'}
        />
        <AiStatusCard
          icon={Shield}
          label="AI Confidence"
          value={aiStatus?.ai_min_confidence?.toUpperCase() || '--'}
          sub={`Size: ${aiStatus?.ai_min_size_mult || '--'}x - ${aiStatus?.ai_max_size_mult || '--'}x`}
        />
        <AiStatusCard
          icon={Zap}
          label="Reviews/Week"
          value={aiStatus?.reviews_this_week != null ? `${aiStatus.reviews_this_week}/${aiStatus.ai_max_automated_reviews_per_week}` : '--'}
          sub="Automated reviews budget"
        />
        <AiStatusCard
          icon={Brain}
          label="Learning"
          value={aiStatus?.ai_learning_enabled ? 'ACTIVE' : 'DISABLED'}
          valueColor={aiStatus?.ai_learning_enabled ? '#059669' : '#DC2626'}
          sub={`${learning.length} param changes recorded`}
        />
      </div>

      {/* Main content: AI Advisor full width */}
      <div className="rounded-2xl border p-5" style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}>
        <div className="flex items-center gap-2 mb-4">
          <Bot className="w-5 h-5" style={{ color: GOLD }} />
          <h3 className="text-base font-bold" style={{ fontFamily: 'Roboto, sans-serif', color: '#111827' }}>AI Trading Advisor</h3>
        </div>
        <AiAdvisor />
      </div>

      {/* News + Learning side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NewsFilter news={news} />
        <LearningMemory changes={learning} />
      </div>

      {/* Memory Snapshot + Strategy Library */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Memory Snapshot */}
        <Card title="Bot Memory Snapshot" icon={Brain} testId="memory-snapshot">
          {!memorySnapshot ? (
            <p className="text-xs" style={{ color: '#9CA3AF' }}>No memory snapshot available</p>
          ) : (
            <div className="space-y-2">
              {memorySnapshot.soul_summary && (
                <div>
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: GOLD }}>Soul</span>
                  <p className="text-xs mt-1 whitespace-pre-wrap" style={{ color: '#6B7280' }}>
                    {typeof memorySnapshot.soul_summary === 'string'
                      ? memorySnapshot.soul_summary.slice(0, 500)
                      : JSON.stringify(memorySnapshot.soul_summary).slice(0, 500)}
                  </p>
                </div>
              )}
              {memorySnapshot.skills_summary && (
                <div className="pt-2 border-t" style={{ borderColor: '#E5E7EB' }}>
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#2563EB' }}>Skills</span>
                  <p className="text-xs mt-1 whitespace-pre-wrap" style={{ color: '#6B7280' }}>
                    {typeof memorySnapshot.skills_summary === 'string'
                      ? memorySnapshot.skills_summary.slice(0, 500)
                      : JSON.stringify(memorySnapshot.skills_summary).slice(0, 500)}
                  </p>
                </div>
              )}
              {!memorySnapshot.soul_summary && !memorySnapshot.skills_summary && (
                <p className="text-xs" style={{ color: '#9CA3AF' }}>Memory snapshot is empty</p>
              )}
            </div>
          )}
        </Card>

        {/* Strategy Library */}
        <Card title="Strategy Library" icon={Zap} testId="strategy-library">
          {!stratLib ? (
            <p className="text-xs" style={{ color: '#9CA3AF' }}>No strategy library data</p>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-2">
              {stratLib.strategies && Array.isArray(stratLib.strategies) ? (
                stratLib.strategies.map((s, i) => (
                  <div key={i} className="p-3 rounded-xl" style={{ background: '#F0F2F5' }}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-semibold" style={{ color: GOLD }}>{s.name || s.strategy_name || `Strategy ${i + 1}`}</span>
                      <span className="text-xs font-mono" style={{ color: s.enabled !== false ? '#059669' : '#DC2626' }}>
                        {s.enabled !== false ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                    {s.description && <p className="text-xs mt-1" style={{ color: '#6B7280' }}>{s.description}</p>}
                  </div>
                ))
              ) : (
                <div className="text-xs" style={{ color: '#6B7280' }}>
                  <pre className="whitespace-pre-wrap font-mono">
                    {JSON.stringify(stratLib, null, 2).slice(0, 800)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function AiStatusCard({ icon: Icon, label, value, valueColor, sub }) {
  return (
    <div className="rounded-2xl p-4 border transition-all" style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245,158,11,0.4)'}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = '#E5E7EB'}
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4" style={{ color: GOLD }} />
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>{label}</span>
      </div>
      <div className="text-lg font-bold font-mono" style={{ color: valueColor || '#fff' }}>{value}</div>
      <div className="text-xs mt-0.5" style={{ color: '#6B7280' }}>{sub}</div>
    </div>
  );
}

function Card({ title, icon: Icon, testId, children }) {
  return (
    <div data-testid={testId} className="rounded-2xl border p-5" style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4" style={{ color: GOLD }} />
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}
