#!/usr/bin/env python3
"""Propose SOPI review rows from the two discovery lists.

Source of spans: prophecy/said_speeches.json + prophecy/marked_formulas.json.
Morphology: MACULA clauses only. No catalogs. Does NOT write sopi/index.json.

For each speech span, keep only coming-act clauses (yiqtol / weqatal /
about.to participle / Greek future; plus qatal whose MACULA gloss already
says will.). Suggest predictive | candidate | exclude. Soft-cut at a
narrative wayyiqtol seam so leaked narrator lines are not proposed.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROP = ROOT / "prophecy"
SOPI = ROOT / "sopi"
OUT_JSON = SOPI / "proposals.json"
OUT_TSV = SOPI / "proposals.tsv"
OUT_SUMMARY = SOPI / "proposals_summary.json"

SPEECH_VERBS = {"אָמַר", "דָּבַר", "דבר", "נָבָא", "נבא", "צָוָה", "צוה", "אָמַר"}
# Consonantal forms after strip — see strip_heb below.
SPEECH_VERBS_C = {"אמר", "דבר", "נבא", "צוה"}

# Second-person assigned work (make / cover / take / bring / put / gather).
ASSIGNED_WORK_C = {
    "עשה",  # make
    "כסה",  # cover
    "לקח",  # take
    "שים",  # put
    "שום",  # put
    "אסף",  # gather
    "כלה",  # finish
}
ASSIGNED_GLOSS = re.compile(
    r"you\.will\.(make|take|cover|bring|put|gather|finish)|"
    r"you will\.(make|take|cover|bring|put|gather|finish)",
    re.I,
)
WILL_GLOSS = re.compile(
    r"\b(I|you|he|she|it|they|we)\.will\b|"
    r"\b(I|you|he|she|it|they|we) will\b|"
    r"about\.to|\[am\]\.about\.to|\[is\]\.coming",
    re.I,
)
REF_PARSE = re.compile(r"^([0-9A-Z]+)\s+(\d+):(\d+|title)$")


def strip_heb(s: str | None) -> str:
    if not s:
        return ""
    n = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in n if unicodedata.category(ch) != "Mn" and ch not in "־־־")


def load_jsonl(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            out[row["id"]] = row
    return out


def book_order() -> dict[str, int]:
    eng = json.loads((ROOT / "data" / "versification" / "eng.json").read_text(encoding="utf-8"))
    return {code: i for i, code in enumerate(eng["maxVerses"])}


def parse_ref(ref: str) -> tuple[str, int, int] | None:
    m = REF_PARSE.match(ref or "")
    if not m:
        return None
    vs = 0 if m.group(3) == "title" else int(m.group(3))
    return m.group(1), int(m.group(2)), vs


def ref_sort_key(ref: str, order: dict[str, int]) -> tuple:
    p = parse_ref(ref)
    if not p:
        return (999, 9999, 9999, ref or "")
    return (order.get(p[0], 999), p[1], p[2], ref)


def verb_c(row: dict) -> str:
    return strip_heb(row.get("verb_lemma") or "")


def is_wayyiqtol(vf: str) -> bool:
    return "wayyiqtol" in (vf or "")


def is_coming_act(row: dict) -> tuple[bool, str]:
    """Return (keep, reason)."""
    vf = row.get("verb_form") or ""
    gloss = row.get("own_gloss") or ""
    if not vf and not WILL_GLOSS.search(gloss):
        return False, "no_verb"
    if is_wayyiqtol(vf):
        return False, "wayyiqtol"
    if "imperative" in vf:
        return False, "imperative"
    if "infinitive" in vf and "about.to" not in gloss and "[am].about" not in gloss:
        # Infinitive construct of purpose stays out unless the host is about.to.
        return False, "infinitive"
    # Relative / present-looking yiqtol without a will/coming gloss (e.g. food which is.eaten).
    if ("yiqtol" in vf or "weqatal" in vf) and not WILL_GLOSS.search(gloss):
        if re.search(r"\b(it|he|she|they)\.is\b|\bis\.", gloss, re.I) and "will" not in gloss.lower():
            return False, "present_looking_yiqtol"
    if "yiqtol" in vf or "weqatal" in vf:
        return True, "yiqtol_or_weqatal"
    if "participle" in vf and ("about.to" in gloss or "[am].about" in gloss or "[is].coming" in gloss):
        return True, "about_to_participle"
    if "future" in vf:
        return True, "greek_future"
    # MACULA sometimes tags qatal while glossing I.will / you.will (GEN 6:18, 7:4).
    if "qatal" in vf and WILL_GLOSS.search(gloss):
        return True, "qatal_will_gloss"
    if "qatal" in vf and ("[is].coming" in gloss or "is.coming" in gloss):
        return True, "qatal_coming_gloss"
    return False, "not_coming"


def person_from_form(vf: str) -> str | None:
    vf = vf or ""
    if "first" in vf:
        return "1"
    if "second" in vf:
        return "2"
    if "third" in vf:
        return "3"
    return None


def is_assigned_work(row: dict) -> bool:
    gloss = row.get("own_gloss") or ""
    if ASSIGNED_GLOSS.search(gloss):
        return True
    vf = row.get("verb_form") or ""
    if "second" not in vf:
        return False
    vc = verb_c(row)
    if vc in ASSIGNED_WORK_C:
        return True
    # hiphil בוא “you will bring”
    if vc == "בוא" and "hiphil" in vf and "second" in vf:
        return True
    return False


def speaker_from_tags(tags: list[str] | None) -> str:
    joined = " ".join(tags or []).lower()
    if "yhwh" in joined or "yahweh" in joined or "lord" in joined:
        return "יהוה"
    if "elohim" in joined or "god" in joined:
        return "אלהים"
    if "prophet" in joined:
        return "prophet"
    return "unknown"


def suggest_status(row: dict, speaker: str) -> tuple[str, str]:
    if is_assigned_work(row):
        return "exclude", "second-person assigned work (make/take/cover/bring/put/gather)"
    vf = row.get("verb_form") or ""
    person = person_from_form(vf)
    divine = speaker in {"יהוה", "אלהים"}
    if divine and person == "1":
        return "predictive", "divine first-person coming act"
    if divine and ("about.to" in (row.get("own_gloss") or "") or "[am].about" in (row.get("own_gloss") or "")):
        return "predictive", "divine about.to"
    if divine and person == "2" and not is_assigned_work(row):
        return "predictive", "divine second-person coming act (not assigned work)"
    if divine and person == "3":
        return "candidate", "divine third-person coming act; raise by hand if curse/outcome speech"
    if not divine:
        return "candidate", "non-divine or unmarked speaker"
    return "candidate", "coming act; status not forced"


def already_ids(index: dict) -> set[str]:
    ids: set[str] = set()
    for rec in index.get("records") or []:
        for cid in rec.get("clause_ids") or []:
            ids.add(cid)
    return ids


def walk_speech(
    speech: dict,
    clauses: dict[str, dict],
    recorded: set[str],
    list_name: str,
) -> list[dict]:
    lines = speech.get("lines") or []
    if not lines:
        return []
    head = lines[0]
    head_ref = head.get("ref") or speech.get("start") or ""
    head_parsed = parse_ref(head_ref)
    speaker = speaker_from_tags(speech.get("tags"))
    proposals: list[dict] = []
    leaked = False

    for i, line in enumerate(lines):
        cid = line.get("id")
        if not cid:
            continue
        row = clauses.get(cid)
        if row is None:
            continue
        kind = line.get("kind") or ""
        vf = row.get("verb_form") or ""
        gloss = (row.get("own_gloss") or line.get("gloss") or "").strip()

        ref = row.get("ref_protestant") or row.get("ref") or line.get("ref") or ""
        after_head = False
        cur = parse_ref(ref)
        if head_parsed and cur and (cur[0], cur[1], cur[2]) > (head_parsed[0], head_parsed[1], head_parsed[2]):
            after_head = True

        # Soft seam: narrative resumes → stop proposing later lines in this span.
        if i > 0 and not leaked:
            if is_wayyiqtol(vf) and verb_c(row) not in SPEECH_VERBS_C:
                leaked = True
            elif (
                after_head
                and person_from_form(vf) == "3"
                and ("qatal" in vf or is_wayyiqtol(vf))
                and not WILL_GLOSS.search(gloss)
                and verb_c(row) not in SPEECH_VERBS_C
            ):
                # GEN 6:3 span leaked into 6:4 Nephilim qatal narrator.
                leaked = True

        if kind == "head" or i == 0 and ("said" in gloss or "spoke" in gloss or "commanded" in gloss):
            # Frame line itself is not a prediction.
            if i == 0 or kind == "head":
                continue

        if leaked:
            continue

        keep, why_keep = is_coming_act(row)
        if not keep:
            continue

        status, why_status = suggest_status(row, speaker)

        proposals.append(
            {
                "speech_id": speech.get("id"),
                "list": list_name,
                "speech_start": speech.get("start"),
                "speech_end": speech.get("end"),
                "speech_tags": speech.get("tags") or [],
                "clause_id": cid,
                "ref": ref,
                "book": row.get("book") or speech.get("book"),
                "corpus": row.get("corpus"),
                "text": (row.get("own_text") or line.get("text") or "").strip(),
                "gloss": gloss[:400],
                "verb_lemma": row.get("verb_lemma"),
                "verb_form": vf,
                "coming_reason": why_keep,
                "suggested_status": status,
                "suggest_reason": why_status,
                "speaker_guess": speaker,
                "after_head_verse": after_head,
                "already_recorded": cid in recorded,
            }
        )
    return proposals


def main() -> int:
    SOPI.mkdir(parents=True, exist_ok=True)
    clauses = {}
    clauses.update(load_jsonl(ROOT / "clauses" / "hebrew.jsonl"))
    clauses.update(load_jsonl(ROOT / "clauses" / "greek.jsonl"))
    order = book_order()

    index_path = SOPI / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {"records": []}
    recorded = already_ids(index)

    said = json.loads((PROP / "said_speeches.json").read_text(encoding="utf-8"))
    marked = json.loads((PROP / "marked_formulas.json").read_text(encoding="utf-8"))

    proposals: list[dict] = []
    for sp in said:
        proposals.extend(walk_speech(sp, clauses, recorded, "said_speeches"))
    for sp in marked:
        proposals.extend(walk_speech(sp, clauses, recorded, "marked_formulas"))

    # De-dupe by clause_id (prefer said_speeches over marked if both).
    by_id: dict[str, dict] = {}
    for p in proposals:
        cid = p["clause_id"]
        if cid not in by_id:
            by_id[cid] = p
        elif by_id[cid]["list"] != "said_speeches" and p["list"] == "said_speeches":
            by_id[cid] = p
    proposals = sorted(by_id.values(), key=lambda p: ref_sort_key(p["ref"], order))

    status_counts = Counter(p["suggested_status"] for p in proposals)
    list_counts = Counter(p["list"] for p in proposals)
    book_counts = Counter(p["book"] for p in proposals)
    open_counts = Counter(
        p["suggested_status"] for p in proposals if not p["already_recorded"] and p["suggested_status"] != "exclude"
    )

    payload = {
        "method": {
            "name": "SOPI propose from two lists",
            "authority": "Biblical text via MACULA clauses only. Spans from said_speeches + marked_formulas.",
            "does_not": [
                "write sopi/index.json",
                "use external prophecy catalogs",
                "classify by later Scripture",
                "invent event titles",
            ],
            "coming_act": "yiqtol / weqatal / about.to participle / Greek future; qatal only if MACULA gloss already says will/coming",
            "exclude_default": "second-person assigned work (make, take, cover, bring, put, gather)",
            "seam": "After the head, a wayyiqtol whose verb is not אמר/דבר/נבא/צוה ends the proposal window; also a later-verse third-person qatal/wayyiqtol without will/coming gloss (soft cut of leaked narrator).",
            "review": "Accept or reject by hand into sopi/index.json. interpretation and later_scripture stay null.",
        },
        "inputs": {
            "said_speeches": len(said),
            "marked_formulas": len(marked),
            "clauses_indexed": len(clauses),
            "already_recorded_clause_ids": len(recorded),
        },
        "counts": {
            "proposals": len(proposals),
            "by_status": dict(status_counts),
            "by_list": dict(list_counts),
            "open_for_review": dict(open_counts),
            "already_recorded": sum(1 for p in proposals if p["already_recorded"]),
            "books": len(book_counts),
        },
        "proposals": proposals,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cols = [
        "ref",
        "suggested_status",
        "already_recorded",
        "list",
        "speech_start",
        "speech_end",
        "clause_id",
        "speaker_guess",
        "verb_form",
        "gloss",
        "suggest_reason",
        "coming_reason",
        "after_head_verse",
        "speech_tags",
    ]
    with OUT_TSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for p in proposals:
            row = {k: p.get(k, "") for k in cols}
            row["speech_tags"] = "; ".join(p.get("speech_tags") or [])
            row["already_recorded"] = "yes" if p.get("already_recorded") else ""
            row["after_head_verse"] = "yes" if p.get("after_head_verse") else ""
            w.writerow(row)

    summary = {
        "proposals": len(proposals),
        "by_status": dict(status_counts),
        "open_for_review": dict(open_counts),
        "already_recorded": payload["counts"]["already_recorded"],
        "top_books": book_counts.most_common(25),
        "files": {"json": str(OUT_JSON.relative_to(ROOT)), "tsv": str(OUT_TSV.relative_to(ROOT))},
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {OUT_JSON} ({len(proposals)} proposals)")
    print(f"wrote {OUT_TSV}")
    print(f"status {dict(status_counts)}")
    print(f"open_for_review {dict(open_counts)} (excludes already_recorded + exclude)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
