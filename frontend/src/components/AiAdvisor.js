import React, { useState, useRef, useEffect } from 'react';
import { fetchJSON, postJSON } from '../lib/api';
import { Send, BarChart3, Sunrise, Clock } from 'lucide-react';

export default function AiAdvisor() {
  const [messages, setMessages] = useState([
    { type: 'bot', text: "Welcome! I'm your AI trading advisor. Click Analyze for a performance review, or ask me anything." },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const add = (type, text) => setMessages((p) => [...p, { type, text }]);

  const runAnalysis = async () => { add('user', 'Analyze my trading performance'); setLoading(true); const r = await fetchJSON('/api/ai/analyze?days=7'); setLoading(false); add('bot', r?.analysis || 'Could not run analysis. Check CLAUDE_API_KEY.'); };
  const getBriefing = async () => { add('user', 'Market briefing'); setLoading(true); const r = await fetchJSON('/api/ai/analyze?days=1'); setLoading(false); add('bot', r?.analysis || 'Could not get briefing.'); };
  const explainWait = async () => { add('user', 'Why waiting?'); setLoading(true); const r = await fetchJSON('/api/ai/why-waiting'); setLoading(false); add('bot', r?.answer || 'Cannot explain.'); };
  const askAI = async () => { if (!input.trim()) return; const q = input.trim(); setInput(''); add('user', q); setLoading(true); const r = await postJSON('/api/ai/ask', { question: q }); setLoading(false); add('bot', r?.answer || 'No response'); };

  return (
    <div data-testid="ai-advisor" className="flex flex-col">
      <div ref={scrollRef} className="flex-1 max-h-80 overflow-y-auto space-y-2 mb-3">
        {messages.map((msg, i) => (
          <div key={i} className="px-3 py-2 rounded-lg text-[12px] leading-relaxed whitespace-pre-wrap"
            style={{
              background: msg.type === 'bot' ? '#1E2532' : 'rgba(245,158,11,0.08)',
              borderLeft: `3px solid ${msg.type === 'bot' ? '#F59E0B' : '#F59E0B'}`,
              color: '#F8FAFC'
            }}>
            {msg.text}
          </div>
        ))}
        {loading && <div className="px-3 py-2 rounded-lg text-[12px]" style={{ background: '#1E2532', borderLeft: '3px solid #F59E0B', color: '#F59E0B' }}>Thinking...</div>}
      </div>
      <div className="flex gap-2 mb-2">
        <button data-testid="ai-analyze-btn" onClick={runAnalysis}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all"
          style={{ background: '#F59E0B', color: '#0B0E14' }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#FBBF24'}
          onMouseLeave={(e) => e.currentTarget.style.background = '#F59E0B'}>
          <BarChart3 className="w-3 h-3" /> Analyze</button>
        <button data-testid="ai-briefing-btn" onClick={getBriefing}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all"
          style={{ background: '#1E2532', color: '#94A3B8', border: '1px solid #2A3548' }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#F59E0B'; e.currentTarget.style.color = '#F8FAFC'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2A3548'; e.currentTarget.style.color = '#94A3B8'; }}>
          <Sunrise className="w-3 h-3" /> Briefing</button>
        <button data-testid="ai-why-waiting-btn" onClick={explainWait}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all"
          style={{ background: '#1E2532', color: '#94A3B8', border: '1px solid #2A3548' }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#F59E0B'; e.currentTarget.style.color = '#F8FAFC'; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2A3548'; e.currentTarget.style.color = '#94A3B8'; }}>
          <Clock className="w-3 h-3" /> Why waiting?</button>
      </div>
      <div className="flex gap-2">
        <input data-testid="ai-input" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && askAI()}
          placeholder="Ask about your trades..." className="flex-1 px-3 py-2 rounded-lg text-[12px] focus:outline-none transition-all"
          style={{ background: '#0B0E14', color: '#F8FAFC', border: '1px solid #2A3548' }}
          onFocus={(e) => e.target.style.borderColor = '#F59E0B'}
          onBlur={(e) => e.target.style.borderColor = '#2A3548'} />
        <button data-testid="ai-send-btn" onClick={askAI}
          className="px-3 py-2 rounded-lg transition-all"
          style={{ background: '#F59E0B', color: '#0B0E14' }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#FBBF24'}
          onMouseLeave={(e) => e.currentTarget.style.background = '#F59E0B'}>
          <Send className="w-3.5 h-3.5" /></button>
      </div>
    </div>
  );
}
