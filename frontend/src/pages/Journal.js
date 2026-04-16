import React, { useState, useEffect, useCallback } from 'react';
import { fetchJSON, postJSON, formatMoney } from '../lib/api';
import {
  BookOpen, Plus, X, Star, Tag, Link2, Trash2, Edit3,
  TrendingUp, TrendingDown, ChevronDown, ChevronUp, Search
} from 'lucide-react';

const MOODS = [
  { value: 'confident', label: 'Confident', emoji: 'C', color: '#059669' },
  { value: 'disciplined', label: 'Disciplined', emoji: 'D', color: '#2563EB' },
  { value: 'anxious', label: 'Anxious', emoji: 'A', color: '#2563EB' },
  { value: 'fomo', label: 'FOMO', emoji: 'F', color: '#DC2626' },
  { value: 'greedy', label: 'Greedy', emoji: 'G', color: '#A78BFA' },
  { value: 'neutral', label: 'Neutral', emoji: 'N', color: '#6B7280' },
];

const GOLD = '#2563EB';

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
      // Use PUT via fetch
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'Roboto, sans-serif', color: '#111827' }}>
            Trade Journal
          </h2>
          <p className="text-sm mt-1" style={{ color: '#6B7280' }}>
            Document your trades, lessons learned, and track your growth as a trader
          </p>
        </div>
        <button
          data-testid="new-note-btn"
          onClick={() => { setEditingNote(null); setShowForm(true); }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all"
          style={{ background: GOLD, color: '#F0F2F5' }}
        >
          <Plus className="w-4 h-4" /> New Entry
        </button>
      </div>

      {/* Search + Stats */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#9CA3AF' }} />
          <input
            data-testid="journal-search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes, instruments, strategies..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border focus:outline-none transition-colors"
            style={{ background: '#FFFFFF', color: '#111827', borderColor: '#E5E7EB' }}
            onFocus={(e) => e.target.style.borderColor = GOLD}
            onBlur={(e) => e.target.style.borderColor = '#E5E7EB'}
          />
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-xs font-mono px-3 py-2 rounded-xl" style={{ background: '#FFFFFF', color: '#6B7280', border: '1px solid #E5E7EB' }}>
            {total} entries
          </span>
        </div>
      </div>

      {/* Tags cloud */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2" data-testid="tags-cloud">
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => setSearchQuery(tag)}
              className="px-2.5 py-1 rounded-full text-xs font-medium border transition-all"
              style={{
                background: searchQuery === tag ? 'rgba(245,158,11,0.12)' : 'transparent',
                color: searchQuery === tag ? GOLD : '#6B7280',
                borderColor: searchQuery === tag ? 'rgba(245,158,11,0.3)' : '#E5E7EB',
              }}
            >
              <Tag className="w-3 h-3 inline mr-1" />{tag}
            </button>
          ))}
        </div>
      )}

      {/* Note Form Modal */}
      {showForm && (
        <NoteForm
          note={editingNote}
          trades={trades}
          onSave={handleSave}
          onClose={() => { setShowForm(false); setEditingNote(null); }}
        />
      )}

      {/* Notes List */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border p-12 text-center" style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}>
          <BookOpen className="w-12 h-12 mx-auto mb-3" style={{ color: '#E5E7EB' }} />
          <p className="text-sm" style={{ color: '#9CA3AF' }}>
            {searchQuery ? 'No notes match your search' : 'Start documenting your trading journey'}
          </p>
          {!searchQuery && (
            <button
              onClick={() => { setEditingNote(null); setShowForm(true); }}
              className="mt-4 px-4 py-2 rounded-xl text-sm font-bold transition-all"
              style={{ background: GOLD, color: '#F0F2F5' }}
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
      className="rounded-2xl border overflow-hidden transition-all"
      style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}
    >
      {/* Header */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold" style={{ color: '#111827' }}>{note.title}</h4>
            {note.rating > 0 && (
              <div className="flex gap-0.5">
                {[1, 2, 3, 4, 5].map((s) => (
                  <Star key={s} className="w-3 h-3" style={{ color: s <= note.rating ? GOLD : '#E5E7EB' }} fill={s <= note.rating ? GOLD : 'none'} />
                ))}
              </div>
            )}
            {mood && (
              <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: `${mood.color}15`, color: mood.color, border: `1px solid ${mood.color}30` }}>
                {mood.label}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mt-1.5 flex-wrap">
            <span className="text-xs font-mono" style={{ color: '#9CA3AF' }}>
              {new Date(note.timestamp).toLocaleDateString()} {new Date(note.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            {hasTrade && (
              <span className="flex items-center gap-1 text-xs font-mono" style={{ color: '#6B7280' }}>
                <Link2 className="w-3 h-3" />
                {note.instrument} {note.direction}
                {pnl != null && (
                  <span style={{ color: pnl >= 0 ? '#059669' : '#DC2626' }}>
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
                <span key={tag} className="px-2 py-0.5 rounded text-xs" style={{ background: '#F0F2F5', color: '#6B7280' }}>
                  {tag.trim()}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button data-testid={`edit-note-${note.id}`} onClick={(e) => { e.stopPropagation(); onEdit(); }} className="p-1.5 rounded transition-colors" style={{ color: '#9CA3AF' }}>
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button data-testid={`delete-note-${note.id}`} onClick={(e) => { e.stopPropagation(); onDelete(); }} className="p-1.5 rounded transition-colors" style={{ color: '#9CA3AF' }}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          {expanded ? <ChevronUp className="w-4 h-4" style={{ color: '#9CA3AF' }} /> : <ChevronDown className="w-4 h-4" style={{ color: '#9CA3AF' }} />}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t" style={{ borderColor: '#E5E7EB' }}>
          {note.content && (
            <div className="pt-3">
              <p className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: '#6B7280' }}>{note.content}</p>
            </div>
          )}
          {note.lessons && (
            <div className="p-3 rounded-xl" style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#059669' }}>Lessons Learned</span>
              <p className="text-sm mt-1 whitespace-pre-wrap" style={{ color: '#6B7280' }}>{note.lessons}</p>
            </div>
          )}
          {note.mistakes && (
            <div className="p-3 rounded-xl" style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#DC2626' }}>Mistakes to Avoid</span>
              <p className="text-sm mt-1 whitespace-pre-wrap" style={{ color: '#6B7280' }}>{note.mistakes}</p>
            </div>
          )}
          {hasTrade && (
            <div className="p-3 rounded-xl" style={{ background: '#F0F2F5' }}>
              <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9CA3AF' }}>Linked Trade</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2">
                <MiniStat label="Instrument" value={note.instrument} />
                <MiniStat label="Direction" value={note.direction} color={note.direction === 'BUY' ? '#059669' : '#DC2626'} />
                <MiniStat label="P&L" value={formatMoney(note.pnl)} color={note.pnl >= 0 ? '#059669' : '#DC2626'} />
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
      <div className="text-xs" style={{ color: '#9CA3AF' }}>{label}</div>
      <div className="text-xs font-mono font-semibold" style={{ color: color || '#fff' }}>{value}</div>
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

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 sm:pt-16 px-4" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div
        data-testid="journal-note-form"
        className="w-full max-w-2xl rounded-2xl border overflow-hidden max-h-[85vh] overflow-y-auto"
        style={{ background: '#FFFFFF', borderColor: '#E5E7EB' }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: '#E5E7EB' }}>
          <h3 className="text-lg font-bold" style={{ fontFamily: 'Roboto, sans-serif', color: '#111827' }}>
            {note ? 'Edit Entry' : 'New Journal Entry'}
          </h3>
          <button data-testid="close-form-btn" onClick={onClose} className="p-1" style={{ color: '#9CA3AF' }}>
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>Title *</label>
            <input
              data-testid="note-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Gold breakout trade - followed the plan"
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
              required
            />
          </div>

          {/* Link Trade */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>
              <Link2 className="w-3 h-3 inline mr-1" />Link to Trade (optional)
            </label>
            <select
              data-testid="link-trade-select"
              value={tradeId}
              onChange={(e) => setTradeId(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none cursor-pointer"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
            >
              <option value="">No linked trade</option>
              {trades.map((t) => (
                <option key={t.id} value={t.id}>
                  #{t.id} {t.instrument} {t.direction} {formatMoney(t.pnl)} ({t.strategy_name || 'no strategy'})
                </option>
              ))}
            </select>
          </div>

          {/* Rating + Mood */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>Trade Quality</label>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((s) => (
                  <button
                    key={s}
                    type="button"
                    data-testid={`rating-star-${s}`}
                    onClick={() => setRating(s === rating ? 0 : s)}
                    className="p-1 transition-colors"
                  >
                    <Star className="w-5 h-5" style={{ color: s <= rating ? GOLD : '#E5E7EB' }} fill={s <= rating ? GOLD : 'none'} />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>Trading Mood</label>
              <div className="flex flex-wrap gap-1.5">
                {MOODS.map((m) => (
                  <button
                    key={m.value}
                    type="button"
                    data-testid={`mood-btn-${m.value}`}
                    onClick={() => setMood(mood === m.value ? '' : m.value)}
                    className="px-2.5 py-1 rounded-full text-xs font-semibold border transition-all"
                    style={{
                      background: mood === m.value ? `${m.color}15` : 'transparent',
                      color: mood === m.value ? m.color : '#9CA3AF',
                      borderColor: mood === m.value ? `${m.color}40` : '#E5E7EB',
                    }}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>Notes</label>
            <textarea
              data-testid="note-content-input"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="What happened? What was your analysis?"
              rows={4}
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none resize-y"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
            />
          </div>

          {/* Lessons */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#059669' }}>Lessons Learned</label>
            <textarea
              data-testid="note-lessons-input"
              value={lessons}
              onChange={(e) => setLessons(e.target.value)}
              placeholder="What did this trade teach you?"
              rows={2}
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none resize-y"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
            />
          </div>

          {/* Mistakes */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#DC2626' }}>Mistakes to Avoid</label>
            <textarea
              data-testid="note-mistakes-input"
              value={mistakes}
              onChange={(e) => setMistakes(e.target.value)}
              placeholder="What would you do differently?"
              rows={2}
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none resize-y"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#9CA3AF' }}>Tags (comma separated)</label>
            <input
              data-testid="note-tags-input"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="e.g. gold, breakout, followed-plan, high-volatility"
              className="w-full px-3 py-2 rounded-xl text-sm border focus:outline-none"
              style={{ background: '#F0F2F5', color: '#111827', borderColor: '#E5E7EB' }}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              data-testid="save-note-btn"
              type="submit"
              className="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all"
              style={{ background: GOLD, color: '#F0F2F5' }}
            >
              {note ? 'Update Entry' : 'Save Entry'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 rounded-xl text-sm font-semibold border transition-all"
              style={{ color: '#6B7280', borderColor: '#E5E7EB' }}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
