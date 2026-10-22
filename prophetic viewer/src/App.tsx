import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import type { FulfillmentStatus, PassageDetail, PassageListItem, PredictiveStatus, ReviewStatus } from './types';

const labels: Record<string, string> = {
  unreviewed: 'Unreviewed', in_progress: 'In progress', reviewed: 'Reviewed', undetermined: 'Undetermined',
  predictive: 'Predictive', not_clearly_predictive: 'Not clearly predictive', not_assessed: 'Not assessed',
  no_fulfillment_identified: 'No fulfillment identified', proposed_fulfillment: 'Proposed fulfillment',
  textually_linked_fulfillment: 'Textually linked', disputed: 'Disputed'
};
const nice = (value: string) => labels[value] || value.replaceAll('_', ' ');

function Badge({ value, tone }: { value: string; tone?: string }) { return <span className={`badge ${tone || value}`}>{nice(value)}</span>; }

function EmptyCatalog() {
  return <div className="empty-state">
    <div className="empty-icon">⌁</div><h2>No catalog has been imported</h2>
    <p>The research database is ready. Place the provided catalog in <code>data/import/</code>, then run:</p>
    <pre>npm run import -- data/import/biblical_prediction_catalog_873.xlsx</pre>
    <p className="muted">CSV, XLSX, and XLS are supported. Missing records are never fabricated.</p>
  </div>;
}

function ReviewPanel({ id, close, refresh }: { id: number; close: () => void; refresh: () => void }) {
  const [item, setItem] = useState<PassageDetail | null>(null);
  const [showSource, setShowSource] = useState(false);
  const [saved, setSaved] = useState('');
  const [statementOpen, setStatementOpen] = useState(false);
  const load = useCallback(() => fetch(`/api/passages/${id}`).then(r => r.json()).then(setItem), [id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { const fn = (event: KeyboardEvent) => event.key === 'Escape' && close(); addEventListener('keydown', fn); return () => removeEventListener('keydown', fn); }, [close]);
  if (!item) return <aside className="drawer"><div className="loading">Loading evidence…</div></aside>;

  async function saveReview(event: FormEvent) {
    event.preventDefault(); setSaved('Saving…');
    const response = await fetch(`/api/passages/${id}/review`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(item) });
    if (!response.ok) { setSaved('Could not save'); return; }
    setSaved('Saved'); await load(); refresh(); setTimeout(() => setSaved(''), 1800);
  }
  async function addStatement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const response = await fetch(`/api/passages/${id}/statements`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (response.ok) { event.currentTarget.reset(); setStatementOpen(false); await load(); refresh(); }
  }
  return <aside className="drawer" aria-label="Passage review">
    <header className="drawer-head"><div><p className="eyebrow">Textual review</p><h2>{item.original_reference}</h2><p className="source-id">{item.source_name} · Record {item.original_source_id}</p></div><button className="icon-button" onClick={close} aria-label="Close">×</button></header>
    <div className="drawer-body">
      <section className="principle"><strong>Begin with the text.</strong><span>Imported interpretations remain hidden until you choose to compare them.</span></section>
      <section><div className="section-title"><h3>Passage text</h3><Badge value={item.text_source || 'No text source'} tone="neutral" /></div>
        {item.passage_text ? <blockquote>{item.passage_text}</blockquote> : <div className="text-missing">No licensed biblical text is attached. Consult the reference above; do not substitute a translation silently.</div>}
      </section>
      <form onSubmit={saveReview}>
        <section><h3>Textual assessment</h3><div className="form-grid">
          <label>Review status<select value={item.textual_review_status} onChange={e => setItem({ ...item, textual_review_status: e.target.value as ReviewStatus })}><option value="unreviewed">Unreviewed</option><option value="in_progress">In progress</option><option value="reviewed">Reviewed</option></select></label>
          <label>Predictive statement<select value={item.predictive_statement_status} onChange={e => setItem({ ...item, predictive_statement_status: e.target.value as PredictiveStatus })}><option value="undetermined">Undetermined</option><option value="predictive">Predictive</option><option value="not_clearly_predictive">Not clearly predictive</option></select></label>
          <label>Reviewed fulfillment status<select value={item.fulfillment_assessment_status} onChange={e => setItem({ ...item, fulfillment_assessment_status: e.target.value as FulfillmentStatus })}><option value="not_assessed">Not assessed</option><option value="no_fulfillment_identified">No fulfillment identified</option><option value="proposed_fulfillment">Proposed fulfillment</option><option value="textually_linked_fulfillment">Textually linked fulfillment</option><option value="disputed">Disputed</option><option value="undetermined">Undetermined</option></select></label>
        </div><label>Observations and evidence<textarea rows={5} value={item.review_notes} placeholder="Record textual observations, uncertainty, and supporting references…" onChange={e => setItem({ ...item, review_notes: e.target.value })} /></label>
        <div className="save-row"><button className="primary" type="submit">Save review</button><span className="save-status">{saved}</span></div></section>
      </form>
      <section><div className="section-title"><div><h3>Predictive statements</h3><p className="muted">A passage may contain zero, one, or several.</p></div><button className="secondary" onClick={() => setStatementOpen(!statementOpen)}>+ Add statement</button></div>
        {statementOpen && <form className="statement-form" onSubmit={addStatement}>
          <label className="full">Statement description<input name="description" required placeholder="Describe only what the text states or supports" /></label>
          <label>Spoken by<input name="speaker" /></label><label>Spoken of<input name="subject" /></label>
          <label>Predicted action or state<input name="predicted_action" /></label><label>Explicitness<select name="explicitness"><option value="undetermined">Undetermined</option><option value="explicit">Explicit</option><option value="inferred">Inferred</option><option value="hypothetical">Hypothetical</option></select></label>
          <label>Announcement timeframe<input name="announcement_time" placeholder="Unknown is acceptable" /></label><label>Predicted timeframe<input name="predicted_time" placeholder="Unknown is acceptable" /></label>
          <label className="full">Evidence notes<textarea name="evidence_notes" rows={3} /></label><button className="primary" type="submit">Add statement</button>
        </form>}
        <div className="statements">{item.statements.length ? item.statements.map(s => <article className="statement" key={s.id}><div><Badge value={s.explicitness} /><Badge value={s.review_status} tone="neutral" /></div><h4>{s.description}</h4><dl><div><dt>Spoken by</dt><dd>{s.speaker || 'Undetermined'}</dd></div><div><dt>Spoken of</dt><dd>{s.subject || 'Undetermined'}</dd></div><div><dt>Predicted time</dt><dd>{s.predicted_time || 'Unknown'}</dd></div></dl></article>) : <p className="muted boxed">No statements identified yet. This may be a valid negative finding.</p>}</div>
      </section>
      <section className="source-section"><button className="reveal" onClick={() => setShowSource(!showSource)}><span>{showSource ? 'Hide' : 'Reveal'} imported source metadata</span><span>{showSource ? '−' : '+'}</span></button>
        {showSource && <div className="source-content"><div className="warning">Source claims are discovery metadata—not reviewed findings.</div><dl><div><dt>Classification</dt><dd>{item.original_classification || 'Not provided'}</dd></div><div><dt>Fulfillment claim</dt><dd>{item.original_fulfillment_claim || 'Not provided'}</dd></div><div><dt>Payne mapping</dt><dd>{item.payne_mapping || 'Not provided'}</dd></div></dl>{item.original_source_url && <a href={item.original_source_url} target="_blank" rel="noreferrer">Open original study ↗</a>}</div>}
      </section>
      {item.history.length > 0 && <section><h3>Review history</h3><div className="history">{item.history.map(h => <div key={h.id}><span>{nice(h.field_name)}</span><small>{nice(h.previous_value)} → {nice(h.new_value)} · {new Date(h.changed_at + 'Z').toLocaleString()}</small></div>)}</div></section>}
    </div>
  </aside>;
}

export default function App() {
  const [items, setItems] = useState<PassageListItem[]>([]); const [books, setBooks] = useState<string[]>([]);
  const [selected, setSelected] = useState<number | null>(null); const [query, setQuery] = useState('');
  const [review, setReview] = useState(''); const [predictive, setPredictive] = useState(''); const [book, setBook] = useState('');
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => { setLoading(true); const params = new URLSearchParams({ ...(query && { q: query }), ...(review && { review }), ...(predictive && { predictive }), ...(book && { book }) }); const response = await fetch(`/api/passages?${params}`); setItems(await response.json()); setLoading(false); }, [query, review, predictive, book]);
  useEffect(() => { const timer = setTimeout(load, 180); return () => clearTimeout(timer); }, [load]);
  useEffect(() => { fetch('/api/books').then(r => r.json()).then(rows => setBooks(rows.map((r: {book:string}) => r.book))); }, []);
  const reviewed = useMemo(() => items.filter(i => i.textual_review_status === 'reviewed').length, [items]);
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/"><span className="brand-mark">S</span><span>Scripture<br />Prophecy Explorer</span></a><nav><a className="active" href="#prophecies"><span>▤</span>Prophecies</a><a className="disabled" title="Prepared for Phase 3"><span>⌁</span>Timeline</a><a className="disabled" title="Prepared for Phase 2"><span>◇</span>Events</a><a className="disabled" title="Prepared for Phase 2"><span>◉</span>Research Topics</a></nav><div className="sidebar-note"><span className="dot"></span><strong>Evidence first</strong><p>Observations, inferences, and source claims remain distinct.</p></div></aside>
    <main><header className="topbar"><div><p className="eyebrow">Research catalog</p><h1>Prophecies</h1><p>Examine candidate passages without presuming interpretation or fulfillment.</p></div><div className="summary"><strong>{items.length}</strong><span>records shown</span><strong>{reviewed}</strong><span>reviewed</span></div></header>
      <section className="workspace"><div className="filters"><label className="search"><span>⌕</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search reference, note, or source ID…" /></label><select aria-label="Book" value={book} onChange={e => setBook(e.target.value)}><option value="">All books</option>{books.map(b => <option key={b}>{b}</option>)}</select><select aria-label="Review status" value={review} onChange={e => setReview(e.target.value)}><option value="">All review states</option><option value="unreviewed">Unreviewed</option><option value="in_progress">In progress</option><option value="reviewed">Reviewed</option></select><select aria-label="Predictive status" value={predictive} onChange={e => setPredictive(e.target.value)}><option value="">All textual findings</option><option value="undetermined">Undetermined</option><option value="predictive">Predictive</option><option value="not_clearly_predictive">Not clearly predictive</option></select></div>
        {loading ? <div className="loading">Loading catalog…</div> : items.length === 0 && !query && !review && !predictive && !book ? <EmptyCatalog /> : <div className="table-wrap"><table><thead><tr><th>Scripture reference</th><th>Textual finding</th><th>Statements</th><th>Fulfillment assessment</th><th>Review</th><th></th></tr></thead><tbody>{items.map(item => <tr key={item.id} onClick={() => setSelected(item.id)}><td><strong>{item.original_reference}</strong><small>{item.source_name} · {item.original_source_id}</small></td><td><Badge value={item.predictive_statement_status} /></td><td>{item.statement_count}</td><td><Badge value={item.fulfillment_assessment_status} /></td><td><Badge value={item.textual_review_status} /></td><td className="arrow">›</td></tr>)}</tbody></table></div>}
      </section>
    </main>{selected && <><div className="scrim" onClick={() => setSelected(null)}></div><ReviewPanel id={selected} close={() => setSelected(null)} refresh={load} /></>}
  </div>;
}
