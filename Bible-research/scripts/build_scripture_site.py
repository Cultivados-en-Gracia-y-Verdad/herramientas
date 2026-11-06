#!/usr/bin/env python3
"""One HTML page from text-internal tags only.

Sources allowed here:
  prophecy/frames.jsonl          — clauses with the text's prophecy vocabulary
  prophecy/divine_speech.jsonl   — YHWH/Elohim said/spoke (not called prophecy)
  prophecy/text_fulfillments.jsonl — clauses that say a word was fulfilled
  data/prophet_roster.json       — names the text puts next to נביא or as subject of נבא

No theme list. No event timeline. No outside quotation index.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "prophecy.html"


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def ref_of(row: dict) -> str:
    return row.get("ref_protestant") or row.get("ref") or ""


def card(row: dict) -> dict:
    return {
        "r": ref_of(row),
        "b": row.get("book") or "",
        "tags": row.get("frame_tags") or row.get("markers") or [],
        "x": (row.get("own_gloss") or "")[:400],
        "v": row.get("verb_english") or row.get("verb_lemma") or "",
    }


def verse_card(row: dict) -> dict:
    return {
        "r": row.get("ref_protestant") or row.get("ref") or "",
        "b": row.get("book") or "",
        "tags": row.get("tags") or [],
        "x": (row.get("own_gloss") or "")[:500],
        "status": row.get("status") or "",
    }


def main() -> int:
    frames = load_jsonl(ROOT / "prophecy" / "frames.jsonl")
    divine = load_jsonl(ROOT / "prophecy" / "divine_speech.jsonl")
    unful = load_jsonl(ROOT / "prophecy" / "unfulfilled.jsonl")
    ful = load_jsonl(ROOT / "prophecy" / "fulfilled.jsonl")
    roster = {}
    rp = ROOT / "data" / "prophet_roster.json"
    if rp.exists():
        roster = json.loads(rp.read_text(encoding="utf-8"))

    tag_n = Counter()
    for r in unful:
        for t in r.get("tags") or []:
            tag_n[t] += 1

    books = sorted({r.get("book") for r in unful if r.get("book")})
    payload = {
        "unful": [verse_card(r) for r in unful],
        "ful": [verse_card(r) for r in ful],
        "frames": [card(r) for r in frames],
        "divine": [card(r) for r in divine],
        "fills": [verse_card(r) for r in ful],
        "roster": [
            {
                "lemma": lem,
                "english": info.get("english"),
                "called_prophet": info.get("called_prophet"),
                "subject_of_prophesy": info.get("subject_of_prophesy"),
                "refs": info.get("refs") or [],
            }
            for lem, info in sorted(
                roster.items(),
                key=lambda kv: -(kv[1].get("called_prophet", 0) + kv[1].get("subject_of_prophesy", 0)),
            )
        ],
        "tag_counts": dict(tag_n.most_common()),
        "books": books,
        "n_frames": len(frames),
        "n_divine": len(divine),
        "n_unful": len(unful),
        "n_ful": len(ful),
    }

    html = TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}  unfulfilled={len(unful)} fulfilled={len(ful)} divine={len(divine)}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prophecy verses — fulfilled or unfulfilled</title>
<style>
  :root{--bg:#faf9f7;--panel:#fff;--ink:#1c1a17;--muted:#6b6560;--faint:#928b84;
    --line:#e3ded7;--accent:#8a5a2b;--soft:#f3ece3;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font:15px/1.55 ui-serif,Georgia,"Times New Roman",serif;}
  header{padding:28px 32px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
  h1{margin:0 0 8px;font-size:24px;font-weight:600}
  .sub{color:var(--muted);max-width:72ch;margin:0}
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
    padding:12px 16px;margin:0 0 20px;color:#5c4630;font-size:14px;max-width:80ch}
  .filters{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}
  input,select{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);
    border-radius:5px;background:var(--panel)}
  input[type=search]{min-width:260px}
  .count{color:var(--faint);font-size:13px;margin:8px 0 12px}
  .v{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px;margin-bottom:8px}
  .ref{font-weight:600;margin-right:10px}
  .gloss{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.65;
    color:#3d3833;background:#fbfaf8;border:1px solid var(--line);border-radius:4px;
    padding:8px 10px;margin:8px 0 0;white-space:pre-wrap}
  .tag{font-size:11.5px;padding:2px 8px;border-radius:11px;background:#f1ede7;
    color:#5f574e;font-family:system-ui,sans-serif;margin-right:6px;display:inline-block}
  .bookh{margin:22px 0 10px;font-size:18px;font-weight:600}
  .more{display:block;width:100%;padding:10px;margin-top:8px;font:inherit;font-size:14px;
    background:var(--panel);border:1px solid var(--line);border-radius:6px;cursor:pointer;color:var(--muted)}
  table{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--line)}
  th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);font-size:14px;vertical-align:top}
  th{background:#f6f3ef;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
  .hidden{display:none}
  .refs{color:var(--faint);font-size:13px}
</style>
</head>
<body>
<header>
  <h1>Fulfilled or unfulfilled</h1>
  <p class="sub">A prophecy-marked verse is <em>fulfilled</em> only when a
  clause on that same verse uses fulfillment language. Every other
  prophecy-marked verse is <em>unfulfilled</em>. That is not a date, and it
  is not a “still future” claim. Quotation in another book does not close
  the verse. Divine speech (“YHWH said”) is listed apart: the text
  attributes speech; it does not call that speech prophecy. Protestant
  numbering is a citation label. The gloss is MACULA word-by-word, not a
  translation.</p>
  <div class="stats" id="stats"></div>
</header>
<nav>
  <button data-tab="unful" class="on">Unfulfilled</button>
  <button data-tab="ful">Fulfilled</button>
  <button data-tab="divine">Divine speech (not called prophecy)</button>
  <button data-tab="names">Names the text calls prophet</button>
</nav>
<main>
  <section id="unful">
    <p class="note">One row per marked verse, in Protestant Bible order
    (Genesis → Revelation), then chapter, then verse. Rows are not grouped
    into speeches. Tags name the words found in that verse only:
    <em>thus says YHWH</em>, <em>utterance</em>, <em>vision</em>, and so on.
    A later verse in the same chapter is a new row, not a continuation
    heading.</p>
    <div class="filters">
      <input type="search" id="q" placeholder="Search gloss or reference…">
      <select id="fBook"></select>
      <select id="fTag"></select>
    </div>
    <p class="count" id="count"></p>
    <div id="list"></div>
    <button class="more hidden" id="more">Show more</button>
  </section>
  <section id="ful" class="hidden">
    <p class="note">Only verses whose own clause uses מלא/קום + דבר + יהוה/נביא,
    or πληρόω + γραφή/προφήτης. The row is the verse that makes the claim.
    It does not name an event and does not point at a different verse as
    “the prophecy that was meant.”</p>
    <p class="count" id="fcount"></p>
    <div id="flist"></div>
  </section>
  <section id="divine" class="hidden">
    <p class="note">YHWH or Elohim is the grammatical subject of אמר or דבר.
    Listed so it is not mixed with prophecy vocabulary. Speech <em>to</em>
    YHWH is not here.</p>
    <p class="count" id="dcount"></p>
    <div id="dlist"></div>
    <button class="more hidden" id="dmore">Show more</button>
  </section>
  <section id="names" class="hidden">
    <p class="note">A proper noun stands next to נביא / נביאה, or is the
    subject of נבא. That is the text’s designation. Construct “prophets of
    Baal / of YHWH” is not treated as a personal name.</p>
    <table id="roster"></table>
  </section>
</main>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

$('#stats').innerHTML = [
  [D.n_unful, 'unfulfilled verses'],
  [D.n_ful, 'fulfilled verses (text says so)'],
  [D.n_divine, 'divine-speech clauses'],
  [D.roster.length, 'names the text calls prophet'],
].map(([b,s]) => `<div class="stat"><b>${Number(b).toLocaleString()}</b><span>${s}</span></div>`).join('');

function fill(sel, label, values) {
  sel.innerHTML = `<option value="">${label}</option>` +
    values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
}
fill($('#fBook'), 'Any book', D.books);
fill($('#fTag'), 'Any marker', Object.keys(D.tag_counts));

const PAGE = 50;
let shown = PAGE;
let dshown = PAGE;

function renderCards(rows, into, limit, byBook) {
  let last = '';
  const html = rows.slice(0, limit).map(v => {
    const head = (byBook && v.b !== last)
      ? `<h2 class="bookh">${esc(v.b)}</h2>` : '';
    last = v.b;
    const tags = (v.tags||[]).map(t => `<span class="tag">${esc(t.replace(/_/g,' '))}</span>`).join(' ');
    return `${head}
    <article class="v">
      <span class="ref">${esc(v.r)}</span>
      ${tags}
      <pre class="gloss">${esc(v.x)}</pre>
    </article>`;
  }).join('');
  return html || '<p class="count">Nothing matches.</p>';
}

function currentUnful() {
  const q = $('#q').value.trim().toLowerCase();
  const book = $('#fBook').value, tag = $('#fTag').value;
  return D.unful.filter(v =>
    (!book || v.b === book) && (!tag || (v.tags||[]).includes(tag)) &&
    (!q || (v.x||'').toLowerCase().includes(q) || (v.r||'').toLowerCase().includes(q))
  );
}

function renderUnful() {
  const rows = currentUnful();
  $('#count').textContent = `${rows.length.toLocaleString()} verses`
    + (rows.length > shown ? ` — showing ${shown}` : '');
  $('#list').innerHTML = renderCards(rows, '#list', shown, true);
  $('#more').classList.toggle('hidden', rows.length <= shown);
}

['#q','#fBook','#fTag'].forEach(s => $(s).addEventListener('input', () => { shown = PAGE; renderUnful(); }));
$('#more').addEventListener('click', () => { shown += 200; renderUnful(); });

$('#fcount').textContent = `${D.ful.length} verses`;
$('#flist').innerHTML = renderCards(D.ful, '#flist', 500, true);

function renderDivine() {
  $('#dcount').textContent = `${D.divine.length.toLocaleString()} clauses`
    + (D.divine.length > dshown ? ` — showing ${dshown}` : '');
  $('#dlist').innerHTML = renderCards(D.divine, '#dlist', dshown);
  $('#dmore').classList.toggle('hidden', D.divine.length <= dshown);
}
$('#dmore').addEventListener('click', () => { dshown += 200; renderDivine(); });
renderDivine();

$('#roster').innerHTML = '<tr><th>MACULA English</th><th>Next to נביא</th><th>Subject of נבא</th><th>Sample refs (MACULA)</th></tr>'
  + D.roster.map(p => `<tr>
      <td><strong>${esc(p.english || p.lemma)}</strong></td>
      <td>${p.called_prophet}</td>
      <td>${p.subject_of_prophesy}</td>
      <td class="refs">${(p.refs||[]).map(esc).join(' · ')}</td>
    </tr>`).join('');

document.querySelectorAll('nav button').forEach(b =>
  b.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
    ['unful','ful','divine','names'].forEach(id =>
      $('#'+id).classList.toggle('hidden', id !== b.dataset.tab));
  }));
renderUnful();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
