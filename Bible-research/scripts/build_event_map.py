#!/usr/bin/env python3
"""Build a prophetic event map from the clauses — not a verse dump.

An event is a coming act: yiqtol / weqatal / Greek future, sitting under
prophecy vocabulary or under narrator “and YHWH said.” Jussive commands
(“do not fear”) are not events. Under divine speech, second-person
you-shall is not taken (that is law). The event’s name is the clause’s
own verb plus the proper nouns MACULA marks in that clause. YHWH /
Elohim / κύριος / θεός are not used as the key.

Repeated event: the same verb + the same proper-noun set in two or more
verses.

Chronology the text itself gives:
  - utterance order (Protestant book → chapter → verse of the saying)
  - speech order (verse order under one frame)
  - sequence words in the clause (אחר / אז / עד / τότε / μετά / ἄχρι / ἕως)

No event titles from memory. No empire dates. No closing a cluster because
another book quotes it.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROP = ROOT / "prophecy"
REPORTS = ROOT / "reports"

HEB_TSV = ROOT / "MACULA" / "macula-hebrew-main" / "WLC" / "tsv" / "macula-hebrew.tsv"
EL_TSV = ROOT / "MACULA" / "macula-greek-SBLGNT" / "SBLGNT" / "tsv" / "macula-greek-SBLGNT.tsv"

DIVINE = {
    "יהוה",
    "אלהים",
    "אדני",
    "אל",
    "κύριος",
    "θεός",
    "πνεῦμα",
}
SEQ_HE = {"אחר", "אז", "עד"}
SEQ_EL = {"τότε", "μετά", "ἄχρι", "ἕως", "εἶτα", "ἔπειτα"}
# Delivery verbs name the speaking, not the predicted act.
SPEECH_VERB = {"אמר", "דבר", "נבא", "צוה", "λέγω", "λαλέω", "προφητεύω"}
REF_PARSE = re.compile(r"^([0-9A-Z]+)\s+(\d+):(\d+|title)$")

# Piles are lemma pairs the text actually puts in one clause.
# The button is those words, not a theological title.
PHRASE_LABEL = {
    "day_yhwh": "day + YHWH",
    "day_lord": "day + Lord",
    "distress_jacob": "distress + Jacob",
    "exile": "exile (גלה / גולה / αἰχμαλωσία)",
    "turn_captivity": "turn the captivity",
    "latter_days": "latter days",
    "return": "return (שוב + Zion / Jerusalem / captivity)",
    "thousand_years": "thousand years",
    "parousia": "παρουσία",
    "come_jesus": "come + Jesus / Christ",
}


def cons(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn"
    )


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def book_order() -> dict[str, int]:
    eng = json.loads((ROOT / "data" / "versification" / "eng.json").read_text(encoding="utf-8"))
    return {code: i for i, code in enumerate(eng["maxVerses"])}


def collect_proper() -> tuple[set[str], dict[str, str]]:
    """Word ids MACULA marks type=proper, plus an English label for the lemma.

    Do not treat a lemma as a name just because that spelling is a name
    somewhere else (אמר the verb is not Immer).
    """
    ids: dict[str, str] = {}
    labels: dict[str, Counter] = defaultdict(Counter)
    for path, hebrew in ((HEB_TSV, True), (EL_TSV, False)):
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                if (row.get("type") or "") != "proper":
                    continue
                raw = row.get("lemma") or ""
                if not raw:
                    continue
                key = cons(raw) if hebrew else raw
                wid = row.get("xml:id") or ""
                if wid:
                    ids[wid] = key
                eng = (row.get("english") or row.get("gloss") or raw).strip()
                if eng:
                    labels[key][eng] += 1
    english = {k: c.most_common(1)[0][0] for k, c in labels.items()}
    return ids, english


def load_clauses() -> dict[str, dict]:
    out = {}
    for name in ("hebrew.jsonl", "greek.jsonl"):
        for row in load_jsonl(ROOT / "clauses" / name):
            out[row["id"]] = row
    return out


def is_hortatory(row: dict) -> bool:
    g = (row.get("own_gloss") or "").strip().lower()
    return (
        g.startswith("do.not")
        or g.startswith("let.")
        or g.startswith("let ")
        or "let.it." in g
        or "let.us." in g
        or "let.them." in g
    )


def is_predictive(row: dict) -> bool:
    """A coming act, not a command or 'do not fear'.

    Jussive / cohortative are hortatory. wayyiqtol is narrative.
    yiqtol / weqatal / Greek future state what will happen.
    """
    if is_hortatory(row):
        return False
    form = (row.get("verb_form") or "").lower()
    if "wayyiqtol" in form or "jussive" in form or "cohortative" in form:
        return False
    if row.get("corpus") == "hebrew":
        return "yiqtol" in form or "weqatal" in form
    return "future" in form


def divine_person_ok(row: dict) -> bool:
    """Under 'YHWH said', keep I-will / he-will. Drop you-shall law."""
    form = (row.get("verb_form") or "").lower()
    return "first" in form or "third" in form


def names_in(row: dict, proper_ids: dict[str, str]) -> list[str]:
    found = []
    seen = set()
    for wid in row.get("word_ids") or []:
        key = proper_ids.get(wid or "")
        if not key or key in DIVINE or key in seen:
            continue
        seen.add(key)
        found.append(key)
    return found


def seq_words(row: dict) -> list[str]:
    keys = {cons(x) if row.get("corpus") == "hebrew" else x for x in (row.get("lemmas") or [])}
    if row.get("corpus") == "hebrew":
        return sorted(keys & SEQ_HE)
    return sorted(keys & SEQ_EL)


def sort_key(ref: str, order: dict[str, int]) -> tuple:
    m = REF_PARSE.match(ref or "")
    if not m:
        return (999, 9999, 9999, ref or "")
    vs = 0 if m.group(3) == "title" else int(m.group(3))
    return (order.get(m.group(1), 999), int(m.group(2)), vs, ref)


def construct(seq: list[str], a: str, b: str, skip: set[str] | None = None) -> bool:
    skip = skip or {"ה", "ὁ", "τοῦ", "τῆς", "τῷ", "τὴν"}
    for i, x in enumerate(seq):
        if x != a:
            continue
        j = i + 1
        while j < len(seq) and seq[j] in skip:
            j += 1
        if j < len(seq) and seq[j] == b:
            return True
    return False


def phrase_hits(row: dict) -> list[str]:
    pred = is_predictive(row)
    verb = cons(row.get("verb_lemma") or "") if row.get("corpus") == "hebrew" else (row.get("verb_lemma") or "")
    subj = {
        cons(x) if row.get("corpus") == "hebrew" else x
        for x in (row.get("subject_lemmas") or [])
    }
    gloss = (row.get("own_gloss") or "").lower()
    hits: list[str] = []
    if row.get("corpus") == "hebrew":
        seq = [cons(x) for x in (row.get("lemmas") or [])]
        C = set(seq)
        if construct(seq, "יום", "יהוה") and ("יום" in subj or "of.yahweh" in gloss):
            hits.append("day_yhwh")
        if "צרה" in C and "יעקב" in C:
            hits.append("distress_jacob")
        if "גולה" in C or (pred and verb == "גלה" and C & {"ישראל", "יהודה", "ירושלם", "בבל"}):
            hits.append("exile")
        if "שוב" in C and "שבות" in C:
            hits.append("turn_captivity")
        if construct(seq, "אחרית", "יום"):
            hits.append("latter_days")
        if pred and verb == "שוב" and C & {"ציון", "ירושלם", "שבות"}:
            hits.append("return")
    else:
        seq = list(row.get("lemmas") or [])
        L = set(seq)
        if construct(seq, "ἡμέρα", "κύριος") and "day of" in gloss:
            hits.append("day_lord")
        if "χίλιοι" in L and "ἔτος" in L:
            hits.append("thousand_years")
        if (
            "παρουσία" in L
            and L & {"Ἰησοῦς", "Χριστός", "υἱός", "σός", "κύριος"}
            and "ἐμός" not in L
        ) or ("παρουσία" in L and "θεός" in L and "ἡμέρα" in L):
            hits.append("parousia")
        if pred and verb == "ἔρχομαι" and ("Ἰησοῦς" in subj or "Χριστός" in subj):
            hits.append("come_jesus")
        if pred and L & {"αἰχμαλωσία", "μετοικεσία"}:
            hits.append("exile")
    return hits


def event_key(verb: str, names: list[str]) -> str:
    return verb + "|" + ",".join(names)


def label_of(verb_en: str, names: list[str], english: dict[str, str]) -> str:
    who = ", ".join(english.get(n, n) for n in names)
    action = verb_en or "?"
    return f"{action} — {who}" if who else action


def main() -> int:
    order = book_order()
    proper, english = collect_proper()
    clauses = load_clauses()
    marked_ids = set()
    under: dict[str, str | None] = {}
    source_of: dict[str, str] = {}
    for row in load_jsonl(PROP / "frames.jsonl") + load_jsonl(PROP / "oracle_content.jsonl"):
        marked_ids.add(row["id"])
        under[row["id"]] = row.get("under_frame_id") or row["id"]
        source_of[row["id"]] = "prophecy_vocab"
    for row in load_jsonl(PROP / "divine_content.jsonl"):
        marked_ids.add(row["id"])
        under[row["id"]] = row.get("under_frame_id") or row["id"]
        source_of[row["id"]] = "divine_speech"

    events = []
    for cid in marked_ids:
        row = clauses.get(cid)
        if row is None or not is_predictive(row):
            continue
        if source_of.get(cid) == "divine_speech" and not divine_person_ok(row):
            continue
        gloss = (row.get("own_gloss") or "").strip()
        if not gloss or gloss.startswith("the.utterance") or gloss.startswith("thus he.says"):
            continue
        if row.get("kind") not in {"content", "reduced", "embed"}:
            continue
        verb = cons(row.get("verb_lemma") or "") if row.get("corpus") == "hebrew" else (row.get("verb_lemma") or "")
        if not verb or verb in SPEECH_VERB:
            continue
        lems = {cons(x) if row.get("corpus") == "hebrew" else x for x in (row.get("lemmas") or [])}
        if verb == "היה" and "דבר" in lems and "יהוה" in lems:
            continue
        names = names_in(row, proper)
        ref = row.get("ref_protestant") or row.get("ref") or ""
        events.append(
            {
                "id": cid,
                "ref": ref,
                "book": row.get("book"),
                "corpus": row.get("corpus"),
                "verb": verb,
                "verb_english": row.get("verb_english") or verb,
                "names": names,
                "key": event_key(verb, names),
                "label": label_of(row.get("verb_english") or verb, names, english),
                "gloss": gloss[:400],
                "seq": seq_words(row),
                "speech": under.get(cid),
                "form": row.get("verb_form"),
                "source": source_of.get(cid, "prophecy_vocab"),
            }
        )

    events.sort(key=lambda e: sort_key(e["ref"], order))

    clusters: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        if e["names"]:
            clusters[e["key"]].append(e)
    repeated = []
    for key, rows in clusters.items():
        refs = sorted({r["ref"] for r in rows}, key=lambda r: sort_key(r, order))
        if len(refs) < 2:
            continue
        repeated.append(
            {
                "key": key,
                "label": rows[0]["label"],
                "verb": rows[0]["verb"],
                "verb_english": rows[0]["verb_english"],
                "names": rows[0]["names"],
                "count": len(refs),
                "first": refs[0],
                "last": refs[-1],
                "refs": refs[:40],
                "samples": [
                    {"ref": r["ref"], "gloss": r["gloss"]}
                    for r in rows[:5]
                ],
            }
        )
    repeated.sort(key=lambda c: (-c["count"], sort_key(c["first"], order)))

    speeches: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        if e.get("speech"):
            speeches[e["speech"]].append(e)
    speech_rows = []
    for sid, rows in speeches.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda e: sort_key(e["ref"], order))
        speech_rows.append(
            {
                "speech": sid,
                "book": rows[0]["book"],
                "start": rows[0]["ref"],
                "end": rows[-1]["ref"],
                "n": len(rows),
                "steps": [
                    {
                        "ref": r["ref"],
                        "label": r["label"],
                        "gloss": r["gloss"],
                        "seq": r["seq"],
                    }
                    for r in rows[:30]
                ],
            }
        )
    speech_rows.sort(key=lambda s: sort_key(s["start"], order))

    by_name: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        for n in e["names"]:
            by_name[n].append(e)
    threads = []
    for n, rows in by_name.items():
        by_ref: dict[str, dict] = {}
        for r in rows:
            rec = by_ref.setdefault(
                r["ref"],
                {"ref": r["ref"], "book": r.get("book"), "verbs": [], "glosses": [], "seq": []},
            )
            if r["verb_english"] not in rec["verbs"]:
                rec["verbs"].append(r["verb_english"])
            if r["gloss"] not in rec["glosses"]:
                rec["glosses"].append(r["gloss"])
            for s in r.get("seq") or []:
                if s not in rec["seq"]:
                    rec["seq"].append(s)
        refs = sorted(by_ref.values(), key=lambda r: sort_key(r["ref"], order))
        acts = Counter(r["verb_english"] for r in rows)
        threads.append(
            {
                "name": english.get(n, n),
                "lemma": n,
                "count": len(refs),
                "first": refs[0]["ref"],
                "last": refs[-1]["ref"],
                "acts": [{"verb": v, "n": c} for v, c in acts.most_common(20)],
                "refs": [
                    {
                        "ref": r["ref"],
                        "book": r.get("book"),
                        "verbs": r["verbs"],
                        "gloss": " | ".join(r["glosses"][:6]),
                        "seq": r["seq"],
                    }
                    for r in refs
                ],
            }
        )
    threads.sort(key=lambda t: (-t["count"], t["name"]))

    phrase_rows: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in clauses.values():
        gloss = (row.get("own_gloss") or "").strip()
        if not gloss:
            continue
        ref = row.get("ref_protestant") or row.get("ref") or ""
        if not ref:
            continue
        for pid in phrase_hits(row):
            rec = phrase_rows[pid].setdefault(
                ref, {"ref": ref, "book": row.get("book"), "glosses": []}
            )
            if gloss not in rec["glosses"]:
                rec["glosses"].append(gloss)
    phrases = []
    for pid, by_ref in phrase_rows.items():
        refs = sorted(by_ref.values(), key=lambda r: sort_key(r["ref"], order))
        phrases.append(
            {
                "id": pid,
                "label": PHRASE_LABEL[pid],
                "count": len(refs),
                "first": refs[0]["ref"],
                "last": refs[-1]["ref"],
                "refs": [
                    {"ref": r["ref"], "book": r.get("book"), "gloss": " | ".join(r["glosses"][:6])}
                    for r in refs
                ],
            }
        )
    phrases.sort(key=lambda p: (-p["count"], p["label"]))

    PROP.mkdir(parents=True, exist_ok=True)
    (PROP / "events.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events),
        encoding="utf-8",
    )
    (PROP / "repeated_events.json").write_text(
        json.dumps(repeated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROP / "speech_sequences.json").write_text(
        json.dumps(speech_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROP / "name_threads.json").write_text(
        json.dumps(threads, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (PROP / "text_phrases.json").write_text(
        json.dumps(phrases, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "method": (
            "Predicted event = yiqtol/weqatal/future under prophecy vocabulary "
            "or under narrator 'and YHWH said' (I-will / he-will). "
            "Not jussive ('do not fear'), not you-shall law. "
            "Repeat = same verb + same MACULA proper nouns (not divine names). "
            "Order = utterance order, speech order, or sequence words in the clause."
        ),
        "proper_nouns": len(proper),
        "predicted_clauses": len(events),
        "repeated_event_types": len(repeated),
        "speeches_with_sequence": len(speech_rows),
        "name_threads": len(threads),
        "text_phrases": [{"label": p["label"], "count": p["count"]} for p in phrases],
        "top_names": [
            {"name": t["name"], "count": t["count"], "first": t["first"], "last": t["last"], "acts": t["acts"][:6]}
            for t in threads[:20]
        ],
        "top_repeated": [
            {"label": c["label"], "count": c["count"], "first": c["first"], "last": c["last"]}
            for c in repeated[:25]
        ],
    }
    (PROP / "event_map_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / "repeated_events.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["label", "count", "first", "last", "verb_english", "names", "sample_refs"])
        for c in repeated:
            w.writerow(
                [
                    c["label"],
                    c["count"],
                    c["first"],
                    c["last"],
                    c["verb_english"],
                    ", ".join(c["names"]),
                    "; ".join(c["refs"][:12]),
                ]
            )
    with (REPORTS / "predicted_events.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["ref", "book", "label", "seq", "gloss"])
        for e in events:
            w.writerow([e["ref"], e["book"], e["label"], " ".join(e["seq"]), e["gloss"]])
    with (REPORTS / "by_name.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["name", "ref", "verbs", "seq", "gloss"])
        for t in threads:
            for r in t["refs"]:
                w.writerow(
                    [
                        t["name"],
                        r["ref"],
                        "; ".join(r["verbs"]),
                        " ".join(r.get("seq") or []),
                        r["gloss"],
                    ]
                )
    with (REPORTS / "text_phrases.tsv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["phrase", "ref", "gloss"])
        for p in phrases:
            for r in p["refs"]:
                w.writerow([p["label"], r["ref"], r["gloss"]])

    print(
        json.dumps(
            {
                "predicted_clauses": len(events),
                "repeated_event_types": len(repeated),
                "speeches_with_sequence": len(speech_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
