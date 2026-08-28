#!/usr/bin/env python3
"""Build Titus TR spine from Robinson-parsed Scrivener (UTR) + remap phrases.

Primary textual/morph source:
  Biblia-LBF/source/greek/TR1894/robinson-parsed/TIT.UTR

Accented display surfaces preferred from tr1894.txt when fold-aligned.
MorphGNT/SBLGNT used only to remap existing phrase token ids + fill lemmas.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERR = Path("/Users/johnwry/Nextcloud/Documents/GitHub/herramientas")
UTR_PATH = HERR / "Biblia-LBF/source/greek/TR1894/robinson-parsed/TIT.UTR"
SCV_PATH = HERR / "Biblia-LBF/source/greek/TR1894/scrivener-textonly/TIT.SCV"
TR_ACCENT_PATH = HERR / "Biblia-LBF/source/greek/TR1894/tr1894.txt"
MORPH = HERR / "MNA/SOURCES/MorphGNT/77-Tit-morphgnt.txt"
PHRASES = HERR / "cgv-translator/translations/titus-phrases.json"
OUT_DIR = HERR / "cgv-translator/translations/tr-spine/titus"
BOOK_CODE = 56

BETA_MAP = {
    "a": "α",
    "b": "β",
    "g": "γ",
    "d": "δ",
    "e": "ε",
    "z": "ζ",
    "h": "η",
    "q": "θ",
    "i": "ι",
    "k": "κ",
    "l": "λ",
    "m": "μ",
    "n": "ν",
    # Robinson/ByzTxt beta (not TLG): c=χ, x=ξ
    "c": "χ",
    "o": "ο",
    "p": "π",
    "r": "ρ",
    "s": "σ",
    "v": "ς",
    "t": "τ",
    "u": "υ",
    "f": "φ",
    "x": "ξ",
    "y": "ψ",
    "w": "ω",
}


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    return re.sub(r"[^\w]", "", s, flags=re.UNICODE)


def beta_to_unicode(beta: str) -> str:
    """Convert Robinson lowercase beta code (no accents) to Greek letters."""
    out = []
    chars = list(beta.lower())
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch == "*":
            # uppercase marker (rare in this UTR); capitalize next letter
            i += 1
            if i < len(chars):
                mapped = BETA_MAP.get(chars[i], chars[i])
                out.append(mapped.upper() if mapped.isalpha() else mapped)
                i += 1
            continue
        if ch == "s":
            # medial sigma unless end / before non-letter
            nxt = chars[i + 1] if i + 1 < len(chars) else ""
            if not nxt or nxt not in BETA_MAP:
                out.append("ς")
            else:
                out.append("σ")
            i += 1
            continue
        out.append(BETA_MAP.get(ch, ch))
        i += 1
    return "".join(out)


def tokenize_greek(text: str) -> list[dict]:
    raw = text.replace("\u00a0", " ").strip()
    parts = re.findall(r"\S+", raw)
    tokens = []
    for p in parts:
        m = re.match(r"^(.*?)([,.;:·!?—–\-\"'»«\)\]]+)$", p)
        if m and m.group(1):
            tokens.append({"surface": m.group(1), "surface_punct": p})
        else:
            m2 = re.match(r"^([\[\(«\"']+)(.+)$", p)
            if m2:
                tokens.append({"surface": m2.group(2).rstrip(",.;:·!?"), "surface_punct": p})
            else:
                tokens.append({"surface": p.rstrip(",.;:·!?·"), "surface_punct": p})
    return tokens


def _is_short_variant_segment(seg: str) -> bool:
    """Heuristic: variant alts are usually 1–3 tokens."""
    morphs = re.findall(r"\{[^}]+\}", seg)
    return 1 <= len(morphs) <= 3


TOKEN_RE = re.compile(
    r"([A-Za-z]+)\s+(\d+)(?:\s+(\d+))?\s*\{([^}]+)\}"
)


def tokens_from_segment(seg: str) -> list[dict]:
    out = []
    for m in TOKEN_RE.finditer(seg):
        beta, strongs, parsing_num, morph = m.group(1), m.group(2), m.group(3), m.group(4)
        greek = beta_to_unicode(beta)
        out.append(
            {
                "beta": beta.lower(),
                "greek": greek,
                "strongs": f"G{strongs}",
                "robinson": morph,
                "parsingNum": parsing_num or "",
            }
        )
    return out


def load_scv_folds() -> dict[tuple[int, int], list[str]]:
    """Load Scrivener textonly beta folds for variant picking (y=θ in SCV)."""
    text = SCV_PATH.read_text(encoding="utf-8", errors="replace")
    # Normalize SCV beta: y often = θ (and sometimes ψ); map y->q for fold compare with UTR
    verses: dict[tuple[int, int], list[str]] = {}
    cur = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+):(\d+)\s+(.*)$", line)
        if m:
            if cur is not None:
                verses[cur] = _scv_words(" ".join(buf))
            cur = (int(m.group(1)), int(m.group(2)))
            buf = [m.group(3)]
            continue
        if cur is not None:
            buf.append(line)
    if cur is not None:
        verses[cur] = _scv_words(" ".join(buf))
    return verses


def _scv_words(s: str) -> list[str]:
    s = re.sub(r"\[[^\]]*\]", " ", s)
    words = []
    for w in re.findall(r"[A-Za-z]+", s):
        w = w.lower().replace("y", "q")  # SCV y≈θ vs UTR q
        words.append(w)
    return words


def load_utr_verses() -> dict[tuple[int, int], str]:
    text = UTR_PATH.read_text(encoding="utf-8", errors="replace")
    verses: dict[tuple[int, int], str] = {}
    cur = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(\d+):(\d+)\s+(.*)$", line)
        if m:
            if cur is not None:
                verses[cur] = " ".join(buf)
            cur = (int(m.group(1)), int(m.group(2)))
            buf = [m.group(3)]
            continue
        if cur is not None:
            buf.append(line.strip())
    if cur is not None:
        verses[cur] = " ".join(buf)
    return verses


def resolve_utr_tokens(ch: int, vs: int, body: str, scv_folds: dict) -> list[dict]:
    body = re.sub(r"\[[^\]]*\]", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    segments = [s.strip() for s in body.split("|")]

    # Rebuild choosing Scrivener alts when we see A|B short pairs
    flat_segments: list[str] = []
    i = 0
    scv = scv_folds.get((ch, vs), [])
    while i < len(segments):
        a = segments[i]
        if not a:
            i += 1
            continue
        if (
            i + 1 < len(segments)
            and segments[i + 1]
            and _is_short_variant_segment(a)
            and _is_short_variant_segment(segments[i + 1])
        ):
            a_toks = tokens_from_segment(a)
            b_toks = tokens_from_segment(segments[i + 1])
            a_betas = [t["beta"] for t in a_toks]
            b_betas = [t["beta"] for t in b_toks]
            # Prefer the alt whose beta sequence appears in SCV
            pick = b_toks  # default: second (often Scrivener in this file)
            scv_join = " ".join(scv)
            if a_betas and all(b in scv for b in a_betas) and not all(
                b in scv for b in b_betas
            ):
                pick = a_toks
                flat_segments.append(a)
            elif b_betas and all(b in scv for b in b_betas):
                pick = b_toks
                flat_segments.append(segments[i + 1])
            else:
                # fallback: whichever beta string occurs in SCV joined text
                if a_betas and a_betas[0] in scv_join.split():
                    flat_segments.append(a)
                else:
                    flat_segments.append(segments[i + 1])
            i += 2
            continue
        flat_segments.append(a)
        i += 1

    merged = " ".join(flat_segments)
    return tokens_from_segment(merged)


def load_tr_accent() -> dict[tuple[int, int], list[dict]]:
    out: dict[tuple[int, int], list[dict]] = {}
    for line in TR_ACCENT_PATH.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("@")
        if len(parts) < 4:
            continue
        ref = parts[2]
        if not ref.startswith("TIT."):
            continue
        _, ch, vs = ref.split(".")
        out[(int(ch), int(vs))] = tokenize_greek(parts[3].strip())
    return out


def load_morphgnt() -> dict[tuple[int, int], list[dict]]:
    morph: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for line in MORPH.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) < 7:
            continue
        vid = p[0]
        ch, vs = int(vid[2:4]), int(vid[4:6])
        morph[(ch, vs)].append(
            {
                "surface": p[4],
                "surface_punct": p[3],
                "norm": p[5],
                "lemma": p[6],
                "pos": p[1],
                "parsing": p[2],
            }
        )
    return morph


def align_keys(a_keys: list[str], b_keys: list[str]):
    sm = SequenceMatcher(a=a_keys, b=b_keys, autojunk=False)
    return list(sm.get_opcodes())


def robinson_pos_parsing(code: str) -> tuple[str, str]:
    """Split Robinson RMAC-like code for morphLoader compatibility."""
    code = (code or "").strip()
    if not code:
        return "", ""
    # Keep full code in parsing; use coarse pos prefix for display helpers
    if "-" in code:
        head, rest = code.split("-", 1)
        return f"{head}-", rest
    return code, ""


def main() -> None:
    utr_bodies = load_utr_verses()
    scv_folds = load_scv_folds()
    accents = load_tr_accent()
    morph = load_morphgnt()

    spine_verses = {}
    report_rows = []
    stats = {
        "verses": 0,
        "tr_tokens": 0,
        "morph_tokens": 0,
        "identical_fold_vs_morph": 0,
        "aligned_ok_vs_morph": 0,
        "tr_only_tokens": 0,
        "morph_only_tokens": 0,
        "substituted": 0,
        "accent_from_tr1894": 0,
        "accent_from_beta": 0,
        "lemmas_from_morphgnt": 0,
        "variants_resolved": 0,
    }

    for (ch, vs) in sorted(utr_bodies):
        stats["verses"] += 1
        rob = resolve_utr_tokens(ch, vs, utr_bodies[(ch, vs)], scv_folds)
        # Count variants in raw body
        if "|" in utr_bodies[(ch, vs)]:
            stats["variants_resolved"] += utr_bodies[(ch, vs)].count("|") // 2

        # Prefer accented surfaces from tr1894 where fold-aligned
        acc = accents.get((ch, vs), [])
        rob_keys = [fold(t["greek"]) for t in rob]
        acc_keys = [fold(t["surface"]) for t in acc]
        accent_map: dict[int, str] = {}
        for tag, i1, i2, j1, j2 in align_keys(rob_keys, acc_keys):
            if tag == "equal":
                for k in range(i2 - i1):
                    accent_map[i1 + k] = acc[j1 + k]["surface"]
                    # keep punct from accent file when present
                    if acc[j1 + k]["surface_punct"] != acc[j1 + k]["surface"]:
                        accent_map[i1 + k] = acc[j1 + k]["surface"]

        # Align Robinson ↔ MorphGNT for phrase remap + lemmas
        mg = morph[(ch, vs)]
        mg_keys = [fold(t["surface"]) for t in mg]
        aligned = []
        ops = []
        for tag, i1, i2, j1, j2 in align_keys(rob_keys, mg_keys):
            if tag == "equal":
                for k in range(i2 - i1):
                    ti = rob[i1 + k]
                    mi = mg[j1 + k]
                    greek = accent_map.get(i1 + k, ti["greek"])
                    if i1 + k in accent_map:
                        stats["accent_from_tr1894"] += 1
                    else:
                        stats["accent_from_beta"] += 1
                    pos, parsing = robinson_pos_parsing(ti["robinson"])
                    aligned.append(
                        {
                            "trIndex": i1 + k + 1,
                            "greek": greek,
                            "greekPunct": greek,
                            "beta": ti["beta"],
                            "strongs": ti["strongs"],
                            "robinson": ti["robinson"],
                            "pos": pos,
                            "parsing": parsing,
                            "align": "match",
                            "morphIndex": j1 + k + 1,
                            "morphGreek": mi["surface"],
                            "lemma": mi["lemma"],
                            "norm": mi["norm"],
                        }
                    )
                    stats["lemmas_from_morphgnt"] += 1
            elif tag == "replace":
                n = min(i2 - i1, j2 - j1)
                for k in range(n):
                    ti = rob[i1 + k]
                    mi = mg[j1 + k]
                    greek = accent_map.get(i1 + k, ti["greek"])
                    if i1 + k in accent_map:
                        stats["accent_from_tr1894"] += 1
                    else:
                        stats["accent_from_beta"] += 1
                    pos, parsing = robinson_pos_parsing(ti["robinson"])
                    aligned.append(
                        {
                            "trIndex": i1 + k + 1,
                            "greek": greek,
                            "greekPunct": greek,
                            "beta": ti["beta"],
                            "strongs": ti["strongs"],
                            "robinson": ti["robinson"],
                            "pos": pos,
                            "parsing": parsing,
                            "align": "substitute",
                            "morphIndex": j1 + k + 1,
                            "morphGreek": mi["surface"],
                            "lemma": mi["lemma"],
                            "norm": fold(greek),
                        }
                    )
                    ops.append({"op": "substitute", "tr": greek, "morph": mi["surface"]})
                    stats["substituted"] += 1
                    stats["lemmas_from_morphgnt"] += 1
                for k in range(n, i2 - i1):
                    ti = rob[i1 + k]
                    greek = accent_map.get(i1 + k, ti["greek"])
                    if i1 + k in accent_map:
                        stats["accent_from_tr1894"] += 1
                    else:
                        stats["accent_from_beta"] += 1
                    pos, parsing = robinson_pos_parsing(ti["robinson"])
                    aligned.append(
                        {
                            "trIndex": i1 + k + 1,
                            "greek": greek,
                            "greekPunct": greek,
                            "beta": ti["beta"],
                            "strongs": ti["strongs"],
                            "robinson": ti["robinson"],
                            "pos": pos,
                            "parsing": parsing,
                            "align": "tr_only",
                            "morphIndex": None,
                            "morphGreek": "",
                            "lemma": "",
                            "norm": fold(greek),
                        }
                    )
                    ops.append({"op": "tr_only", "tr": greek, "morph": ""})
                    stats["tr_only_tokens"] += 1
                for k in range(n, j2 - j1):
                    mi = mg[j1 + k]
                    ops.append(
                        {
                            "op": "morph_only",
                            "tr": "",
                            "morph": mi["surface"],
                            "morphIndex": j1 + k + 1,
                        }
                    )
                    stats["morph_only_tokens"] += 1
            elif tag == "insert":
                for k in range(j1, j2):
                    mi = mg[k]
                    ops.append(
                        {
                            "op": "morph_only",
                            "tr": "",
                            "morph": mi["surface"],
                            "morphIndex": k + 1,
                        }
                    )
                    stats["morph_only_tokens"] += 1
            elif tag == "delete":
                for k in range(i1, i2):
                    ti = rob[k]
                    greek = accent_map.get(k, ti["greek"])
                    if k in accent_map:
                        stats["accent_from_tr1894"] += 1
                    else:
                        stats["accent_from_beta"] += 1
                    pos, parsing = robinson_pos_parsing(ti["robinson"])
                    aligned.append(
                        {
                            "trIndex": k + 1,
                            "greek": greek,
                            "greekPunct": greek,
                            "beta": ti["beta"],
                            "strongs": ti["strongs"],
                            "robinson": ti["robinson"],
                            "pos": pos,
                            "parsing": parsing,
                            "align": "tr_only",
                            "morphIndex": None,
                            "morphGreek": "",
                            "lemma": "",
                            "norm": fold(greek),
                        }
                    )
                    ops.append({"op": "tr_only", "tr": greek, "morph": ""})
                    stats["tr_only_tokens"] += 1

        identical = rob_keys == mg_keys
        if identical:
            stats["identical_fold_vs_morph"] += 1
        if not ops:
            stats["aligned_ok_vs_morph"] += 1
        stats["tr_tokens"] += len(rob)
        stats["morph_tokens"] += len(mg)

        tokens = []
        for t in aligned:
            tid = f"n{BOOK_CODE}{ch:03d}{vs:03d}{t['trIndex']:03d}"
            tokens.append(
                {
                    "sourceTokenId": tid,
                    "trIndex": t["trIndex"],
                    "greek": t["greek"],
                    "greekPunct": t["greekPunct"],
                    "beta": t["beta"],
                    "strongs": t["strongs"],
                    "robinson": t["robinson"],
                    "align": t["align"],
                    "morphIndex": t["morphIndex"],
                    "morphGreek": t["morphGreek"],
                    "lemma": t["lemma"],
                    "pos": t["pos"],
                    "parsing": t["parsing"],
                    "norm": t["norm"],
                }
            )

        tr_text = " ".join(t["greek"] for t in tokens)
        spine_verses[f"{ch}:{vs}"] = {
            "ch": ch,
            "vs": vs,
            "trText": tr_text,
            "identicalToMorphFold": identical,
            "ops": ops,
            "tokens": tokens,
        }
        if ops or not identical:
            report_rows.append(
                {
                    "ref": f"Titus {ch}:{vs}",
                    "identicalFold": identical,
                    "trTokenCount": len(rob),
                    "morphTokenCount": len(mg),
                    "ops": ops,
                    "trText": tr_text,
                    "morphText": " ".join(t["surface"] for t in mg),
                }
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spine_doc = {
        "book": "titus",
        "bookCode": BOOK_CODE,
        "textualBasis": "Scrivener 1894 TR",
        "morphSource": "Maurice A. Robinson TR (robinson-parsed/*.UTR)",
        "morphHelper": "MorphGNT/SBLGNT (lemma fill + phrase remap only)",
        "accentHelper": "tr1894.txt where fold-aligned",
        "stats": stats,
        "verses": spine_verses,
    }
    (OUT_DIR / "titus-tr-spine.json").write_text(
        json.dumps(spine_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Phrase remap (MorphGNT positions -> TR positions)
    morph_to_tr: dict[tuple[int, int, int], int] = {}
    tr_token_by_pos: dict[tuple[int, int, int], dict] = {}
    for verse in spine_verses.values():
        ch, vs = verse["ch"], verse["vs"]
        for t in verse["tokens"]:
            tr_token_by_pos[(ch, vs, t["trIndex"])] = t
            if t["morphIndex"] is not None and t["align"] in ("match", "substitute"):
                morph_to_tr[(ch, vs, t["morphIndex"])] = t["trIndex"]

    # Manual TR walks for MorphGNT↔TR word-order / article gaps (phraseIndex → TR positions + ES)
    HAND_TR_FIXES = {
        23: {
            "trPositions": [8, 9, 10, 11, 12],
            "spanish": "engañadores, sobre todo los de la circuncisión,",
            "note": "TR omits τῆς (οἱ ἐκ περιτομῆς)",
        },
        52: {
            "trPositions": [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            "spanish": (
                "para que el de la parte contraria se avergüence, "
                "no teniendo nada malo que decir de vosotros."
            ),
            "note": "TR: περὶ ὑμῶν λέγειν (order + 2pl, not ἡμῶν)",
        },
        55: {
            "trPositions": [3, 4, 5, 6, 7],
            "spanish": "sino demostrando toda buena fidelidad,",
            "note": "TR: πίστιν πᾶσαν (not πᾶσαν πίστιν)",
        },
        56: {
            "trPositions": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
            "spanish": "para que en todo adornen la doctrina de Dios nuestro Salvador.",
            "note": "TR omits second τὴν before τοῦ σωτῆρος",
        },
    }

    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
    remapped = []
    phrase_issues = []
    for p in phrases:
        m = re.search(r"(\d+):(\d+)$", p["reference"])
        ch, vs = int(m.group(1)), int(m.group(2))
        old_ids = p.get("sourceTokenIds") or []
        morph_positions = []
        for oid in old_ids:
            mm = re.match(r"^n(\d{2})(\d{3})(\d{3})(\d{3})$", oid)
            if mm:
                morph_positions.append(int(mm.group(4)))
            else:
                phrase_issues.append(
                    {"phraseIndex": p["phraseIndex"], "issue": f"bad id {oid}"}
                )

        hand = HAND_TR_FIXES.get(p["phraseIndex"])
        if hand:
            tr_positions = list(hand["trPositions"])
            missing = []
            status = "mapped"
            spanish = hand["spanish"]
        else:
            tr_positions = []
            missing = []
            for mp in morph_positions:
                tp = morph_to_tr.get((ch, vs, mp))
                if tp is None:
                    missing.append(mp)
                else:
                    tr_positions.append(tp)
            status = "mapped"
            spanish = p.get("spanish", "")
            if missing:
                status = "partial" if tr_positions else "unmapped"
                phrase_issues.append(
                    {
                        "phraseIndex": p["phraseIndex"],
                        "ref": p["reference"],
                        "issue": "morph positions not in TR alignment",
                        "missingMorphPositions": missing,
                        "spanish": p.get("spanish"),
                        "greek": p.get("greek"),
                    }
                )

        new_ids = [f"n{BOOK_CODE}{ch:03d}{vs:03d}{pos:03d}" for pos in tr_positions]
        tr_greek = (
            " ".join(tr_token_by_pos[(ch, vs, pos)]["greek"] for pos in tr_positions)
            if tr_positions
            else ""
        )
        token_rows = []
        for pos in tr_positions:
            t = tr_token_by_pos[(ch, vs, pos)]
            rmac = t.get("robinson") or (
                f"{t['pos']}{str(t.get('parsing') or '').strip('-')}" if t.get("pos") else ""
            )
            token_rows.append(
                {
                    "sourceTokenId": t["sourceTokenId"],
                    "greek": t["greek"],
                    "lemma": t["lemma"],
                    "strongs": t.get("strongs", ""),
                    "rmac": rmac,
                    "morphology": "",
                    "align": t["align"],
                    "ble": "",
                    "rv1909": "",
                }
            )

        rp = dict(p)
        rp["sourceTokenIds"] = new_ids
        rp["greek"] = tr_greek or p.get("greek", "")
        rp["spanish"] = spanish
        rp["tokenRows"] = token_rows
        rp["trAlignStatus"] = status
        rp["textualBasis"] = "Scrivener 1894 TR"
        if hand:
            rp["trWalkNote"] = hand["note"]
        remapped.append(rp)

    (OUT_DIR / "titus-phrases-tr.json").write_text(
        json.dumps(remapped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Titus TR spine (Robinson-parsed)",
        "",
        "Textual basis: **Scrivener 1894 TR** via `robinson-parsed/TIT.UTR`.",
        "Morph/Strong’s: Maurice A. Robinson. MorphGNT used only for lemma fill + phrase remap.",
        "",
        "## Stats",
        "",
        f"- Verses: {stats['verses']}",
        f"- TR tokens: {stats['tr_tokens']}",
        f"- MorphGNT tokens: {stats['morph_tokens']}",
        f"- Verses identical after fold vs MorphGNT: {stats['identical_fold_vs_morph']}",
        f"- Verses with zero Morph ops: {stats['aligned_ok_vs_morph']}",
        f"- TR-only tokens: {stats['tr_only_tokens']}",
        f"- Morph-only tokens: {stats['morph_only_tokens']}",
        f"- Substitutions: {stats['substituted']}",
        f"- Accents from tr1894.txt: {stats['accent_from_tr1894']}",
        f"- Surfaces from beta: {stats['accent_from_beta']}",
        f"- Lemmas filled from MorphGNT: {stats['lemmas_from_morphgnt']}",
        f"- Phrases remapped: {len(remapped)}",
        f"- Phrase issues: {len(phrase_issues)}",
        "",
        "## Verses with TR ≠ MorphGNT (token-level ops)",
        "",
    ]
    if not report_rows:
        lines.append("_None — all verses token-aligned cleanly after folding._")
    else:
        for row in report_rows:
            lines += [
                f"### {row['ref']}",
                "",
                f"- identicalFold: {row['identicalFold']}",
                f"- TR tokens: {row['trTokenCount']} · Morph tokens: {row['morphTokenCount']}",
                f"- TR: {row['trText']}",
                f"- Morph: {row['morphText']}",
                "",
            ]
            if row["ops"]:
                lines.append("Ops:")
                for o in row["ops"]:
                    lines.append(
                        f"- `{o['op']}`: TR=`{o.get('tr','')}` · Morph=`{o.get('morph','')}`"
                    )
                lines.append("")

    lines += ["## Phrase remap issues", ""]
    if not phrase_issues:
        lines.append("_None._")
    else:
        for iss in phrase_issues:
            lines.append(
                f"- phrase {iss.get('phraseIndex')} {iss.get('ref','')}: {iss.get('issue')} {iss.get('missingMorphPositions','')}"
            )
            if iss.get("spanish"):
                lines.append(f"  - ES: {iss['spanish']}")
                lines.append(f"  - GR(old): {iss.get('greek','')}")

    (OUT_DIR / "titus-tr-diff-report.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )
    (OUT_DIR / "titus-phrase-remap-issues.json").write_text(
        json.dumps(phrase_issues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    mapped = sum(1 for p in remapped if p.get("trAlignStatus") == "mapped")
    partial = sum(1 for p in remapped if p.get("trAlignStatus") == "partial")
    print(json.dumps(stats, indent=2))
    print(f"phrases mapped={mapped} partial={partial} issues={len(phrase_issues)}")
    print("wrote", OUT_DIR)
    # Spot-check 1:4
    v14 = spine_verses["1:4"]
    print("1:4:", v14["trText"])
    print("1:4 strongs sample:", [t["strongs"] for t in v14["tokens"][:8]])


if __name__ == "__main__":
    main()
