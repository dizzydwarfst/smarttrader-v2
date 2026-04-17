import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, postJSON, formatMoney } from '../lib/api';
import {
  BookOpen, Plus, X, Star, Tag, Link2, Trash2, Edit3,
  TrendingUp, TrendingDown, ChevronDown, ChevronUp, Search
} from 'lucide-react';

const GOLD = '#2563EB';
const GREEN = '#059669';
const RED = '#DC2626';
const SURFACE = '#FFFFFF';
const SURFACE_ALT = '#F1F5F9';
const BG = '#F8FAFC';
const BORDER = '#E2E8F0';
const TEXT = '#0F172A';
const TEXT_SECONDARY = '#475569';
const TEXT_MUTED = '#94A3B8';

const MOODS = [
  { value: 'confident', label: 'Confident', color: GREEN },
  { value: 'disciplined', label: 'Disciplined', color: '#2563EB' },
  { value: 'anxious', label: 'Anxious', color: '#D97706' },
  { value: 'fomo', label: 'FOMO', color: RED },
  { value: 'greedy', label: 'Greedy', color: '#7C3AED' },
  { value: 'neutral', label: 'Neutral', color: TEXT_MUTED },
];

export default function Journal() {
  const [notes, setNotes] = useState([]);
  const [total, setTotal] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [editingNote, setEditingNote] = useState(null);
  const [trades, setTrades] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  const fetchNotes = useCallback(async () => {
    const data = await fetchJSON('/api/journal/notes?limit=50');
    if (data) {
      setNotes(data.notes || []);
      setTotal(data.total || 0);
    }
  }, []);

  const fetchTrades = useCallback(async () => {
    const data = await fetchJSON('/api/journal/trades-for-linking?days=60');
    if (data) setTrades(data);
  }, []);

  const fetchTags = useCallback(async () => {
    const data = await fetchJSON('/api/journal/tags');
    if (data) setAllTags(data);
  }, []);

  useEffect(() => {
    fetchNotes();
    fetchTrades();
    fetchTags();
  }, [fetchNotes, fetchTrades, fetchTags]);

  const handleSave = async (noteData) => {
    if (editingNote) {
      await postJSON(`/api/journal/notes/${editingNote.id}`, { ...noteData, _method: 'PUT' });
      await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/journal/notes/${editingNote.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(noteData),
      });
    } else {
      await postJSON('/api/journal/notes', noteData);
    }
    setShowForm(false);
    setEditingNote(null);
    fetchNotes();
    fetchTags();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this journal note?')) return;
    await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/journal/notes/${id}`, { method: 'DELETE' });
    fetchNotes();
  };

  const handleEdit = (note) => {
    setEditingNote(note);
    setShowForm(true);
  };

  const filtered = notes.filter((n) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      n.title?.toLowerCase().includes(q) ||
      n.content?.toLowerCase().includes(q) ||
      n.tags?.toLowerCase().includes(q) ||
      n.instrument?.toLowerCase().includes(q) ||
      n.strategy_name?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 animate-fade-in" data-testid="journal-page">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-[22px] font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif', color: TEXT }}>
            Trade Journal
          </h2>
          <p className="text-[13px] mt-1" style={{ color: TEXT_SECONDARY }}>
            Document your trades, lessons learned, and track your growth as a trader
          </p>
        </div>
        <button
          data-testid="new-note-btn"
          onClick={() => { setEditingNote(null); setShowForm(true); }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[13px] font-bold transition-all"
          style={{ background: GOLD, color: BG }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#1D4ED8'}
          onMouseLeave={(e) => e.currentTarget.style.background = GOLD}
        >
          <Plus className="w-4 h-4" /> New Entry
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: TEXT_MUTED }} />
          <input
            data-testid="journal-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes, instruments, strategies..."
            className="w-full pl-10 pr-4 py-2.5 rounded-lg text-[13px] focus:outline-none transition-colors"
            style={{ background: SURFACE, color: TEXT, border: `1px solid ${BORDER}` }}
            onFocus={(e) => e.target.style.borderColor = GOLD}
            onBlur={(e) => e.target.style.borderColor = BORDER}
          />
        </div>
        <span className="text-[12px] font-mono px-3 py-2.5 rounded-lg" style={{ background: SURFACE, color: TEXT_SECONDARY, border: `1px solid ${BORDER}` }}>
          {total} entries
        </span>
      </div>

      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid="tags-cloud">
          {allTags.map((tag) => {
            const active = searchQuery === tag;
            return (
              <button
                key={tag}
                onClick={() => setSearchQuery(tag)}
                className="px-2.5 py-1 rounded-full text-[11px] font-medium transition-all"
                style={{
                  background: active ? 'rgba(37,99,235,0.12)' : 'transparent',
                  color: active ? GOLD : TEXT_SECONDARY,
                  border: `1px solid ${active ? 'rgba(37,99,235,0.3)' : BORDER}`,
                }}
              >
                <Tag className="w-3 h-3 inline mr-1" />{tag}
              </button>
            );
          })}
        </div>
      )}

      {showForm && (
        <NoteForm
          note={editingNote}
          trades={trades}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditingNote(null); }}
        />
      )}

      {filtered.length === 0 ? (
        <div className="rounded-xl p-12 text-center" style={{ background: SURFACE, border: `1px solid ${BORDER}` }}>
          <BookOpen className="w-12 h-12 mx-auto mb-3" style={{ color: TEXT_MUTED }} />
          <p className="text-[13px]" style={{ color: TEXT_SECONDARY }}>
            {searchQuery ? 'No notes match your search' : 'Start documenting your trading journey'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => { setEditingNote(null); setShowForm(true); }}
              className="mt-4 px-4 py-2.5 rounded-lg text-[13px] font-bold transition-all"
              style={{ background: GOLD, color: BG }}
            >
              Write your first entry
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((note) => (
            <NoteCard
              key={note.id}
              note={note}
              expanded={expandedId === note.id}
              onToggle={() => setExpandedId(expandedId === note.id ? null : note.id)}
              onEdit={() => handleEdit(note)}
              onDelete={() => handleDelete(note.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function NoteCard({ note, expanded, onToggle, onEdit, onDelete }) {
  const mood = MOODS.find((m) => m.value === note.mood);
  const pnl = note.pnl;
  const hasTrade = note.trade_id && note.instrument;

  return (
    <div
      data-testid={`journal-note-${note.id}`}
      className="rounded-xl overflow-hidden transition-all"
      style={{ background: SURFACE, border: `1px solid ${BORDER}` }}
    >
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-[14px] font-semibold" style={{ color: TEXT }}>{note.title}</h4>
            {note.rating > 0 && (
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star key={s} className="w-3 h-3" style={{ color: s <= note.rating ? GOLD : BORDER }} fill={s <= note.rating ? GOLD : 'none'} />
                ))}
              </div>
            )}
            {mood && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold" style={{ background: `${mood.color}15`, color: mood.color, border: `1px solid ${mood.color}30` }}>
                {mood.label}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className="text-[11px] font-mono" style={{ color: TEXT_MUTED }}>
              {new Date(note.timestamp).toLocaleDateString()} {new Date(note.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            {hasTrade && (
              <span className="flex items-center gap-1 text-[11px] font-mono" style={{ color: TEXT_SECONDARY }}>
                <Link2 className="w-3 h-3" />
                {note.instrument} {note.direction}
                {pnl != null && (
                  <span style={{ color: pnl >= 0 ? GREEN : RED }}>
                    {pnl >= 0 ? <TrendingUp className="w-3 h-3 inline" /> : <TrendingDown className="w-3 h-3 inline" />}
                    {formatMoney(pnl)}
                  </span>
                )}
              </span>
            )}
          </div>

          {note.tags && (
            <div className="flex gap-1.5 mt-2 flex-wrap">
              {note.tags.split(',').filter(Boolean).map((tag) => (
                <span key={tag} className="px-2 py-0.5 rounded text-[11px]" style={{ background: SURFACE_ALT, color: TEXT_SECONDARY }}>
                  {tag.trim()}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button data-testid={`edit-note-${note.id}`} onClick={(e) => { e.stopPropagation(); onEdit(); }} className="p-1.5 rounded transition-colors" style={{ color: TEXT_MUTED }}
            onMouseEnter={(e) => e.currentTarget.style.color = GOLD}
            onMouseLeave={(e) => e.currentTarget.style.color = TEXT_MUTED}>
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button data-testid={`delete-note-${note.id}`} onClick={(e) => { e.stopPropagation(); onDelete(); }} className="p-1.5 rounded transition-colors" style={{ color: TEXT_MUTED }}
            onMouseEnter={(e) => e.currentTarget.style.color = RED}
            onMouseLeave={(e) => e.currentTarget.style.color = TEXT_MUTED}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          {expanded ? <ChevronUp className="w-4 h-4" style={{ color: TEXT_MUTED }} /> : <ChevronDown className="w-4 h-4" style={{ color: TEXT_MUTED }} />}
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t" style={{ borderColor: BORDER }}>
          {note.content && (
            <div className="pt-3">
              <p className="text-[13px] whitespace-pre-wrap leading-relaxed" style={{ color: TEXT_SECONDARY }}>{note.content}</p>
            </div>
          )}
          {note.lessons && (
            <div className="p-3 rounded-lg" style={{ background: 'rgba(5,150,105,0.08)', border: '1px solid rgba(5,150,105,0.2)' }}>
              <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: GREEN }}>Lessons Learned</span>
              <p className="text-[13px] mt-1 whitespace-pre-wrap" style={{ color: TEXT_SECONDARY }}>{note.lessons}</p>
            </div>
          )}
          {note.mistakes && (
            <div className="p-3 rounded-lg" style={{ background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)' }}>
              <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: RED }}>Mistakes to Avoid</span>
              <p className="text-[13px] mt-1 whitespace-pre-wrap" style={{ color: TEXT_SECONDARY }}>{note.mistakes}</p>
            </div>
          )}
          {hasTrade && (
            <div className="p-3 rounded-lg" style={{ background: BG, border: `1px solid ${BORDER}` }}>
              <span className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: TEXT_MUTED }}>Linked Trade</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                <MiniStat label="Instrument" value={note.instrument} />
                <MiniStat label="Direction" value={note.direction} color={note.direction === 'BUY' ? GREEN : RED} />
                <MiniStat label="P&L" value={formatMoney(note.pnl)} color={note.pnl >= 0 ? GREEN : RED} />
                <MiniStat label="Strategy" value={note.strategy_name || '--'} color={GOLD} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest" style={{ color: TEXT_MUTED }}>{label}</div>
      <div className="text-[12px] font-mono font-semibold" style={{ color: color || TEXT }}>{value}</div>
    </div>
  );
}

function NoteForm({ note, trades, onSave, onClose }) {
  const [title, setTitle] = useState(note?.title || '');
  const [content, setContent] = useState(note?.content || '');
  const [tags, setTags] = useState(note?.tags || '');
  const [rating, setRating] = useState(note?.rating || 0);
  const [mood, setMood] = useState(note?.mood || '');
  const [lessons, setLessons] = useState(note?.lessons || '');
  const [mistakes, setMistakes] = useState(note?.mistakes || '');
  const [tradeId, setTradeId] = useState(note?.trade_id || '');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      title,
      content,
      tags,
      rating,
      mood,
      lessons,
      mistakes,
      trade_id: tradeId || null,
    });
  };

  const inputStyle = { background: BG, color: TEXT, border: `1px solid ${BORDER}` };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 sm:pt-16 px-4" style={{ background: 'rgba(0,0,0,0.78)', backdropFilter: 'blur(4px)' }}>
      <div
        data-testid="journal-note-form"
        className="w-full max-w-2xl rounded-xl overflow-hidden max-h-[85vh] overflow-y-auto"
        style={{ background: SURFACE, border: `1px solid ${BORDER}`, boxShadow: '0 20px 60px rgba(0,0,0,0.6)' }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: BORDER }}>
          <h3 className="text-[16px] font-bold" style={{ fontFamily: 'Outfit, sans-serif', color: TEXT }}>
            {note ? 'Edit Entry' : 'New Journal Entry'}
          </h3>
          <button data-testid="close-form-btn" onClick={onClose} className="p-1 transition-colors" style={{ color: TEXT_MUTED }}
            onMouseEnter={(e) => e.currentTarget.style.color = TEXT}
            onMouseLeave={(e) => e.currentTarget.style.color = TEXT_MUTED}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <Field label="Title *">
            <input
              data-testid="note-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Gold breakout trade - followed the plan"
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none"
              style={inputStyle}
              required
            />
          </Field>

          <Field label={<><Link2 className="w-3 h-3 inline mr-1" />Link to Trade (optional)</>}>
            <select
              data-testid="link-trade-select"
              value={tradeId}
              onChange={(e) => setTradeId(e.target.value)}
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none cursor-pointer"
              style={inputStyle}
            >
              <option value="">No linked trade</option>
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  #{t.id} {t.instrument} {t.direction} {formatMoney(t.pnl)} ({t.strategy_name || 'no strategy'})
                </option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Trade Quality">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((s) => (
                  <button
                    key={s}
                    type="button"
                    data-testid={`rating-star-${s}`}
                    onClick={() => setRating(s === rating ? 0 : s)}
                    className="p-1 transition-colors"
                  >
                    <Star className="w-5 h-5" style={{ color: s <= rating ? GOLD : BORDER }} fill={s <= rating ? GOLD : 'none'} />
                  </button>
                ))}
              </div>
            </Field>
            <Field label="Trading Mood">
              <div className="flex flex-wrap gap-1.5">
                {MOODS.map((m) => {
                  const act = mood === m.value;
                  return (
                    <button
                      key={m.value}
                      type="button"
                      data-testid={`mood-btn-${m.value}`}
                      onClick={() => setMood(act ? '' : m.value)}
                      className="px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all"
                      style={{
                        background: act ? `${m.color}15` : 'transparent',
                        color: act ? m.color : TEXT_SECONDARY,
                        border: `1px solid ${act ? `${m.color}50` : BORDER}`,
                      }}
                    >
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </Field>
          </div>

          <Field label="Notes">
            <textarea
              data-testid="note-content-input"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What happened? What was your analysis?"
              rows={4}
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none resize-y"
              style={inputStyle}
            />
          </Field>

          <Field label="Lessons Learned" labelColor={GREEN}>
            <textarea
              data-testid="note-lessons-input"
              value={lessons}
              onChange={(e) => setLessons(e.target.value)}
              placeholder="What did this trade teach you?"
              rows={2}
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none resize-y"
              style={inputStyle}
            />
          </Field>

          <Field label="Mistakes to Avoid" labelColor={RED}>
            <textarea
              data-testid="note-mistakes-input"
              value={mistakes}
              onChange={(e) => setMistakes(e.target.value)}
              placeholder="What would you do differently?"
              rows={2}
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none resize-y"
              style={inputStyle}
            />
          </Field>

          <Field label="Tags (comma separated)">
            <input
              data-testid="note-tags-input"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. gold, breakout, followed-plan, high-volatility"
              className="w-full px-3 py-2 rounded-lg text-[13px] focus:outline-none"
              style={inputStyle}
            />
          </Field>

          <div className="flex gap-3 pt-2">
            <button
              data-testid="save-note-btn"
              type="submit"
              className="flex-1 py-2.5 rounded-lg text-[13px] font-bold transition-all"
              style={{ background: GOLD, color: BG }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#1D4ED8'}
              onMouseLeave={(e) => e.currentTarget.style.background = GOLD}
            >
              {note ? 'Update Entry' : 'Save Entry'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 rounded-lg text-[13px] font-semibold transition-all"
              style={{ color: TEXT_SECONDARY, border: `1px solid ${BORDER}`, background: SURFACE_ALT }}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, labelColor, children }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold uppercase tracking-widest mb-1.5" style={{ color: labelColor || TEXT_MUTED }}>{label}</label>
      {children}
    </div>
  );
}
