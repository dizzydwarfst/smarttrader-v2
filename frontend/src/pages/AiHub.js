import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON } from '../lib/api';
import AiAdvisor from '../components/AiAdvisor';
import NewsFilter from '../components/NewsFilter';
import LearningMemory from '../components/LearningMemory';
import { Bot, Brain, Shield, Cpu, Zap } from 'lucide-react';

const GOLD = '#F59E0B';
const GREEN = '#10B981';
const RED = '#EF4444';
const SURFACE = '#151A24';
const SURFACE_ALT = '#1E2532';
const BG = '#0B0E14';
const BORDER = '#2A3548';
const TEXT = '#F8FAFC';
const TEXT_SECONDARY = '#94A3B8';
const TEXT_MUTED = '#64748B';

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
      <div>
        <h2 className="text-[22px] font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif', color: TEXT }}>
          AI & News Hub
        </h2>
        <p className="text-[13px] mt-1" style={{ color: TEXT_SECONDARY }}>
          AI trading advisor, market news, and bot intelligence
        </p>
      </div>

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
          valueColor={aiStatus?.ai_learning_enabled ? GREEN : RED}
          sub={`${learning.length} param changes recorded`}
        />
      </div>

      <div className="rounded-xl p-5" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}>
        <div className="flex items-center gap-2 mb-4">
          <Bot className="w-5 h-5" style={{ color: GOLD }} />
          <h3 className="text-[15px] font-bold" style={{ fontFamily: 'Outfit, sans-serif', color: TEXT }}>AI Trading Advisor</h3>
        </div>
        <AiAdvisor />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <NewsFilter news={news} />
        <LearningMemory changes={learning} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card title="Bot Memory Snapshot" icon={Brain} testId="memory-snapshot">
          {!memorySnapshot ? (
            <p className="text-[12px]" style={{ color: TEXT_MUTED }}>No memory snapshot available</p>
          ) : (
            <div className="space-y-3">
              {memorySnapshot.soul_summary && (
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: GOLD }}>Soul</span>
                  <p className="text-[12px] mt-1 whitespace-pre-wrap leading-relaxed" style={{ color: TEXT_SECONDARY }}>
                    {typeof memorySnapshot.soul_summary === 'string'
                      ? memorySnapshot.soul_summary.slice(0, 500)
                      : JSON.stringify(memorySnapshot.soul_summary).slice(0, 500)}
                  </p>
                </div>
              )}
              {memorySnapshot.skills_summary && (
                <div className="pt-2 border-t" style={{ borderColor: BORDER }}>
                  <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#60A5FA' }}>Skills</span>
                  <p className="text-[12px] mt-1 whitespace-pre-wrap leading-relaxed" style={{ color: TEXT_SECONDARY }}>
                    {typeof memorySnapshot.skills_summary === 'string'
                      ? memorySnapshot.skills_summary.slice(0, 500)
                      : JSON.stringify(memorySnapshot.skills_summary).slice(0, 500)}
                  </p>
                </div>
              )}
              {!memorySnapshot.soul_summary && !memorySnapshot.skills_summary && (
                <p className="text-[12px]" style={{ color: TEXT_MUTED }}>Memory snapshot is empty</p>
              )}
            </div>
          )}
        </Card>

        <Card title="Strategy Library" icon={Zap} testId="strategy-library">
          {!stratLib ? (
            <p className="text-[12px]" style={{ color: TEXT_MUTED }}>No strategy library data</p>
          ) : (
            <div className="max-h-72 overflow-y-auto space-y-2">
              {stratLib.strategies && Array.isArray(stratLib.strategies) ? (
                stratLib.strategies.map((s, i) => (
                  <div key={i} className="p-3 rounded-lg" style={{ background: BG, border: `1px solid ${BORDER}` }}>
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] font-mono font-semibold" style={{ color: GOLD }}>{s.name || s.strategy_name || `Strategy ${i + 1}`}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full" style={{
                        background: s.enabled !== false ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                        color: s.enabled !== false ? GREEN : RED,
                        border: `1px solid ${s.enabled !== false ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                      }}>
                        {s.enabled !== false ? 'Active' : 'Disabled'}
                      </span>
                    </div>
                    {s.description && <p className="text-[11px] mt-1" style={{ color: TEXT_SECONDARY }}>{s.description}</p>}
                  </div>
                ))
              ) : (
                <div className="text-[11px]" style={{ color: TEXT_SECONDARY }}>
                  <pre className="whitespace-pre-wrap font-mono p-3 rounded-lg" style={{ background: BG, border: `1px solid ${BORDER}`, color: TEXT_SECONDARY }}>
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
    <div className="rounded-xl p-4 transition-all" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(245,158,11,0.4)'}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = BORDER}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 rounded-lg" style={{ background: 'rgba(245,158,11,0.12)' }}>
          <Icon className="w-3.5 h-3.5" style={{ color: GOLD }} />
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED }}>{label}</span>
      </div>
      <div className="text-[18px] font-bold font-mono" style={{ color: valueColor || TEXT }}>{value}</div>
      <div className="text-[11px] mt-0.5" style={{ color: TEXT_SECONDARY }}>{sub}</div>
    </div>
  );
}

function Card({ title, icon: Icon, testId, children }) {
  return (
    <div data-testid={testId} className="rounded-xl p-5" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4" style={{ color: GOLD }} />
        <h3 className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}
