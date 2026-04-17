import React, { useState, useRef, useEffect } from 'react';
import { postJSON } from '../lib/api';
import { Settings, Zap, RotateCcw, DollarSign, ChevronDown, ChevronUp } from 'lucide-react';

const profileDescriptions = {
  conservative: 'Slow and safe. H1 candles, 1% risk, max 2 positions.',
  routine: 'Balanced default. M15 candles, 2% risk, max 3 positions.',
  aggressive: 'More risk, faster scans. M5 candles, 3% risk, max 5 positions.',
  scalper: 'Ultra-fast M1 candles. 1.5% risk, max 8 positions.',
};

export default function ControlPanel({ controlStatus, onRefresh }) {
  const [currentProfile, setCurrentProfile] = useState('routine');
  const [isCustom, setIsCustom] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [granularity, setGranularity] = useState('M15');
  const [poll, setPoll] = useState('30');
  const [maxPos, setMaxPos] = useState('3');
  const [risk, setRisk] = useState('0.02');
  const [trainingMode, setTrainingMode] = useState(false);
  const [reverseMode, setReverseMode] = useState(false);
  const [minPnl, setMinPnl] = useState('1.00');
  const pendingRef = useRef({});

  useEffect(() => {
    if (!controlStatus) return;
    const now = Date.now();
    if (!pendingRef.current.profile && controlStatus.active_profile) setCurrentProfile(controlStatus.active_profile);
    if (!pendingRef.current.training || now >= pendingRef.current.training) { setTrainingMode(controlStatus.daily_loss_limit_enabled === false); pendingRef.current.training = 0; }
    if (!pendingRef.current.reverse || now >= pendingRef.current.reverse) { setReverseMode(!!controlStatus.reverse_mode); pendingRef.current.reverse = 0; }
    if (!pendingRef.current.minPnl || now >= pendingRef.current.minPnl) { if (controlStatus.min_trade_pnl != null) setMinPnl(Number(controlStatus.min_trade_pnl).toFixed(2)); pendingRef.current.minPnl = 0; }
  }, [controlStatus]);

  const activateProfile = async (name) => { await postJSON('/api/profile/activate', { profile: name }); setCurrentProfile(name); setIsCustom(false); pendingRef.current.profile = true; setTimeout(() => { pendingRef.current.profile = false; }, 10000); onRefresh(); };
  const applyCustom = async () => { await postJSON('/api/settings', { bar_granularity: granularity, poll_interval: parseInt(poll), max_positions: parseInt(maxPos), risk_per_trade: parseFloat(risk) }); setIsCustom(true); onRefresh(); };
  const toggleTraining = async () => { const n = !trainingMode; setTrainingMode(n); pendingRef.current.training = Date.now() + 12000; await postJSON('/api/bot/training-mode', { enabled: n }); onRefresh(); };
  const toggleReverse = async () => { const n = !reverseMode; if (n && !window.confirm('Reverse flips BUY/SELL. Sure?')) return; setReverseMode(n); pendingRef.current.reverse = Date.now() + 12000; await postJSON('/api/bot/reverse-mode', { enabled: n }); onRefresh(); };
  const applyMinPnl = async () => { const v = parseFloat(minPnl); if (isNaN(v) || v < 0) return; pendingRef.current.minPnl = Date.now() + 12000; await postJSON('/api/bot/min-trade-pnl', { value: v }); onRefresh(); };

  return (
    <div data-testid="control-panel" className="rounded-xl p-6" style={{ background: '#151A24', border: '1px solid #2A3548' }}>
      <div className="flex items-center justify-between mb-5 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5" style={{ color: '#F59E0B' }} />
          <h3 className="text-[16px] font-bold" style={{ color: '#F8FAFC', fontFamily: 'Outfit, sans-serif' }}>Control Panel</h3>
          <span className="text-[12px] font-mono px-2.5 py-1 rounded-lg font-bold"
            style={{ background: 'rgba(245,158,11,0.12)', color: '#F59E0B', border: '1px solid rgba(245,158,11,0.3)' }}>
            {isCustom ? 'CUSTOM' : currentProfile.toUpperCase()}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5" style={{ color: '#64748B' }} /> : <ChevronDown className="w-5 h-5" style={{ color: '#64748B' }} />}
      </div>

      <div className="flex flex-wrap gap-2.5 mb-4">
        {['conservative', 'routine', 'aggressive', 'scalper'].map(p => {
          const act = currentProfile === p && !isCustom;
          return (
            <button key={p} data-testid={`profile-btn-${p}`} onClick={() => activateProfile(p)}
              className="px-4 py-2.5 rounded-lg text-[13px] font-semibold transition-all"
              style={{
                background: act ? '#F59E0B' : '#1E2532',
                color: act ? '#0B0E14' : '#94A3B8',
                border: `1px solid ${act ? '#F59E0B' : '#2A3548'}`
              }}
              onMouseEnter={(e) => { if (!act) { e.currentTarget.style.borderColor = '#F59E0B'; e.currentTarget.style.color = '#F8FAFC'; } }}
              onMouseLeave={(e) => { if (!act) { e.currentTarget.style.borderColor = '#2A3548'; e.currentTarget.style.color = '#94A3B8'; } }}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          );
        })}
      </div>
      <p className="text-[14px]" style={{ color: '#94A3B8' }}>{isCustom ? 'Custom settings applied.' : profileDescriptions[currentProfile]}</p>

      {expanded && (
        <div className="space-y-4 pt-5 mt-5 border-t" style={{ borderColor: '#2A3548' }}>
          <div className="flex flex-wrap items-center gap-3 p-4 rounded-lg" style={{ background: '#0B0E14', border: '1px solid #2A3548' }}>
            <Sel label="Candle" value={granularity} onChange={setGranularity} options={[['M1','M1'],['M5','M5'],['M15','M15'],['M30','M30'],['H1','H1'],['H4','H4']]} />
            <Sel label="Scan" value={poll} onChange={setPoll} options={[['10','10s'],['15','15s'],['30','30s'],['60','60s']]} />
            <Sel label="Pos" value={maxPos} onChange={setMaxPos} options={[['1','1'],['2','2'],['3','3'],['5','5'],['8','8']]} />
            <Sel label="Risk" value={risk} onChange={setRisk} options={[['0.01','1%'],['0.015','1.5%'],['0.02','2%'],['0.03','3%']]} />
            <button data-testid="apply-custom-btn" onClick={applyCustom}
              className="px-5 py-2 rounded-lg text-[13px] font-bold transition-all"
              style={{ background: '#F59E0B', color: '#0B0E14' }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#FBBF24'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#F59E0B'}>Apply</button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Chip testId="training-mode-chip" active={trainingMode} onClick={toggleTraining} icon={Zap} label={`Training: ${trainingMode ? 'ON' : 'OFF'}`} color="#10B981" />
            <Chip testId="reverse-mode-chip" active={reverseMode} onClick={toggleReverse} icon={RotateCcw} label={`Reverse: ${reverseMode ? 'ON' : 'OFF'}`} color="#EF4444" />
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4" style={{ color: '#64748B' }} />
              <input data-testid="min-pnl-input" type="number" step="0.25" min="0" value={minPnl} onChange={(e) => setMinPnl(e.target.value)}
                className="w-16 px-2.5 py-1.5 rounded-lg text-[13px] font-mono focus:outline-none transition-all"
                style={{ background: '#0B0E14', color: '#F8FAFC', border: '1px solid #2A3548' }}
                onFocus={(e) => e.target.style.borderColor = '#F59E0B'}
                onBlur={(e) => e.target.style.borderColor = '#2A3548'} />
              <button data-testid="set-min-pnl-btn" onClick={applyMinPnl}
                className="px-3 py-1.5 rounded-lg text-[12px] font-semibold transition-all"
                style={{ background: '#1E2532', color: '#94A3B8', border: '1px solid #2A3548' }}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#F59E0B'; e.currentTarget.style.color = '#F8FAFC'; }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#2A3548'; e.currentTarget.style.color = '#94A3B8'; }}>Set</button>
            </div>
          </div>
          {reverseMode && (
            <div data-testid="reverse-mode-notice" className="p-4 rounded-lg text-[13px]"
              style={{ background: 'rgba(239,68,68,0.08)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.25)' }}>
              <strong style={{ color: '#EF4444' }}>Reverse Mode Active</strong> — BUY signals execute as SELL, and vice versa.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Sel({ label, value, onChange, options }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[12px]" style={{ color: '#94A3B8' }}>{label}:</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="px-2.5 py-1.5 rounded-lg text-[12px] font-mono cursor-pointer focus:outline-none transition-all"
        style={{ background: '#151A24', color: '#F8FAFC', border: '1px solid #2A3548' }}
        onFocus={(e) => e.target.style.borderColor = '#F59E0B'}
        onBlur={(e) => e.target.style.borderColor = '#2A3548'}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

function Chip({ testId, active, onClick, icon: Icon, label, color }) {
  return (
    <button data-testid={testId} onClick={onClick}
      className="flex items-center gap-2 px-4 py-2 rounded-full text-[12px] font-semibold transition-all"
      style={{
        background: active ? color : '#1E2532',
        color: active ? '#0B0E14' : '#94A3B8',
        border: `1px solid ${active ? color : '#2A3548'}`
      }}>
      <Icon className="w-3.5 h-3.5" /> {label}
    </button>
  );
}
