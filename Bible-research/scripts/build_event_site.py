#!/usr/bin/env python3
"""HTML event map: repeated predictions, speech order, utterance spine."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "prophecy.html"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> int:
    summary = load_json(ROOT / "prophecy" / "event_map_summary.json") or {}
    repeated = load_json(ROOT / "prophecy" / "repeated_events.json") or []
    speeches = load_json(ROOT / "prophecy" / "speech_sequences.json") or []
    threads = load_json(ROOT / "prophecy" / "name_threads.json") or []
    phrases = load_json(ROOT / "prophecy" / "text_phrases.json") or []
    events = load_jsonl(ROOT / "prophecy" / "events.jsonl")
    books = []
    seen = set()
    for e in events:
        b = e.get("book")
        if b and b not in seen:
            seen.add(b)
            books.append(b)
    payload = {
        "n_events": summary.get("predicted_clauses", len(events)),
        "n_types": summary.get("repeated_event_types", len(repeated)),
        "n_speeches": summary.get("speeches_with_sequence", len(speeches)),
        "n_names": summary.get("name_threads", len(threads)),
        "n_phrases": len(phrases),
        "phrases": [
            {
                "name": p["label"],
                "n": p["count"],
                "first": p["first"],
                "last": p["last"],
                "refs": p.get("refs") or [],
            }
            for p in phrases
        ],
        "threads": [
            {
                "name": t["name"],
                "n": t["count"],
                "first": t["first"],
                "last": t["last"],
                "acts": t.get("acts") or [],
                "refs": t.get("refs") or [],
            }
            for t in threads
        ],
        "repeated": [
            {
                "label": c["label"],
                "n": c["count"],
                "first": c["first"],
                "last": c["last"],
                "refs": c.get("refs") or [],
                "samples": c.get("samples") or [],
            }
            for c in repeated
        ],
        "speeches": [
            {
                "book": s["book"],
                "start": s["start"],
                "end": s["end"],
                "n": s["n"],
                "steps": s["steps"],
            }
            for s in speeches
        ],
        "spine": [
            {
                "r": e["ref"],
                "b": e.get("book"),
                "label": e["label"],
                "x": e["gloss"],
                "seq": e.get("seq") or [],
                "src": e.get("source") or "",
            }
            for e in events
        ],
        "books": books,
    }
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prophetic event map</title>
<style>
  :root{--bg:#faf9f7;--panel:#fff;--ink:#1c1a17;--muted:#6b6560;--faint:#928b84;
    --line:#e3ded7;--accent:#8a5a2b;--soft:#f3ece3;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font:15px/1.55 ui-serif,Georgia,"Times New Roman",serif;}
  header{padding:28px 32px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
  h1{margin:0 0 8px;font-size:24px;font-weight:600}
  .sub{color:var(--muted);max-width:78ch;margin:0}
  .stats{display:flex;gap:28px;flex-wrap:wrap;margin-top:16px}
  .stat b{display:block;font-size:22px;font-weight:600}
  .stat span{color:var(--faint);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
  nav{display:flex;gap:2px;padding:0 32px;background:var(--panel);
    border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
  nav button{border:0;background:none;padding:12px 16px;cursor:pointer;color:var(--muted);
    font:inherit;font-size:14px;border-bottom:2px solid transparent}
  nav button.on{color:var(--ink);border-bottom-color:var(--accent)}
  main{padding:24px 32px 80px;max-width:1100px}
  .note{background:var(--soft);border-left:3px solid var(--accent);
    padding:12px 16px;margin:0 0 20px;color:#5c4630;font-size:14px;max-width:84ch}
  .filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px}
  input,select{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);
    border-radius:5px;background:var(--panel)}
  input[type=search]{min-width:260px}
  .count{color:var(--faint);font-size:13px;margin:8px 0 12px}
  .v,.cluster{background:var(--panel);border:1px solid var(--line);border-radius:6px;
    padding:12px 14px;margin-bottom:10px}
  .ref{font-weight:600;margin-right:8px}
  .muted{color:var(--muted);font-size:13px}
  .gloss{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.65;
    color:#3d3833;background:#fbfaf8;border:1px solid var(--line);border-radius:4px;
    padding:8px 10px;margin:8px 0 0;white-space:pre-wrap}
  .tag{font-size:11.5px;padding:2px 8px;border-radius:11px;background:#f1ede7;
    color:#5f574e;font-family:system-ui,sans-serif;margin-right:6px;display:inline-block}
  .more{display:block;width:100%;padding:10px;margin-top:8px;font:inherit;font-size:14px;
    background:var(--panel);border:1px solid var(--line);border-radius:6px;cursor:pointer;color:var(--muted)}
  .hidden{display:none}
  .step{padding:8px 0;border-top:1px solid var(--line)}
  .step:first-child{border-top:0}
  .bookh{margin:22px 0 10px;font-size:18px;font-weight:600}
  .names{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
  .names button{font:inherit;font-size:13px;padding:5px 10px;border:1px solid var(--line);
    background:var(--panel);border-radius:14px;cursor:pointer;color:var(--muted)}
  .names button.on{background:var(--soft);color:var(--ink);border-color:var(--accent)}
</style>
</head>
<body>
<header>
  <h1>Prophetic event map</h1>
  <p class="sub">Predicted clauses are filed under the proper names they
  contain. Open a name to see every verse, in Protestant book order. A later
  quotation does not close an event. Order of happening is only marked when
  the clause itself says after / then / until.</p>
  <div class="stats" id="stats"></div>
</header>
<nav>
  <button data-tab="who" class="on">Named in the act</button>
  <button data-tab="phrase">Phrases the text uses</button>
  <button data-tab="rep">Same act repeated</button>
  <button data-tab="speech">Order inside a speech</button>
  <button data-tab="spine">Utterance spine</button>
</nav>
<main>
  <section id="who">
    <p class="note">Every predicted verse that names this person or place is
    here, in Protestant book order. Pick a name. First and last are when
    those sayings are spoken, not when the acts happen.</p>
    <div class="filters">
      <input type="search" id="qWho" placeholder="Filter names…">
    </div>
    <div class="names" id="nameBtns"></div>
    <p class="count" id="whoCount"></p>
    <div id="whoList"></div>
  </section>
  <section id="phrase" class="hidden">
    <p class="note">These piles are lemma pairs in the same clause, not a
    theological menu. Buttons are the text’s words: day + YHWH, day + Lord,
    distress + Jacob, exile, turn the captivity, return, latter days,
    thousand years, παρουσία, come + Jesus. A later book quoting a saying
    does not add it to a pile.</p>
    <div class="names" id="phraseBtns"></div>
    <p class="count" id="phraseCount"></p>
    <div id="phraseList"></div>
  </section>
  <section id="rep" class="hidden">
    <p class="note">Same verb and the same names in more than one verse.
    “First” and “last” are when that wording is spoken, not when it happens.</p>
    <div class="filters">
      <input type="search" id="qRep" placeholder="Search event or reference…">
    </div>
    <p class="count" id="repCount"></p>
    <div id="repList"></div>
    <button class="more hidden" id="repMore">Show more</button>
  </section>
  <section id="speech" class="hidden">
    <p class="note">When one prophetic speech names several coming acts, they
    are listed in the order the speech says them. A tag such as אחר or τότε
    means that word is in the clause.</p>
    <div class="filters">
      <select id="spBook"></select>
    </div>
    <p class="count" id="spCount"></p>
    <div id="spList"></div>
    <button class="more hidden" id="spMore">Show more</button>
  </section>
  <section id="spine" class="hidden">
    <p class="note">Coming acts in the order the books print the saying:
    yiqtol / weqatal / future under prophecy vocabulary, or under
    “and YHWH said” (I-will / he-will). “Do not fear” is a command, not an
    act. This is not the order the acts happen unless the clause says
    after / then / until.</p>
    <div class="filters">
      <input type="search" id="qSpine" placeholder="Search gloss or reference…">
      <select id="spnBook"></select>
    </div>
    <p class="count" id="spnCount"></p>
    <div id="spnList"></div>
    <button class="more hidden" id="spnMore">Show more</button>
  </section>
</main>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

$('#stats').innerHTML = [
  [D.n_names, 'names inside predicted acts'],
  [D.n_phrases, 'text phrases'],
  [D.n_types, 'same act said more than once'],
  [D.n_events, 'predicted clauses'],
  [D.n_speeches, 'speeches with more than one coming act'],
].map(([b,s]) => `<div class="stat"><b>${Number(b).toLocaleString()}</b><span>${s}</span></div>`).join('');

function fill(sel, label, values) {
  sel.innerHTML = `<option value="">${label}</option>` +
    values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
}
fill($('#spBook'), 'Any book', D.books);
fill($('#spnBook'), 'Any book', D.books);

const PAGE = 30;
let rShow = PAGE, sShow = PAGE, pShow = PAGE;
let whoName = (D.threads[0] && D.threads[0].name) || '';
let phraseName = (D.phrases[0] && D.phrases[0].name) || '';

function filteredNames() {
  const q = $('#qWho').value.trim().toLowerCase();
  return D.threads.filter(t => !q || (t.name||'').toLowerCase().includes(q));
}

function renderWho() {
  const names = filteredNames();
  if (whoName && !names.some(t => t.name === whoName)) {
    whoName = names[0] ? names[0].name : '';
  }
  $('#nameBtns').innerHTML = names.map(t =>
    `<button type="button" data-name="${esc(t.name)}" class="${t.name===whoName?'on':''}">${esc(t.name)}</button>`
  ).join('');
  const t = D.threads.find(x => x.name === whoName);
  if (!t) {
    $('#whoCount').textContent = 'No name selected.';
    $('#whoList').innerHTML = '';
    return;
  }
  $('#whoCount').textContent = `${t.name}: ${t.n} predicted verses, spoken from ${t.first} to ${t.last}`;
  $('#whoList').innerHTML = `
      <div>${(t.acts||[]).map(a => `<span class="tag">${esc(a.verb)}</span>`).join(' ')}</div>
    ${(t.refs||[]).map(r => `
      <article class="v">
        <span class="ref">${esc(r.ref)}</span>
        ${(r.verbs||[]).map(v => `<span class="tag">${esc(v)}</span>`).join('')}
        ${(r.seq||[]).map(x => `<span class="tag">${esc(x)}</span>`).join('')}
        <pre class="gloss">${esc(r.gloss)}</pre>
      </article>`).join('')}`;
}
$('#qWho').addEventListener('input', renderWho);
$('#nameBtns').addEventListener('click', e => {
  const b = e.target.closest('button[data-name]');
  if (!b) return;
  whoName = b.dataset.name;
  renderWho();
});

function renderPhrase() {
  $('#phraseBtns').innerHTML = D.phrases.map(t =>
    `<button type="button" data-name="${esc(t.name)}" class="${t.name===phraseName?'on':''}">${esc(t.name)}</button>`
  ).join('');
  const t = D.phrases.find(x => x.name === phraseName);
  if (!t) {
    $('#phraseCount').textContent = '';
    $('#phraseList').innerHTML = '';
    return;
  }
  $('#phraseCount').textContent = `${t.name}: ${t.n} verses, ${t.first} to ${t.last}`;
  $('#phraseList').innerHTML = (t.refs||[]).map(r => `
    <article class="v">
      <span class="ref">${esc(r.ref)}</span>
      <pre class="gloss">${esc(r.gloss)}</pre>
    </article>`).join('');
}
$('#phraseBtns').addEventListener('click', e => {
  const b = e.target.closest('button[data-name]');
  if (!b) return;
  phraseName = b.dataset.name;
  renderPhrase();
});

function renderRep() {
  const q = $('#qRep').value.trim().toLowerCase();
  const rows = D.repeated.filter(c =>
    !q || (c.label||'').toLowerCase().includes(q) || (c.first||'').toLowerCase().includes(q)
    || (c.refs||[]).some(r => r.toLowerCase().includes(q))
    || (c.samples||[]).some(s => (s.gloss||'').toLowerCase().includes(q))
  );
  $('#repCount').textContent = `${rows.length.toLocaleString()} event types`
    + (rows.length > rShow ? ` — showing ${rShow}` : '');
  $('#repList').innerHTML = rows.slice(0, rShow).map(c => `
    <article class="cluster">
      <div><strong>${esc(c.label)}</strong>
        <span class="tag">${c.n} verses</span>
        <span class="muted">spoken from ${esc(c.first)} to ${esc(c.last)}</span>
      </div>
      <div class="muted">${(c.refs||[]).slice(0,16).map(esc).join(' · ')}</div>
      ${(c.samples||[]).slice(0,3).map(s =>
        `<pre class="gloss"><span class="ref">${esc(s.ref)}</span>${esc(s.gloss)}</pre>`
      ).join('')}
    </article>`).join('') || '<p class="count">Nothing matches.</p>';
  $('#repMore').classList.toggle('hidden', rows.length <= rShow);
}
$('#qRep').addEventListener('input', () => { rShow = PAGE; renderRep(); });
$('#repMore').addEventListener('click', () => { rShow += 40; renderRep(); });

function renderSp() {
  const book = $('#spBook').value;
  const rows = D.speeches.filter(s => !book || s.book === book);
  $('#spCount').textContent = `${rows.length.toLocaleString()} speeches`
    + (rows.length > sShow ? ` — showing ${sShow}` : '');
  $('#spList').innerHTML = rows.slice(0, sShow).map(s => `
    <article class="cluster">
      <div><span class="ref">${esc(s.start)} → ${esc(s.end)}</span>
        <span class="muted">${s.n} coming acts in this speech</span></div>
      ${s.steps.map((t,i) => `
        <div class="step">
          <span class="muted">${i+1}.</span>
          <span class="ref">${esc(t.ref)}</span>
          ${(t.seq||[]).map(x => `<span class="tag">${esc(x)}</span>`).join('')}
          <span>${esc(t.label)}</span>
          <pre class="gloss">${esc(t.gloss)}</pre>
        </div>`).join('')}
    </article>`).join('') || '<p class="count">Nothing matches.</p>';
  $('#spMore').classList.toggle('hidden', rows.length <= sShow);
}
$('#spBook').addEventListener('input', () => { sShow = PAGE; renderSp(); });
$('#spMore').addEventListener('click', () => { sShow += 20; renderSp(); });

function renderSpine() {
  const q = $('#qSpine').value.trim().toLowerCase();
  const book = $('#spnBook').value;
  const rows = D.spine.filter(v =>
    (!book || v.b === book) &&
    (!q || (v.x||'').toLowerCase().includes(q) || (v.r||'').toLowerCase().includes(q)
      || (v.label||'').toLowerCase().includes(q))
  );
  let last = '';
  $('#spnCount').textContent = `${rows.length.toLocaleString()} clauses`
    + (rows.length > pShow ? ` — showing ${pShow}` : '');
  $('#spnList').innerHTML = rows.slice(0, pShow).map(v => {
    const head = v.b !== last ? `<h2 class="bookh">${esc(v.b)}</h2>` : '';
    last = v.b;
    return `${head}<article class="v">
      <span class="ref">${esc(v.r)}</span>
      <span class="muted">${esc(v.label)}</span>
      ${v.src==='divine_speech'?'<span class="tag">YHWH said</span>':''}
      ${(v.seq||[]).map(x => `<span class="tag">${esc(x)}</span>`).join('')}
      <pre class="gloss">${esc(v.x)}</pre>
    </article>`;
  }).join('') || '<p class="count">Nothing matches.</p>';
  $('#spnMore').classList.toggle('hidden', rows.length <= pShow);
}
['#qSpine','#spnBook'].forEach(s => $(s).addEventListener('input', () => { pShow = PAGE; renderSpine(); }));
$('#spnMore').addEventListener('click', () => { pShow += 80; renderSpine(); });

document.querySelectorAll('nav button').forEach(b =>
  b.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
    ['who','phrase','rep','speech','spine'].forEach(id =>
      $('#'+id).classList.toggle('hidden', id !== b.dataset.tab));
  }));
renderWho(); renderPhrase(); renderRep(); renderSp(); renderSpine();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
