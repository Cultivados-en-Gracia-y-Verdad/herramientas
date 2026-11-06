#!/usr/bin/env python3
"""Two lists from the clauses. No event classifier.

1. Narrator 'and YHWH / Elohim said' — that saying plus the speech until
   the story resumes (wayyiqtol seam, new chapter, or new book).
2. The text’s prophecy words — נאם, כה אמר יהוה, דבר יהוה היה, נבא,
   חזון/חזות, משא+company, προφητ- — plus same-sentence / nested clauses
   only. No chapter walk.

A later book quoting a saying does not join or close a row.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROP = ROOT / "prophecy"
OUT = ROOT / "reports" / "prophecy.html"
REF_PARSE = re.compile(r"^([0-9A-Z]+)\s+(\d+):(\d+|title)$")

TAG_LABEL = {
    "yhwh_said": "YHWH said",
    "elohim_said": "Elohim said",
    "yhwh_spoke": "YHWH spoke",
    "utterance_formula": "נאם",
    "messenger_formula": "כה אמר",
    "thus_says": "כה אמר",
    "word_event": "word of YHWH came",
    "prophesy_verb": "נבא / προφητεύω",
    "prophet_speaks": "prophet said",
    "prophet_named": "προφήτης",
    "prophecy_noun": "προφητεία",
    "vision": "חזון",
    "massa_oracle": "משא",
    "fulfillment_citation": "πληρόω",
    "spirit_via_prophet": "spirit + prophet",
    "spoken_by_lord_through_prophet": "Lord through prophet",
}


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def book_order() -> dict[str, int]:
    eng = json.loads((ROOT / "data" / "versification" / "eng.json").read_text(encoding="utf-8"))
    return {code: i for i, code in enumerate(eng["maxVerses"])}


def sort_key(ref: str, order: dict[str, int]) -> tuple:
    m = REF_PARSE.match(ref or "")
    if not m:
        return (999, 9999, 9999, ref or "")
    vs = 0 if m.group(3) == "title" else int(m.group(3))
    return (order.get(m.group(1), 999), int(m.group(2)), vs, ref)


def ref_of(row: dict) -> str:
    return row.get("ref_protestant") or row.get("ref") or ""


def clause_line(row: dict) -> dict | None:
    gloss = (row.get("own_gloss") or "").strip()
    if not gloss:
        return None
    return {
        "id": row["id"],
        "ref": ref_of(row),
        "book": row.get("book"),
        "gloss": gloss[:400],
        "text": (row.get("own_text") or "").strip(),
        "kind": "head" if row.get("is_frame") or row.get("tier") == "D" else "speech",
    }


def tag_names(tags: list[str] | None) -> list[str]:
    seen: list[str] = []
    for t in tags or []:
        label = TAG_LABEL.get(t, t)
        if label not in seen:
            seen.append(label)
    return seen


def group_speeches(
    heads: list[dict],
    body: list[dict],
    clauses: dict[str, dict],
    order: dict[str, int],
    *,
    require_body: bool,
) -> list[dict]:
    by_head: dict[str, list[dict]] = defaultdict(list)
    for row in body:
        hid = row.get("under_frame_id")
        if hid:
            by_head[hid].append(row)

    head_by_id = {r["id"]: r for r in heads}
    used_heads = set(by_head)
    if not require_body:
        used_heads.update(head_by_id)

    speeches = []
    for hid in used_heads:
        head = head_by_id.get(hid) or clauses.get(hid)
        if head is None:
            continue
        lines = []
        hline = clause_line(head)
        if hline:
            hline["kind"] = "head"
            lines.append(hline)
        kids = sorted(by_head.get(hid, []), key=lambda r: (sort_key(ref_of(r), order), r["id"]))
        for row in kids:
            line = clause_line(row)
            if line:
                lines.append(line)
        if not lines:
            continue
        if require_body and len(lines) < 2:
            continue
        refs = [ln["ref"] for ln in lines]
        speeches.append(
            {
                "id": hid,
                "book": head.get("book"),
                "start": refs[0],
                "end": refs[-1],
                "n": len(lines),
                "tags": tag_names(head.get("frame_tags") or head.get("under_frame_tags")),
                "lines": lines,
            }
        )
    speeches.sort(key=lambda s: sort_key(s["start"], order))
    return speeches


def main() -> int:
    order = book_order()
    clauses = {}
    for name in ("hebrew.jsonl", "greek.jsonl"):
        for row in load_jsonl(ROOT / "clauses" / name):
            clauses[row["id"]] = row

    said = group_speeches(
        load_jsonl(PROP / "divine_speech.jsonl"),
        load_jsonl(PROP / "divine_content.jsonl"),
        clauses,
        order,
        require_body=True,
    )
    marked = group_speeches(
        load_jsonl(PROP / "frames.jsonl"),
        load_jsonl(PROP / "oracle_content.jsonl"),
        clauses,
        order,
        require_body=False,
    )

    books_said = []
    books_mark = []
    seen_s, seen_m = set(), set()
    for s in said:
        if s["book"] not in seen_s:
            seen_s.add(s["book"])
            books_said.append(s["book"])
    for s in marked:
        if s["book"] not in seen_m:
            seen_m.add(s["book"])
            books_mark.append(s["book"])

    summary = {
        "method": (
            "Two lists only. (1) Narrator and-YHWH/Elohim-said plus speech "
            "until story seam. (2) Prophecy vocabulary plus same-sentence / "
            "nested clauses. No event, no name thread, no phrase pile."
        ),
        "said_speeches": len(said),
        "said_clauses": sum(s["n"] for s in said),
        "marked_formulas": len(marked),
        "marked_clauses": sum(s["n"] for s in marked),
    }
    PROP.mkdir(parents=True, exist_ok=True)
    (PROP / "said_speeches.json").write_text(
        json.dumps(said, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PROP / "marked_formulas.json").write_text(
        json.dumps(marked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PROP / "two_lists_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    payload = {
        "said": said,
        "marked": marked,
        "books_said": books_said,
        "books_mark": books_mark,
        "n_said": len(said),
        "n_mark": len(marked),
        "c_said": summary["said_clauses"],
        "c_mark": summary["marked_clauses"],
    }
    html = TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print(f"wrote {OUT}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Two lists</title>
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
  .cluster{background:var(--panel);border:1px solid var(--line);border-radius:6px;
    padding:12px 14px;margin-bottom:12px}
  .ref{font-weight:600;margin-right:8px}
  .muted{color:var(--muted);font-size:13px}
  .gloss{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;line-height:1.65;
    color:#3d3833;background:#fbfaf8;border:1px solid var(--line);border-radius:4px;
    padding:8px 10px;margin:6px 0 0;white-space:pre-wrap}
  .tag{font-size:11.5px;padding:2px 8px;border-radius:11px;background:#f1ede7;
    color:#5f574e;font-family:system-ui,sans-serif;margin-right:6px;display:inline-block}
  .more{display:block;width:100%;padding:10px;margin-top:8px;font:inherit;font-size:14px;
    background:var(--panel);border:1px solid var(--line);border-radius:6px;cursor:pointer;color:var(--muted)}
  .hidden{display:none}
  .step{padding:8px 0;border-top:1px solid var(--line)}
  .step:first-child{border-top:0}
  .head .ref{color:var(--accent)}
</style>
</head>
<body>
<header>
  <h1>Two lists</h1>
  <p class="sub">The text’s own speech headings, in Protestant book order.
  Nothing here is classified as an event. A later quotation does not join
  or close a row.</p>
  <div class="stats" id="stats"></div>
</header>
<nav>
  <button data-tab="said" class="on">YHWH / Elohim said</button>
  <button data-tab="mark">Prophecy words</button>
</nav>
<main>
  <section id="said">
    <p class="note">Narrator “and YHWH said” / “and Elohim said,” then every
    clause of that speech until the story resumes (a wayyiqtol that is not
    a saying, or a new chapter). Genesis 1 “let there be” is here because
    the narrator says Elohim said it. GEN 3:15 is here because it sits in
    the speech that starts at GEN 3:14.</p>
    <div class="filters">
      <input type="search" id="qSaid" placeholder="Search gloss or reference…">
      <select id="bkSaid"></select>
    </div>
    <p class="count" id="saidCount"></p>
    <div id="saidList"></div>
    <button class="more hidden" id="saidMore">Show more</button>
  </section>
  <section id="mark" class="hidden">
    <p class="note">Clauses the text marks with prophecy vocabulary: נאם,
    כה אמר יהוה, דבר יהוה היה, נבא, חזון/חזות, משא with a company word,
    προφητ-, πληρόω with γραφή/προφήτης. Content is same-sentence or
    nested in the MACULA tree only. GEN 15:1 is here as a delivery
    (“the word came in a vision”), including “do not fear.”</p>
    <div class="filters">
      <input type="search" id="qMark" placeholder="Search gloss or reference…">
      <select id="bkMark"></select>
    </div>
    <p class="count" id="markCount"></p>
    <div id="markList"></div>
    <button class="more hidden" id="markMore">Show more</button>
  </section>
</main>
<script>
const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

$('#stats').innerHTML = [
  [D.n_said, 'YHWH / Elohim said speeches'],
  [D.c_said, 'clauses in those speeches'],
  [D.n_mark, 'prophecy-word headings'],
  [D.c_mark, 'clauses under those headings'],
].map(([b,s]) => `<div class="stat"><b>${Number(b).toLocaleString()}</b><span>${s}</span></div>`).join('');

function fill(sel, label, values) {
  sel.innerHTML = `<option value="">${label}</option>` +
    values.map(v => `<option value="${esc(v)}">${esc(v)}</option>`).join('');
}
fill($('#bkSaid'), 'Any book', D.books_said);
fill($('#bkMark'), 'Any book', D.books_mark);

const PAGE = 25;
let saidShow = PAGE, markShow = PAGE;

function matchSpeech(s, q, book) {
  if (book && s.book !== book) return false;
  if (!q) return true;
  if ((s.start||'').toLowerCase().includes(q) || (s.end||'').toLowerCase().includes(q)) return true;
  if ((s.tags||[]).some(t => t.toLowerCase().includes(q))) return true;
  return (s.lines||[]).some(ln =>
    (ln.ref||'').toLowerCase().includes(q) || (ln.gloss||'').toLowerCase().includes(q));
}

function card(s) {
  return `<article class="cluster">
    <div><span class="ref">${esc(s.start)} → ${esc(s.end)}</span>
      <span class="muted">${s.n} clauses</span>
      ${(s.tags||[]).map(t => `<span class="tag">${esc(t)}</span>`).join('')}</div>
    ${s.lines.map(ln => `
      <div class="step ${ln.kind==='head'?'head':''}">
        <span class="ref">${esc(ln.ref)}</span>
        <pre class="gloss">${esc(ln.gloss)}</pre>
      </div>`).join('')}
  </article>`;
}

function renderList(kind) {
  const q = $(kind==='said' ? '#qSaid' : '#qMark').value.trim().toLowerCase();
  const book = $(kind==='said' ? '#bkSaid' : '#bkMark').value;
  const rows = (kind==='said' ? D.said : D.marked).filter(s => matchSpeech(s, q, book));
  const show = kind==='said' ? saidShow : markShow;
  $(kind==='said' ? '#saidCount' : '#markCount').textContent =
    `${rows.length.toLocaleString()} speeches` + (rows.length > show ? ` — showing ${show}` : '');
  $(kind==='said' ? '#saidList' : '#markList').innerHTML =
    rows.slice(0, show).map(card).join('') || '<p class="count">Nothing matches.</p>';
  $(kind==='said' ? '#saidMore' : '#markMore').classList.toggle('hidden', rows.length <= show);
}

$('#qSaid').addEventListener('input', () => { saidShow = PAGE; renderList('said'); });
$('#bkSaid').addEventListener('input', () => { saidShow = PAGE; renderList('said'); });
$('#saidMore').addEventListener('click', () => { saidShow += 25; renderList('said'); });
$('#qMark').addEventListener('input', () => { markShow = PAGE; renderList('mark'); });
$('#bkMark').addEventListener('input', () => { markShow = PAGE; renderList('mark'); });
$('#markMore').addEventListener('click', () => { markShow += 25; renderList('mark'); });

document.querySelectorAll('nav button').forEach(b =>
  b.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
    ['said','mark'].forEach(id => $('#'+id).classList.toggle('hidden', id !== b.dataset.tab));
  }));
renderList('said');
renderList('mark');
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
