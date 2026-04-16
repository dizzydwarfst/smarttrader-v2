import React, { useState, useRef, useEffect } from 'react';
import { postJSON } from '../lib/api';
import { Settings, Pause, Play, XCircle, Zap, RotateCcw, DollarSign, ChevronDown, ChevronUp } from 'lucide-react';

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
    <div data-testid="control-panel" className="rounded-2xl p-6 shadow-sm" style={{ background: '#fff', border: '1px solid #E5E7EB' }}>
      <div className="flex items-center justify-between mb-5 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5" style={{ color: '#2563EB' }} />
          <h3 className="text-[16px] font-bold" style={{ color: '#111827' }}>Control Panel</h3>
          <span className="text-[12px] font-mono px-2.5 py-1 rounded-lg" style={{ background: '#EFF6FF', color: '#2563EB' }}>
            {isCustom ? 'CUSTOM' : currentProfile.toUpperCase()}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5" style={{ color: '#9CA3AF' }} /> : <ChevronDown className="w-5 h-5" style={{ color: '#9CA3AF' }} />}
      </div>

      <div className="flex flex-wrap gap-2.5 mb-4">
        {['conservative', 'routine', 'aggressive', 'scalper'].map(p => (
          <button key={p} data-testid={`profile-btn-${p}`} onClick={() => activateProfile(p)}
            className="px-4 py-2.5 rounded-xl text-[13px] font-medium transition-all"
            style={{ background: currentProfile === p && !isCustom ? '#2563EB' : '#F0F2F5', color: currentProfile === p && !isCustom ? '#fff' : '#6B7280' }}>
            {p.charAt(0).toUpperCase() + p.slice(1)}
          </button>
        ))}
      </div>
      <p className="text-[14px]" style={{ color: '#6B7280' }}>{isCustom ? 'Custom settings applied.' : profileDescriptions[currentProfile]}</p>

      {expanded && (
        <div className="space-y-4 pt-5 mt-5 border-t" style={{ borderColor: '#E5E7EB' }}>
          <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl" style={{ background: '#F9FAFB' }}>
            <Sel label="Candle" value={granularity} onChange={setGranularity} options={[['M1','M1'],['M5','M5'],['M15','M15'],['M30','M30'],['H1','H1'],['H4','H4']]} />
            <Sel label="Scan" value={poll} onChange={setPoll} options={[['10','10s'],['15','15s'],['30','30s'],['60','60s']]} />
            <Sel label="Pos" value={maxPos} onChange={setMaxPos} options={[['1','1'],['2','2'],['3','3'],['5','5'],['8','8']]} />
            <Sel label="Risk" value={risk} onChange={setRisk} options={[['0.01','1%'],['0.015','1.5%'],['0.02','2%'],['0.03','3%']]} />
            <button data-testid="apply-custom-btn" onClick={applyCustom} className="px-5 py-2 rounded-xl text-[13px] font-bold text-white" style={{ background: '#2563EB' }}>Apply</button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Chip testId="training-mode-chip" active={trainingMode} onClick={toggleTraining} icon={Zap} label={`Training: ${trainingMode ? 'ON' : 'OFF'}`} color="#059669" />
            <Chip testId="reverse-mode-chip" active={reverseMode} onClick={toggleReverse} icon={RotateCcw} label={`Reverse: ${reverseMode ? 'ON' : 'OFF'}`} color="#DC2626" />
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4" style={{ color: '#9CA3AF' }} />
              <input data-testid="min-pnl-input" type="number" step="0.25" min="0" value={minPnl} onChange={(e) => setMinPnl(e.target.value)}
                className="w-16 px-2.5 py-1.5 rounded-xl text-[13px] font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                style={{ background: '#F0F2F5', color: '#111827', border: '1px solid #E5E7EB' }} />
              <button data-testid="set-min-pnl-btn" onClick={applyMinPnl} className="px-3 py-1.5 rounded-xl text-[12px] font-medium" style={{ background: '#F0F2F5', color: '#6B7280' }}>Set</button>
            </div>
          </div>
          {reverseMode && (
            <div data-testid="reverse-mode-notice" className="p-4 rounded-xl text-[13px]" style={{ background: '#FEF2F2', color: '#991B1B', border: '1px solid #FECACA' }}>
              <strong>Reverse Mode Active</strong> — BUY signals execute as SELL, and vice versa.
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
      <span className="text-[12px]" style={{ color: '#6B7280' }}>{label}:</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="px-2.5 py-1.5 rounded-xl text-[12px] font-mono cursor-pointer focus:outline-none"
        style={{ background: '#fff', color: '#111827', border: '1px solid #E5E7EB' }}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

function Chip({ testId, active, onClick, icon: Icon, label, color }) {
  return (
    <button data-testid={testId} onClick={onClick}
      className="flex items-center gap-2 px-4 py-2 rounded-full text-[12px] font-semibold transition-all"
      style={{ background: active ? color : '#F0F2F5', color: active ? '#fff' : '#6B7280' }}>
      <Icon className="w-3.5 h-3.5" /> {label}
    </button>
  );
}
