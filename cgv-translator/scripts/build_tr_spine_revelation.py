#!/usr/bin/env python3
"""Build Revelation TR spine from Robinson-parsed Scrivener (UTR) + remap phrases.

Primary textual/morph source:
  Biblia-LBF/source/greek/TR1894/robinson-parsed/RE.UTR

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
UTR_PATH = HERR / "Biblia-LBF/source/greek/TR1894/robinson-parsed/RE.UTR"
SCV_PATH = HERR / "Biblia-LBF/source/greek/TR1894/scrivener-textonly/RE.SCV"
TR_ACCENT_PATH = HERR / "Biblia-LBF/source/greek/TR1894/tr1894.txt"
MORPH = HERR / "MNA/SOURCES/MorphGNT/87-Re-morphgnt.txt"
PHRASES = HERR / "cgv-translator/translations/revelation-phrases.json"
OUT_DIR = HERR / "cgv-translator/translations/tr-spine/revelation"
BOOK_CODE = 66

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
    r"([A-Za-z]+)\s+(\d+(?:\s+\d+)*)\s*\{([^}]+)\}"
)


def tokens_from_segment(seg: str) -> list[dict]:
    out = []
    for m in TOKEN_RE.finditer(seg):
        beta, nums_raw, morph = m.group(1), m.group(2), m.group(3)
        nums = nums_raw.split()
        # Verbs carry Strong's + a 4-digit parsing code. Numeral abbreviations
        # (rmd = 144) may list several Strong's and no parsing code.
        if len(nums) >= 2 and morph.startswith("V-") and len(nums[-1]) == 4:
            strongs_nums, parsing_num = nums[:-1], nums[-1]
        else:
            strongs_nums, parsing_num = nums, ""
        greek = beta_to_unicode(beta)
        out.append(
            {
                "beta": beta.lower(),
                "greek": greek,
                "strongs": " ".join(f"G{n}" for n in strongs_nums),
                "robinson": morph,
                "parsingNum": parsing_num,
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
    # 17:4 UTR prints καὶ ἡ γυνὴ | ἡ | ἦν |; SCV keeps καὶ ἡ γυνὴ ἦν.
    if (ch, vs) == (17, 4):
        body = re.sub(
            r"\|\s*h\s+3588\s*\{T-NSF\}\s*\|\s*hn\s+1510\s+5707\s*\{V-IAI-3S\}\s*\|",
            "hn 1510 5707 {V-IAI-3S}",
            body,
        )
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
    toks = tokens_from_segment(merged)
    # 7:10 UTR prints both Θεῷ ἡμῶν placements; SCV / tr1894 keep only the first.
    if (ch, vs) == (7, 10):
        cleaned = []
        seen_qronou = False
        skip = 0
        for i, t in enumerate(toks):
            if skip:
                skip -= 1
                continue
            if t["beta"] == "qronou":
                seen_qronou = True
                cleaned.append(t)
                continue
            if (
                seen_qronou
                and t["beta"] == "tou"
                and i + 2 < len(toks)
                and toks[i + 1]["beta"] == "qeou"
                and toks[i + 2]["beta"] == "hmwn"
            ):
                skip = 2
                continue
            cleaned.append(t)
        toks = cleaned
    # 9:19 UTR prints εἰσιν | ἐστιν; SCV / tr1894 keep singular ἐστιν.
    if (ch, vs) == (9, 19):
        toks = [t for t in toks if t["beta"] != "eisin"]
    # 13:3 UTR prints ἐθαυμάσθη ἐν ὅλῃ τῇ γῇ | ἐθαύμασεν ὅλη ἡ γῆ; SCV keeps the second.
    if (ch, vs) == (13, 3):
        cleaned = []
        i = 0
        while i < len(toks):
            if (
                i + 4 < len(toks)
                and [toks[j]["beta"] for j in range(i, i + 5)]
                == ["eqaumasqh", "en", "olh", "th", "gh"]
            ):
                i += 5
                continue
            cleaned.append(toks[i])
            i += 1
        toks = cleaned
    return toks


def load_tr_accent() -> dict[tuple[int, int], list[dict]]:
    out: dict[tuple[int, int], list[dict]] = {}
    for line in TR_ACCENT_PATH.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("@")
        if len(parts) < 4:
            continue
        ref = parts[2]
        if not ref.startswith("REV."):
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
                    "ref": f"Revelation {ch}:{vs}",
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
        "book": "revelation",
        "bookCode": BOOK_CODE,
        "textualBasis": "Scrivener 1894 TR",
        "morphSource": "Maurice A. Robinson TR (robinson-parsed/*.UTR)",
        "morphHelper": "MorphGNT/SBLGNT (lemma fill + phrase remap only)",
        "accentHelper": "tr1894.txt where fold-aligned",
        "stats": stats,
        "verses": spine_verses,
    }
    (OUT_DIR / "revelation-tr-spine.json").write_text(
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
        # Revelation 1 — TR readings the MorphGNT remap missed or mis-rendered.
        2: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "quien dio testimonio de la palabra de Dios y del testimonio "
                "de Jesús Cristo, de todo lo que vio"
            ),
            "note": "TR ὅσα τε εἶδεν (τε is TR-only)",
        },
        6: {
            "trPositions": list(range(9, 23)),
            "spanish": "Gracia y paz a ustedes de aquel que es y que era y que viene,",
            "note": "TR ἀπὸ τοῦ ὁ ὤν (τοῦ is TR-only)",
        },
        7: {
            "trPositions": list(range(23, 34)),
            "spanish": "y de los siete espíritus que están delante de su trono,",
            "note": "TR ἃ ἐστιν ἐνώπιον (ἐστιν is TR-only)",
        },
        9: {
            "trPositions": list(range(9, 21)),
            "spanish": (
                "el primogénito de entre los muertos y el gobernante "
                "de los reyes de la tierra."
            ),
            "note": "TR πρωτότοκος ἐκ τῶν νεκρῶν",
        },
        10: {
            "trPositions": list(range(21, 35)),
            "spanish": (
                "Al que nos amó y nos lavó de nuestros pecados con su sangre"
            ),
            "note": "TR ἀγαπήσαντι / λούσαντι / ἀπὸ (not Morph ἀγαπῶντι / λύσαντι / ἐκ)",
        },
        11: {
            "trPositions": list(range(1, 24)),
            "spanish": (
                "y nos hizo reyes y sacerdotes para su Dios y Padre: "
                "a él la gloria y el poder por los siglos de los siglos. Amén."
            ),
            "note": "TR βασιλεῖς καὶ ἱερεῖς (not βασιλείαν ἱερεῖς)",
        },
        12: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "He aquí, viene con las nubes, y todo ojo lo verá, "
                "incluso quienes lo traspasaron,"
            ),
            "note": "TR οἵτινες αὐτὸν ἐξεκέντησαν; ἰδού → He aquí",
        },
        14: {
            "trPositions": list(range(1, 12)),
            "spanish": "Yo soy el Alfa y la Omega, el principio y el fin, dice",
            "note": "TR adds ἀρχὴ καὶ τέλος; Morph κύριος ὁ θεός starts next phrase",
        },
        15: {
            "trPositions": list(range(12, 24)),
            "spanish": "el Señor, el que es y que era y que viene, el Todopoderoso.",
            "note": "TR ὁ Κύριος (no ὁ θεός)",
        },
        16: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "Yo, Juan, también hermano de ustedes y copartícipe "
                "en la tribulación y en el reino y la perseverancia de Jesús Cristo,"
            ),
            "note": "TR ὁ καὶ ἀδελφός; ἐν τῇ βασιλείᾳ; Ἰησοῦ Χριστοῦ",
        },
        17: {
            "trPositions": list(range(20, 38)),
            "spanish": (
                "estuve en la isla llamada Patmos por causa de la palabra de Dios "
                "y por el testimonio de Jesús Cristo."
            ),
            "note": "TR διὰ τὴν μαρτυρίαν Ἰησοῦ Χριστοῦ",
        },
        20: {
            "trPositions": list(range(2, 28)),
            "spanish": (
                "Yo soy el Alfa y la Omega, el primero y el último, "
                "y lo que ves, escríbelo en un libro y envíalo a las siete iglesias "
                "que están en Asia:"
            ),
            "note": "TR adds Ἐγώ εἰμι τὸ Α καὶ τὸ Ω ὁ πρῶτος καὶ ὁ ἔσχατος; ταῖς ἐν Ἀσίᾳ",
        },
        23: {
            "trPositions": list(range(1, 10)),
            "spanish": (
                "y en medio de los siete candelabros a alguien semejante "
                "a un hijo de hombre,"
            ),
            "note": "TR τῶν ἑπτὰ λυχνιῶν",
        },
        29: {
            "trPositions": list(range(1, 10)),
            "spanish": "y tenía en su mano derecha siete estrellas,",
            "note": "TR ἐν τῇ δεξιᾷ αὐτοῦ χειρί",
        },
        33: {
            "trPositions": list(range(12, 24)),
            "spanish": "Y puso su mano derecha sobre mí, diciéndome: No tengas miedo.",
            "note": "TR χεῖρα; λέγων μοι",
        },
        35: {
            "trPositions": list(range(1, 26)),
            "spanish": (
                "y el que vive. Estuve muerto, y he aquí, vivo por los siglos "
                "de los siglos. Amén. Y tengo las llaves del Hades y de la muerte."
            ),
            "note": "TR ἀμήν; κλεῖς τοῦ ᾅδου καὶ τοῦ θανάτου (Hades then death)",
        },
        36: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "Escribe las cosas que has visto, las que son y las que están "
                "por suceder después de estas cosas:"
            ),
            "note": "TR omits Morph οὖν",
        },
        40: {
            "trPositions": list(range(26, 35)),
            "spanish": "y los siete candelabros que viste son siete iglesias.",
            "note": "TR αἱ ἑπτὰ λυχνίαι ἅς εἶδες ἑπτὰ ἐκκλησίαι εἰσίν",
        },
        # Revelation 2
        41: {
            "trPositions": list(range(1, 7)),
            "spanish": "Escribe al ángel de la iglesia efesia:",
            "note": "TR τῆς Ἐφέσίνης ἐκκλησίας (not ἐν Ἐφέσῳ)",
        },
        44: {
            "trPositions": list(range(1, 13)),
            "spanish": "Conozco tus obras, y tu trabajo, y tu perseverancia,",
            "note": "TR τὸν κόπον σου",
        },
        45: {
            "trPositions": list(range(13, 25)),
            "spanish": (
                "y que no puedes soportar a los malos, y has puesto a prueba "
                "a los que afirman ser apóstoles"
            ),
            "note": "TR ἐπειράσω τοὺς φάσκοντας εἶναι ἀποστόλους",
        },
        47: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y has soportado, y tienes perseverancia, y por causa de mi nombre "
                "has trabajado y no te has cansado."
            ),
            "note": "TR καὶ ἐβάστασας… κεκοπίακας καὶ οὐ κέκμηκας",
        },
        50: {
            "trPositions": list(range(12, 30)),
            "spanish": (
                "Pero si no, voy a ti pronto y quitaré tu candelabro de su lugar, "
                "si no te arrepientes."
            ),
            "note": "TR ἔρχομαί σοι ταχύ",
        },
        54: {
            "trPositions": list(range(21, 29)),
            "spanish": "que está en medio del paraíso de Dios.",
            "note": "TR ἐν μέσῳ τοῦ παραδείσου τοῦ Θεοῦ",
        },
        55: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y escribe al ángel de la iglesia de los esmirneos:",
            "note": "TR τῆς ἐκκλησίας Σμυρναίων (not ἐν Σμύρνῃ)",
        },
        57: {
            "trPositions": list(range(1, 14)),
            "spanish": "Conozco tus obras, y tu tribulación y tu pobreza —pero eres rico—,",
            "note": "TR Οἶδά σου τὰ ἔργα καὶ… πλούσιος δὲ εἶ",
        },
        58: {
            "trPositions": list(range(14, 22)),
            "spanish": "y la blasfemia de los que se dicen ser judíos",
            "note": "TR τῶν λεγόντων (no ἐκ)",
        },
        61: {
            "trPositions": list(range(6, 17)),
            "spanish": (
                "He aquí, el diablo está por echar a algunos de ustedes en prisión "
                "para que sean probados,"
            ),
            "note": "TR ἰδοὺ μέλλει βάλειν ἐξ ὑμῶν ὁ διάβολος",
        },
        68: {
            "trPositions": list(range(1, 13)),
            "spanish": "Conozco tus obras y dónde habitas: donde está el trono de Satanás.",
            "note": "TR Οἶδα τὰ ἔργα σου καὶ ποῦ κατοικεῖς",
        },
        69: {
            "trPositions": list(range(13, 31)),
            "spanish": (
                "Y retienes mi nombre y no negaste mi fe, "
                "incluso en los días en que Antipas,"
            ),
            "note": "TR ἐν ταῖς ἡμέραις ἐν αἷς Ἀντιπᾶς",
        },
        70: {
            "trPositions": list(range(31, 40)),
            "spanish": "mi testigo, el fiel, quien fue matado entre ustedes,",
            "note": "TR ὁ μάρτυς μου ὁ πιστός (no Morph extra μου)",
        },
        71: {
            "trPositions": list(range(40, 44)),
            "spanish": "donde habita Satanás.",
            "note": "TR ὅπου κατοικεῖ ὁ Σατανᾶς",
        },
        75: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Así también tú tienes a quienes retienen la enseñanza "
                "de los nicolaítas, la cual yo odio."
            ),
            "note": "TR τῶν Νικολαϊτῶν ὃ μισῶ (not ὁμοίως)",
        },
        76: {
            "trPositions": [1],
            "spanish": "Arrepiéntete.",
            "note": "TR omits Morph οὖν",
        },
        79: {
            "trPositions": list(range(11, 21)),
            "spanish": "Al que vence le daré a comer del maná escondido,",
            "note": "TR δώσω αὐτῷ φαγεῖν ἀπὸ τοῦ μάννα",
        },
        84: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Conozco tus obras, y tu amor, y tu servicio, y tu fe, "
                "y tu perseverancia,"
            ),
            "note": "TR ἀγάπην… διακονίαν… πίστιν (not Morph faith-then-service)",
        },
        85: {
            "trPositions": list(range(18, 28)),
            "spanish": "y tus obras, y que las últimas son más que las primeras.",
            "note": "TR καὶ τὰ ἔργα σου καὶ τὰ ἔσχατα",
        },
        86: {
            "trPositions": list(range(1, 11)),
            "spanish": "Pero tengo unas pocas cosas contra ti: que permites a la mujer Jezabel,",
            "note": "TR ὀλίγα; ἐᾷς",
        },
        87: {
            "trPositions": list(range(11, 24)),
            "spanish": (
                "la que se dice a sí misma profetisa, enseñar y extraviar a mis siervos "
                "para que cometan inmoralidad sexual y coman cosas sacrificadas a ídolos."
            ),
            "note": "TR τὴν λέγουσαν… διδάσκειν καὶ πλανᾶσθαι",
        },
        88: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y le di tiempo para que se arrepintiera de su inmoralidad sexual, "
                "y no se arrepintió."
            ),
            "note": "TR καὶ οὐ μετενόησεν (not Morph οὐ θέλει μετανοῆσαι)",
        },
        89: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "He aquí, yo la arrojo en cama, y a los que cometen adulterio con ella, "
                "en gran tribulación,"
            ),
            "note": "TR ἰδοὺ ἐγὼ βάλλω",
        },
        94: {
            "trPositions": list(range(1, 9)),
            "spanish": "Pero les digo a ustedes y a los demás que están en Tiatira,",
            "note": "TR ὑμῖν δὲ λέγω καὶ λοιποῖς",
        },
        95: {
            "trPositions": list(range(9, 23)),
            "spanish": (
                "a cuantos no tienen esta enseñanza, y quienes no han conocido "
                "las profundidades de Satanás,"
            ),
            "note": "TR καὶ οἵτινες; τὰ βάθη",
        },
        100: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "y las pastoreará con vara de hierro; como vasijas de barro son quebradas, "
                "como también yo la he recibido de mi Padre."
            ),
            "note": "TR ὡς κἀγώ εἴληφα belongs to 2:27, not 2:28",
        },
        101: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y le daré la estrella de la mañana.",
            "note": "TR 2:28 is only καὶ δώσω αὐτῷ τὸν ἀστέρα τὸν πρωϊνόν",
        },
        # Revelation 3
        105: {
            "trPositions": list(range(22, 35)),
            "spanish": "Conozco tus obras: tienes el nombre de que vives, y estás muerto.",
            "note": "TR τὸ ὄνομα; καὶ νεκρὸς εἶ (not adversative gloss)",
        },
        106: {
            "trPositions": list(range(1, 10)),
            "spanish": "Mantente vigilante y fortalece lo que queda, que está por morir,",
            "note": "TR ἃ μέλλει ἀποθανεῖν (present, not Morph ἔμελλον)",
        },
        107: {
            "trPositions": list(range(10, 20)),
            "spanish": "pues no he hallado tus obras completas delante de Dios.",
            "note": "TR ἐνώπιον τοῦ Θεοῦ (omits Morph μου)",
        },
        109: {
            "trPositions": list(range(11, 29)),
            "spanish": (
                "Si, pues, no te mantienes vigilante, vendré sobre ti como ladrón "
                "y de ninguna manera sabrás a qué hora vendré sobre ti."
            ),
            "note": "TR ἥξω ἐπὶ σε ὡς κλέπτης (first ἐπὶ σε is TR-only)",
        },
        110: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "Tienes unos pocos nombres también en Sardis que no han manchado "
                "sus vestiduras,"
            ),
            "note": "TR omits ἀλλά; has καὶ ἐν Σάρδεσιν",
        },
        112: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "El que vence, este será vestido con vestiduras blancas, "
                "y de ninguna manera borraré su nombre del libro de la vida,"
            ),
            "note": "TR οὕτος (this one), not Morph οὕτως (thus)",
        },
        116: {
            "trPositions": list(range(9, 21)),
            "spanish": "Esto dice el santo, el verdadero, el que tiene la llave de David,",
            "note": "TR τὴν κλεῖδα τοῦ Δαβίδ",
        },
        117: {
            "trPositions": list(range(21, 31)),
            "spanish": "el que abre y nadie cierra, y cierra y nadie abre:",
            "note": "TR κλείει… κλείει (presents, not κλείσει / κλείων)",
        },
        118: {
            "trPositions": list(range(1, 11)),
            "spanish": "Conozco tus obras. He aquí, he puesto delante de ti una puerta abierta,",
            "note": "ἰδού → He aquí",
        },
        119: {
            "trPositions": list(range(11, 20)),
            "spanish": "y nadie puede cerrarla, porque tienes poca fuerza,",
            "note": "TR καὶ οὐδεὶς (not Morph ἣν οὐδεὶς)",
        },
        121: {
            "trPositions": list(range(1, 12)),
            "spanish": "He aquí, doy de la sinagoga de Satanás a los que se dicen ser judíos,",
            "note": "ἰδοὺ → He aquí",
        },
        122: {
            "trPositions": list(range(12, 31)),
            "spanish": (
                "y no lo son, sino que mienten. He aquí, haré que vengan y se postren "
                "delante de tus pies,"
            ),
            "note": "ἰδοὺ → He aquí",
        },
        126: {
            "trPositions": list(range(1, 13)),
            "spanish": "He aquí, vengo pronto. Retén lo que tienes, para que nadie tome tu corona.",
            "note": "TR ἰδού ἔρχομαι ταχύ",
        },
        132: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y escribe al ángel de la iglesia de los laodicenses:",
            "note": "TR τῆς ἐκκλησίας Λαοδικέων (not ἐν Λαοδικείᾳ)",
        },
        136: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Así, porque eres tibio, y ni frío ni caliente, "
                "estoy por vomitarte de mi boca."
            ),
            "note": "TR οὔτε ψυχρὸς οὔτε ζεστός (cold then hot)",
        },
        141: {
            "trPositions": list(range(25, 33)),
            "spanish": "y colirio: unge tus ojos, para que veas.",
            "note": "TR καὶ κολλούριον; ἐγχρῖσον (imperative)",
        },
        143: {
            "trPositions": list(range(1, 8)),
            "spanish": "He aquí, estoy de pie a la puerta y llamo.",
            "note": "ἰδοὺ → He aquí",
        },
        145: {
            "trPositions": list(range(18, 29)),
            "spanish": "entraré a él y cenaré con él, y él conmigo.",
            "note": "TR omits Morph καὶ before εἰσελεύσομαι",
        },
        # Revelation 4
        149: {
            "trPositions": list(range(1, 11)),
            "spanish": "Después de esto vi, y he aquí: una puerta abierta en el cielo,",
            "note": "ἰδοὺ → He aquí",
        },
        150: {
            "trPositions": list(range(11, 24)),
            "spanish": "y la primera voz que oí, como de trompeta que hablaba conmigo, decía:",
            "note": "TR λέγουσα (agrees with φωνή)",
        },
        152: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y enseguida estuve en el Espíritu, y he aquí: un trono estaba puesto "
                "en el cielo, y uno sentado en el trono"
            ),
            "note": "TR καὶ εὐθέως; ἰδοὺ → He aquí",
        },
        153: {
            "trPositions": list(range(1, 11)),
            "spanish": (
                "y el que estaba sentado era semejante en apariencia a una piedra "
                "de jaspe y de cornalina,"
            ),
            "note": "TR ἦν ὅμοιος",
        },
        155: {
            "trPositions": list(range(1, 24)),
            "spanish": (
                "y alrededor del trono había veinticuatro tronos, y sobre los tronos "
                "vi a los veinticuatro ancianos sentados, vestidos con ropas blancas,"
            ),
            "note": "TR εἴκοσι καὶ τέσσαρες; εἴδον τοὺς εἴκοσι καὶ τέσσαρας",
        },
        156: {
            "trPositions": list(range(24, 32)),
            "spanish": "y tenían sobre sus cabezas coronas de oro",
            "note": "TR καὶ ἔσχον ἐπὶ τὰς κεφαλάς",
        },
        157: {
            "trPositions": list(range(1, 11)),
            "spanish": "y del trono salen relámpagos y truenos y voces,",
            "note": "TR ἀστραπαὶ καὶ βρονταί καὶ φωναί (not Morph voices-then-thunder)",
        },
        160: {
            "trPositions": list(range(1, 9)),
            "spanish": "y delante del trono, un mar de vidrio semejante al cristal.",
            "note": "TR omits Morph ὡς",
        },
        161: {
            "trPositions": list(range(9, 25)),
            "spanish": "Y en medio del trono y alrededor del trono, cuatro seres vivientes llenos de ojos por delante y por detrás.",
            "note": "punctuation after 4:6a",
        },
        163: {
            "trPositions": list(range(14, 23)),
            "spanish": "y el tercer ser viviente tenía el rostro como un hombre,",
            "note": "TR καὶ τὸ τρίτον; ὡς ἄνθρωπος (nominative)",
        },
        165: {
            "trPositions": list(range(1, 11)),
            "spanish": "y los cuatro seres vivientes, cada uno por sí, tenían seis alas;",
            "note": "TR ἓν καθ’ ἑαυτὸ εἴχον (not ἓν καθ’ ἓν αὐτῶν ἔχων)",
        },
        167: {
            "trPositions": list(range(16, 24)),
            "spanish": "y no tienen descanso día y noche, diciendo:",
            "note": "punctuation before the trisagion",
        },
        168: {
            "trPositions": list(range(24, 32)),
            "spanish": "Santo, santo, santo, el Señor Dios, el Todopoderoso,",
            "note": "punctuation before ὁ ἦν",
        },
        170: {
            "trPositions": list(range(1, 16)),
            "spanish": "y cuando los seres vivientes den gloria, honra y agradecimiento al que está sentado en el trono,",
            "note": "punctuation before τῷ ζῶντι",
        },
        172: {
            "trPositions": list(range(1, 13)),
            "spanish": "los veinticuatro ancianos caerán delante del que está sentado en el trono,",
            "note": "TR εἴκοσι καὶ τέσσαρες",
        },
        173: {
            "trPositions": list(range(13, 22)),
            "spanish": "y adoran al que vive por los siglos de los siglos,",
            "note": "TR προσκυνουσιν (present, not future)",
        },
        174: {
            "trPositions": list(range(22, 31)),
            "spanish": "y echan sus coronas delante del trono, diciendo:",
            "note": "TR βαλλουσιν (present, not future)",
        },
        175: {
            "trPositions": list(range(1, 4)),
            "spanish": "Digno eres, Señor,",
            "note": "TR Ἄξιος εἶ Κύριε (omits Morph καὶ ὁ θεὸς ἡμῶν)",
        },
        176: {
            "trPositions": list(range(4, 13)),
            "spanish": "de recibir la gloria, la honra y el poder,",
            "note": "punctuation before ὅτι",
        },
        177: {
            "trPositions": list(range(13, 26)),
            "spanish": "porque tú creaste todas las cosas, y por tu voluntad existen y fueron creadas",
            "note": "TR εἰσιν (not Morph ἦσαν)",
        },
        # Revelation 5
        179: {
            "trPositions": list(range(1, 8)),
            "spanish": "y vi a un ángel poderoso proclamando con gran voz:",
            "note": "TR φωνῇ μεγάλῃ (no ἐν); punctuation",
        },
        180: {
            "trPositions": list(range(8, 19)),
            "spanish": "¿Quién es digno de abrir el libro y desatar sus sellos?",
            "note": "TR Τίς ἐστιν ἄξιος",
        },
        182: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y yo lloraba mucho porque nadie fue hallado digno de abrir "
                "y leer el libro ni de mirarlo."
            ),
            "note": "TR ἀνοῖξαι καὶ ἀναγνῶναι τὸ βιβλίον",
        },
        184: {
            "trPositions": list(range(10, 20)),
            "spanish": "He aquí, ha vencido el león que es de la tribu de Judá,",
            "note": "TR ἰδοὺ; ὁ ὢν ἐκ τῆς φυλῆς Ἰούδα",
        },
        185: {
            "trPositions": list(range(20, 32)),
            "spanish": "la raíz de David, para abrir el libro y desatar sus siete sellos.",
            "note": "TR καὶ λῦσαι τὰς ἑπτὰ σφραγῖδας",
        },
        186: {
            "trPositions": list(range(1, 22)),
            "spanish": (
                "Y vi, y he aquí, en medio del trono y de los cuatro seres vivientes "
                "y en medio de los ancianos, un cordero de pie como sacrificado,"
            ),
            "note": "TR καὶ εἶδον καὶ ἰδού",
        },
        187: {
            "trPositions": list(range(22, 37)),
            "spanish": (
                "que tenía siete cuernos y siete ojos, que son los siete espíritus "
                "de Dios enviados"
            ),
            "note": "TR τὰ ἑπτὰ τοῦ Θεοῦ πνεύματα τὰ ἀπεσταλμένα",
        },
        188: {
            "trPositions": list(range(37, 41)),
            "spanish": "a toda la tierra.",
            "note": "remainder of ἀπεσταλμένα εἰς πᾶσαν τὴν γῆν",
        },
        189: {
            "trPositions": list(range(1, 15)),
            "spanish": "Y vino y tomó el libro de la mano derecha del que estaba sentado en el trono.",
            "note": "TR εἴληφεν τὸ βιβλίον",
        },
        190: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y cuando tomó el libro, los cuatro seres vivientes y los veinticuatro "
                "ancianos cayeron delante del cordero,"
            ),
            "note": "TR εἴκοσιτέσσαρες as one form",
        },
        191: {
            "trPositions": list(range(17, 25)),
            "spanish": "teniendo cada uno liras y copas de oro llenas de incienso,",
            "note": "TR κιθάρας (plural, not κιθάραν)",
        },
        195: {
            "trPositions": list(range(16, 36)),
            "spanish": (
                "porque fuiste sacrificado y con tu sangre nos compraste para Dios "
                "de toda tribu, lengua, pueblo y nación,"
            ),
            "note": "TR ἠγόρασας τῷ Θεῷ ἡμᾶς",
        },
        196: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "e hiciste de nosotros para nuestro Dios reyes y sacerdotes, "
                "y reinaremos sobre la tierra."
            ),
            "note": "TR ἡμᾶς / βασιλεῖς / βασιλεύσομεν (not αὐτοὺς / βασιλείαν / βασιλεύουσιν)",
        },
        201: {
            "trPositions": list(range(1, 21)),
            "spanish": (
                "y toda criatura que está en el cielo y en la tierra y debajo de la tierra "
                "y sobre el mar,"
            ),
            "note": "TR ὃ ἐστιν; ἐν τῇ γῇ (not ἐπὶ τῆς γῆς)",
        },
        202: {
            "trPositions": list(range(21, 30)),
            "spanish": "y todo lo que hay en ellos, las oí diciendo:",
            "note": "TR ἃ ἐστιν καὶ τὰ ἐν αὐτοῖς πάντα",
        },
        204: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "Y los cuatro seres vivientes decían: Amén. Y los veinticuatro ancianos "
                "cayeron y adoraron al que vive por los siglos de los siglos."
            ),
            "note": "TR οἱ εἴκοσιτέσσαρες; ζῶντι εἰς τοὺς αἰῶνας τῶν αἰώνων",
        },
        # Revelation 6
        205: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y vi cuando el cordero abrió uno de los sellos",
            "note": "TR μίαν ἐκ τῶν σφραγίδων (no ἑπτά)",
        },
        206: {
            "trPositions": list(range(11, 25)),
            "spanish": (
                "y oí a uno de los cuatro seres vivientes decir como con voz de trueno: "
                "Ven y mira."
            ),
            "note": "TR Ἔρχου καὶ βλέπε",
        },
        207: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "y vi, y he aquí, un caballo blanco, y el que estaba sentado sobre él "
                "tenía un arco"
            ),
            "note": "TR ἰδοὺ; ἐπ’ αὐτῷ",
        },
        209: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y cuando abrió el segundo sello, oí al segundo ser viviente decir: "
                "Ven y mira."
            ),
            "note": "TR τὴν δευτέραν σφραγῖδα; Ἔρχου καὶ βλέπε",
        },
        212: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y cuando abrió el tercer sello, oí al tercer ser viviente decir: "
                "Ven y mira;"
            ),
            "note": "TR τὴν τρίτην σφραγῖδα; Ἔρχου καὶ βλέπε",
        },
        213: {
            "trPositions": list(range(15, 32)),
            "spanish": (
                "y vi, y he aquí, un caballo negro, y el que estaba sentado sobre él "
                "tenía una balanza en su mano."
            ),
            "note": "TR ἰδοὺ; ἐπ’ αὐτῷ",
        },
        214: {
            "trPositions": list(range(1, 10)),
            "spanish": "y oí una voz en medio de los cuatro seres vivientes que decía:",
            "note": "TR ἤκουσα φωνήν (no ὡς)",
        },
        217: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y cuando abrió el cuarto sello, oí la voz del cuarto ser viviente "
                "que decía: Ven y mira."
            ),
            "note": "TR λέγουσαν; Ἔρχου καὶ βλέπε",
        },
        218: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "y vi, y he aquí, un caballo pálido, y el que estaba sentado sobre él "
                "tenía por nombre Muerte"
            ),
            "note": "TR ἰδοὺ",
        },
        219: {
            "trPositions": list(range(16, 32)),
            "spanish": (
                "y el Hades lo seguía; y les fue dada autoridad para matar "
                "sobre la cuarta parte de la tierra"
            ),
            "note": "TR ἀποκτεῖναι before ἐπὶ τὸ τέταρτον",
        },
        220: {
            "trPositions": list(range(32, 46)),
            "spanish": (
                "con espada, con hambre, con muerte y por las bestias de la tierra."
            ),
            "note": "instruments after ἀποκτεῖναι ἐπὶ τὸ τέταρτον",
        },
        222: {
            "trPositions": list(range(1, 6)),
            "spanish": "y clamaban con gran voz, diciendo:",
            "note": "TR ἔκραζον (imperfect, not ἔκραξαν)",
        },
        223: {
            "trPositions": list(range(6, 15)),
            "spanish": "¿Hasta cuándo, Soberano, el santo y el verdadero,",
            "note": "TR ὁ ἅγιος καὶ ὁ ἀληθινός",
        },
        225: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y se les dieron a cada uno túnicas blancas, y se les dijo que "
                "descansaran todavía un poco de tiempo"
            ),
            "note": "TR ἐδόθησαν ἑκάστοις στολαὶ λευκαί (plural)",
        },
        226: {
            "trPositions": list(range(14, 31)),
            "spanish": (
                "hasta que se completen también sus compañeros siervos y sus hermanos "
                "que iban a ser matados como ellos."
            ),
            "note": "TR ἕως οὗ πληρωσονται (verb was unmapped; no 'número')",
        },
        228: {
            "trPositions": list(range(9, 22)),
            "spanish": (
                "y he aquí, hubo un gran terremoto, y el sol se volvió negro "
                "como tela de saco de pelo"
            ),
            "note": "TR καὶ ἰδού σεισμός",
        },
        229: {
            "trPositions": list(range(22, 28)),
            "spanish": "y la luna se volvió como sangre.",
            "note": "TR ἡ σελήνη (no ὅλη)",
        },
        231: {
            "trPositions": list(range(10, 20)),
            "spanish": (
                "como una higuera arroja sus higos verdes, sacudida por un gran viento."
            ),
            "note": "TR ὑπὸ μεγάλου ἀνέμου",
        },
        232: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "y el cielo se apartó como un libro que se enrolla, y toda montaña "
                "e isla fueron removidas de sus lugares."
            ),
            "note": "TR οὐρανός without ὁ; clear morph-article gap",
        },
        233: {
            "trPositions": list(range(1, 35)),
            "spanish": (
                "y los reyes de la tierra, y los magnates, y los ricos, y los comandantes, "
                "y los poderosos, y todo siervo y todo libre se escondieron en las cuevas "
                "y entre las rocas de las montañas."
            ),
            "note": "TR πλούσιοι / χιλίαρχοι / δυνατοί; πᾶς ἐλεύθερος",
        },
        236: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "porque ha llegado el gran día de su ira, ¿y quién puede mantenerse en pie?"
            ),
            "note": "TR τῆς ὀργῆς αὐτοῦ (not αὐτῶν)",
        },
        234: {
            "trPositions": list(range(1, 8)),
            "spanish": "y dicen a las montañas y a las rocas:",
            "note": "punctuation before the quoted plea",
        },
        # Revelation 7
        237: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y después de esto vi a cuatro ángeles de pie "
                "en las cuatro esquinas de la tierra"
            ),
            "note": "TR Καὶ μετὰ ταῦτα (Καὶ was unmapped)",
        },
        241: {
            "trPositions": [1],
            "spanish": "diciendo:",
            "note": "punctuation before the prohibition",
        },
        243: {
            "trPositions": list(range(12, 24)),
            "spanish": (
                "hasta que hayamos sellado en sus frentes a los siervos "
                "de nuestro Dios."
            ),
            "note": "TR ἄχρις οὗ",
        },
        244: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y oí el número de los sellados: ciento cuarenta y cuatro mil "
                "sellados de toda tribu de los hijos de Israel."
            ),
            "note": "TR ρμδ χιλιάδες (numeral abbreviation; parser now keeps rmd)",
        },
        245: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "de la tribu de Judá, doce mil sellados; de la tribu de Rubén, "
                "doce mil sellados; de la tribu de Gad, doce mil sellados."
            ),
            "note": "TR ἐσφραγισμένοι after each ιβ χιλιάδες",
        },
        246: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "de la tribu de Aser, doce mil sellados; de la tribu de Neftalí, "
                "doce mil sellados; de la tribu de Manasés, doce mil sellados."
            ),
            "note": "TR ἐσφραγισμένοι after each ιβ χιλιάδες",
        },
        247: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "de la tribu de Simeón, doce mil sellados; de la tribu de Leví, "
                "doce mil sellados; de la tribu de Isacar, doce mil sellados."
            ),
            "note": "TR ἐσφραγισμένοι after each ιβ χιλιάδες",
        },
        248: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "de la tribu de Zabulón, doce mil sellados; de la tribu de José, "
                "doce mil sellados; de la tribu de Benjamín, doce mil sellados."
            ),
            "note": "TR ἐσφραγισμένοι after each ιβ χιλιάδες",
        },
        249: {
            "trPositions": list(range(1, 13)),
            "spanish": "Después de esto vi, y he aquí, una gran multitud que nadie podía contar",
            "note": "TR ἰδοὺ",
        },
        253: {
            "trPositions": list(range(1, 6)),
            "spanish": "y clamando con gran voz, diciendo:",
            "note": "TR κράζοντες (participle, not κράζουσι)",
        },
        254: {
            "trPositions": list(range(6, 19)),
            "spanish": (
                "La salvación a nuestro Dios, al que está sentado en el trono, "
                "y al cordero."
            ),
            "note": "SCV: τῷ Θεῷ ἡμῶν τῷ καθημένῳ ἐπὶ τοῦ θρόνου (no second τοῦ θεοῦ ἡμῶν)",
        },
        256: {
            "trPositions": list(range(16, 28)),
            "spanish": (
                "y cayeron delante del trono sobre el rostro y adoraron a Dios,"
            ),
            "note": "TR ἐπὶ πρόσωπον (singular; Morph τὰ πρόσωπα)",
        },
        257: {
            "trPositions": list(range(1, 3)),
            "spanish": "diciendo: Amén.",
            "note": "punctuation after Ἀμήν",
        },
        259: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y uno de los ancianos respondió, diciéndome:",
            "note": "punctuation before the question",
        },
        261: {
            "trPositions": list(range(1, 4)),
            "spanish": "Y le dije:",
            "note": "punctuation before the reply",
        },
        262: {
            "trPositions": list(range(4, 10)),
            "spanish": "Señor, tú lo sabes. Y me dijo:",
            "note": "TR Κύριε (no μου)",
        },
        270: {
            "trPositions": list(range(11, 18)),
            "spanish": "y los guiará a fuentes de aguas vivas",
            "note": "TR ζώσας πηγὰς ὑδάτων (not ζωῆς)",
        },
        # Revelation 8
        274: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "Y vino otro ángel y se puso sobre el altar, "
                "con un incensario de oro."
            ),
            "note": "TR ἐπὶ τὸ θυσιαστήριον (accusative)",
        },
        279: {
            "trPositions": list(range(20, 29)),
            "spanish": "Y hubo voces, truenos, relámpagos y un terremoto.",
            "note": "TR φωναὶ καὶ βρονταὶ καὶ ἀστραπαὶ (not Morph thunder-first)",
        },
        281: {
            "trPositions": list(range(1, 6)),
            "spanish": "Y el primer ángel tocó la trompeta,",
            "note": "TR ὁ πρῶτος ἄγγελος (ἄγγελος is TR-only vs Morph)",
        },
        282: {
            "trPositions": list(range(6, 13)),
            "spanish": "y hubo granizo y fuego mezclados con sangre,",
            "note": "TR μεμιγμένα αἵματι (no ἐν)",
        },
        284: {
            "trPositions": list(range(18, 24)),
            "spanish": "Y se quemó la tercera parte de los árboles,",
            "note": "TR has no τὸ τρίτον τῆς γῆς κατεκάη",
        },
        293: {
            "trPositions": list(range(16, 28)),
            "spanish": (
                "y cayó sobre la tercera parte de los ríos "
                "y sobre los manantiales de aguas."
            ),
            "note": "TR πηγὰς ὑδάτων (no τῶν)",
        },
        294: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y el nombre de la estrella se llama Ajenjo.",
            "note": "TR Ἄψινθος (no ὁ)",
        },
        295: {
            "trPositions": list(range(8, 16)),
            "spanish": "Y la tercera parte de las aguas se convierte en ajenjo,",
            "note": "TR γίνεται (present, not ἐγένετο)",
        },
        296: {
            "trPositions": list(range(16, 25)),
            "spanish": (
                "y muchos de los hombres murieron por las aguas, "
                "porque se hicieron amargas."
            ),
            "note": "TR πολλοὶ ἀνθρώπων (no τῶν)",
        },
        301: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "Y vi y oí a un ángel que volaba en medio del cielo, "
                "diciendo con gran voz:"
            ),
            "note": "TR ἑνὸς ἀγγέλου (not ἀετοῦ)",
        },
        302: {
            "trPositions": list(range(13, 33)),
            "spanish": (
                "¡Ay, ay, ay de los que habitan en la tierra, "
                "por las demás voces de la trompeta de los tres ángeles "
                "que están por tocar!"
            ),
            "note": "TR τοῖς κατοικοῦσιν; φωνῶν",
        },
        # Revelation 9
        311: {
            "trPositions": list(range(17, 33)),
            "spanish": (
                "sino solamente a las personas que no tienen el sello de Dios "
                "en las frentes de ellas."
            ),
            "note": "TR μόνους; ἐπὶ τῶν μετώπων αὐτῶν",
        },
        314: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y en aquellos días las personas buscarán la muerte "
                "y no la encontrarán,"
            ),
            "note": "TR οὐχ εὑρήσουσιν (not οὐ μή)",
        },
        315: {
            "trPositions": list(range(15, 24)),
            "spanish": "y desearán morir, y la muerte huirá de ellas.",
            "note": "TR φεύξεται (future, not φεύγει)",
        },
        321: {
            "trPositions": list(range(1, 22)),
            "spanish": (
                "Y tienen colas semejantes a escorpiones, y había aguijones "
                "en las colas de ellas; y su autoridad para dañar a las personas "
                "durante cinco meses."
            ),
            "note": "TR κέντρα ἦν ἐν ταῖς οὐραῖς; καὶ ἡ ἐξουσία",
        },
        322: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y tienen sobre ellas como rey al ángel del abismo;",
            "note": "TR καὶ ἔχουσιν",
        },
        324: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "El primer ay pasó. He aquí, vienen todavía dos ayes "
                "después de estas cosas."
            ),
            "note": "TR ἰδοὺ; ἔρχονται (plural)",
        },
        326: {
            "trPositions": list(range(6, 22)),
            "spanish": (
                "y oí una voz de entre los cuatro cuernos del altar de oro "
                "que está delante de Dios,"
            ),
            "note": "TR τῶν τεσσάρων κεράτων",
        },
        328: {
            "trPositions": list(range(9, 21)),
            "spanish": (
                "Suelta a los cuatro ángeles que están atados "
                "junto al gran río Éufrates."
            ),
            "note": "drop guillemets; TR ὅς εἴχε already in 327",
        },
        331: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y el número de los ejércitos de la caballería era "
                "doscientos millones; y oí el número de ellos."
            ),
            "note": "TR δύο μυριάδες μυριάδων καὶ ἤκουσα",
        },
        336: {
            "trPositions": list(range(1, 10)),
            "spanish": "Por estas tres murió la tercera parte de las personas,",
            "note": "TR ὑπὸ τῶν τριῶν τούτων (no πληγῶν)",
        },
        337: {
            "trPositions": list(range(10, 27)),
            "spanish": (
                "por el fuego, y por el humo, y por el azufre "
                "que salía de las bocas de ellos."
            ),
            "note": "TR ἐκ τοῦ πυρὸς καὶ ἐκ τοῦ καπνοῦ καὶ ἐκ τοῦ θείου",
        },
        338: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Porque la autoridad de ellos está en la boca de ellos "
                "y en las colas de ellos;"
            ),
            "note": "TR ἡ ἐξουσία αὐτῶν (not τῶν ἵππων); στόματι singular; SCV ἐστιν",
        },
        343: {
            "trPositions": list(range(21, 42)),
            "spanish": (
                "para no adorar a los demonios ni a ídolos de oro, plata, "
                "bronce, piedra y madera,"
            ),
            "note": "TR εἴδωλα without τὰ",
        },
        344: {
            "trPositions": list(range(42, 50)),
            "spanish": "que no puede ver, ni oír, ni caminar.",
            "note": "TR δύναται (singular)",
        },
        # Revelation 10
        347: {
            "trPositions": list(range(10, 17)),
            "spanish": "envuelto en una nube, y un arco iris sobre la cabeza;",
            "note": "TR ἶρις ἐπὶ τῆς κεφαλῆς (no ἡ; no αὐτοῦ)",
        },
        349: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y tenía en la mano de él un pequeño rollo abierto,",
            "note": "TR καὶ εἴχεν (imperfect)",
        },
        352: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y gritó con gran voz, como ruge un león;",
            "note": "TR φωνῇ μεγάλῃ",
        },
        354: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Y cuando hablaron los siete truenos las voces de ellos, "
                "yo estaba por escribir,"
            ),
            "note": "TR τὰς φωνὰς ἑαυτῶν ἔμελλον γράφειν",
        },
        355: {
            "trPositions": list(range(12, 20)),
            "spanish": "y oí una voz del cielo que me decía:",
            "note": "TR λέγουσαν μοι",
        },
        356: {
            "trPositions": list(range(20, 30)),
            "spanish": (
                "Sella las cosas que hablaron los siete truenos, "
                "y no escribas estas cosas."
            ),
            "note": "TR ταὐτά (not αὐτά)",
        },
        358: {
            "trPositions": list(range(14, 21)),
            "spanish": "levantó la mano de él al cielo",
            "note": "TR τὴν χεῖρα αὐτοῦ (no τὴν δεξιάν)",
        },
        359: {
            "trPositions": list(range(1, 11)),
            "spanish": "y juró por el que vive por los siglos de los siglos,",
            "note": "TR ὤμοσεν ἐν τῷ ζῶντι",
        },
        360: {
            "trPositions": list(range(11, 33)),
            "spanish": (
                "quien creó el cielo y lo que hay en él, la tierra y lo que hay "
                "en ella, y el mar y lo que hay en ella,"
            ),
            "note": "TR τὴν θάλασσαν καὶ τὰ ἐν αὐτῇ",
        },
        361: {
            "trPositions": list(range(33, 38)),
            "spanish": "que ya no habrá más tiempo,",
            "note": "TR χρόνος οὐκ ἔσται ἔτι",
        },
        363: {
            "trPositions": list(range(10, 19)),
            "spanish": (
                "cuando esté por tocar la trompeta, y se complete "
                "el misterio de Dios,"
            ),
            "note": "TR καὶ τελεσθῇ (subjunctive, not ἐτελέσθη)",
        },
        367: {
            "trPositions": list(range(15, 34)),
            "spanish": (
                "Ve, toma el pequeño rollo abierto que está en la mano "
                "del ángel que está de pie sobre el mar y sobre la tierra."
            ),
            "note": "TR βιβλαρίδιον; ἀγγέλου without τοῦ",
        },
        368: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y fui al ángel, diciéndole: Dame el pequeño rollo. Y me dice:"
            ),
            "note": "TR Δός μοι (imperative, not δοῦναι)",
        },
        369: {
            "trPositions": list(range(15, 24)),
            "spanish": "Tómalo y cómelo por completo; te amargará el vientre,",
            "note": "drop guillemets",
        },
        370: {
            "trPositions": list(range(24, 33)),
            "spanish": "pero en tu boca será dulce como miel.",
            "note": "drop guillemets",
        },
        374: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y me dice: Es necesario que profetices otra vez sobre "
                "muchos pueblos, naciones, lenguas y reyes."
            ),
            "note": "TR λέγει (singular, not λέγουσιν)",
        },
        # Revelation 11
        375: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Y se me dio una caña semejante a una vara, y el ángel "
                "estaba de pie, diciendo:"
            ),
            "note": "TR καὶ ὁ ἄγγελος εἰστήκει λέγων",
        },
        376: {
            "trPositions": list(range(12, 27)),
            "spanish": (
                "Levántate y mide el santuario de Dios, el altar "
                "y a los que adoran en él."
            ),
            "note": "TR Ἔγειραι; drop guillemets",
        },
        377: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y echa fuera el atrio exterior del santuario y no lo midas,",
            "note": "TR ἔκβαλε ἔξω (not ἔξωθεν); καὶ not 'Pero'",
        },
        380: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y daré a mis dos testigos, y profetizarán mil doscientos "
                "sesenta días, vestidos de tela áspera."
            ),
            "note": "TR καὶ προφητεύσουσιν; drop closing guillemet",
        },
        381: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Estos son los dos olivos y los dos candelabros que están "
                "de pie delante del Dios de la tierra."
            ),
            "note": "TR τοῦ Θεοῦ τῆς γῆς (not κυρίου)",
        },
        383: {
            "trPositions": list(range(18, 28)),
            "spanish": "y si alguien quiere dañarlos, así debe ser matado.",
            "note": "TR εἴ τις αὐτοὺς θέλῃ ἀδικῆσαι (θέλῃ was unmapped)",
        },
        384: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Estos tienen autoridad para cerrar el cielo, para que no "
                "caiga lluvia en los días de la profecía de ellos;"
            ),
            "note": "TR ὑετὸς ἐν ἡμέραις αὐτῶν τῆς προφητείας (no τὴν)",
        },
        385: {
            "trPositions": list(range(16, 35)),
            "spanish": (
                "y tienen autoridad sobre las aguas para convertirlas en sangre "
                "y para herir la tierra con toda plaga cuantas veces quieran."
            ),
            "note": "TR πάσῃ πληγῇ (no ἐν)",
        },
        386: {
            "trPositions": list(range(1, 24)),
            "spanish": (
                "Y cuando terminen el testimonio de ellos, la bestia que sube "
                "del abismo hará guerra contra ellos, los vencerá y los matará."
            ),
            "note": "TR ποιήσει πόλεμον μετ’ αὐτῶν (πόλεμον before μετ’)",
        },
        387: {
            "trPositions": list(range(1, 11)),
            "spanish": (
                "Y los cadáveres de ellos estarán en la plaza de la gran ciudad,"
            ),
            "note": "TR τὰ πτῶματα (plural); πόλεως without τῆς",
        },
        388: {
            "trPositions": list(range(11, 23)),
            "spanish": (
                "que espiritualmente se llama Sodoma y Egipto, donde también "
                "fue crucificado nuestro Señor."
            ),
            "note": "TR ὁ Κύριος ἡμῶν (not αὐτῶν)",
        },
        389: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "Y de los pueblos, tribus, lenguas y naciones verán los cadáveres "
                "de ellos durante tres días y medio,"
            ),
            "note": "TR βλέψουσιν; τὰ πτῶματα",
        },
        390: {
            "trPositions": list(range(19, 28)),
            "spanish": (
                "y no permitirán que los cadáveres de ellos sean puestos en tumbas."
            ),
            "note": "TR μνῆματα (plural)",
        },
        391: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Y los que habitan en la tierra se alegrarán por ellos "
                "y se regocijarán,"
            ),
            "note": "TR χάρουσιν / εὐφρανθήσονται (future)",
        },
        393: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Y después de los tres días y medio un espíritu de vida "
                "procedente de Dios entró sobre ellos,"
            ),
            "note": "TR εἰσῆλθεν ἐπ’ αὐτούς (not ἐν αὐτοῖς)",
        },
        395: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y oyeron una gran voz del cielo que les decía:",
            "note": "TR φωνὴν μεγάλην",
        },
        396: {
            "trPositions": list(range(10, 20)),
            "spanish": "Suban aquí. Y subieron al cielo en la nube,",
            "note": "TR Ἀνάβητε; drop guillemets",
        },
        401: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "El segundo ay pasó. Y he aquí, el tercer ay viene pronto."
            ),
            "note": "TR καὶ ἰδού",
        },
        404: {
            "trPositions": list(range(14, 26)),
            "spanish": (
                "Los reinos del mundo han llegado a ser de nuestro Señor "
                "y del Cristo de él,"
            ),
            "note": "TR Ἐγένοντο αἱ βασιλεῖαι (plural)",
        },
        405: {
            "trPositions": list(range(26, 33)),
            "spanish": "y él reinará por los siglos de los siglos.",
            "note": "drop guillemets",
        },
        406: {
            "trPositions": list(range(1, 25)),
            "spanish": (
                "Y los veinticuatro ancianos, que estaban sentados delante de Dios "
                "en los tronos de ellos, cayeron sobre los rostros de ellos "
                "y adoraron a Dios,"
            ),
            "note": "TR εἴκοσι καὶ τέσσαρες",
        },
        408: {
            "trPositions": list(range(2, 17)),
            "spanish": (
                "Te damos gracias, Señor Dios, el Todopoderoso, el que es "
                "y el que era y el que viene,"
            ),
            "note": "TR καὶ ὁ ἐρχόμενος (Morph omits)",
        },
        410: {
            "trPositions": list(range(1, 34)),
            "spanish": (
                "Y las naciones se enfurecieron, y vino tu ira y el tiempo "
                "de juzgar a los muertos y de dar la recompensa a tus siervos "
                "los profetas, a los santos y a los que temen tu nombre,"
            ),
            "note": "TR καὶ τὰ ἔθνη",
        },
        411: {
            "trPositions": list(range(34, 45)),
            "spanish": (
                "a los pequeños y a los grandes, y de destruir a los que "
                "destruyen la tierra."
            ),
            "note": "TR τοῖς μικροῖς καὶ τοῖς μεγάλοις; drop guillemets",
        },
        412: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y se abrió el santuario de Dios en el cielo,",
            "note": "TR ὁ ναὸς τοῦ Θεοῦ ἐν τῷ οὐρανῷ (no extra ὁ)",
        },
        # Revelation 12
        416: {
            "trPositions": list(range(12, 27)),
            "spanish": (
                "y la luna debajo de sus pies, y sobre su cabeza "
                "una corona de doce estrellas."
            ),
            "note": "punctuation",
        },
        417: {
            "trPositions": list(range(1, 10)),
            "spanish": (
                "y estando embarazada, grita con dolores de parto "
                "y atormentada para dar a luz."
            ),
            "note": "TR no καὶ before κράζει",
        },
        418: {
            "trPositions": list(range(1, 13)),
            "spanish": "Y apareció otra señal en el cielo, y he aquí, un gran dragón rojo",
            "note": "TR ἰδού",
        },
        419: {
            "trPositions": list(range(13, 26)),
            "spanish": (
                "que tenía siete cabezas y diez cuernos, "
                "y sobre sus cabezas siete diademas."
            ),
            "note": "TR διαδήματα ἑπτά (ἑπτά after the noun)",
        },
        425: {
            "trPositions": list(range(14, 26)),
            "spanish": "y su hijo fue arrebatado hacia Dios y su trono.",
            "note": "TR πρὸς τὸν Θεὸν καὶ τὸν θρόνον (no second πρός)",
        },
        426: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y la mujer huyó al desierto, donde tiene un lugar "
                "preparado por Dios"
            ),
            "note": "TR ὅπου ἔχει τόπον (no ἐκεῖ before τόπον)",
        },
        428: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y hubo guerra en el cielo: Miguel y sus ángeles "
                "combatieron contra el dragón"
            ),
            "note": "TR ἐπολέμησαν κατὰ τοῦ δράκοντος (not τοῦ πολεμῆσαι μετά)",
        },
        430: {
            "trPositions": list(range(1, 12)),
            "spanish": "y no pudieron, ni se halló ya lugar para ellos en el cielo.",
            "note": "TR ἴσχυσαν (plural)",
        },
        434: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y oí una gran voz que decía en el cielo:",
            "note": "TR φωνὴν μεγάλην λέγουσαν ἐν τῷ οὐρανῷ",
        },
        436: {
            "trPositions": list(range(28, 45)),
            "spanish": (
                "porque fue derribado el acusador de nuestros hermanos, "
                "el que los acusa delante de nuestro Dios día y noche."
            ),
            "note": "TR κατεβλήθη; κατηγορῶν αὐτῶν",
        },
        437: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y ellos lo vencieron por medio de la sangre del cordero "
                "y por medio de la palabra de su testimonio"
            ),
            "note": "cordero lowercase",
        },
        440: {
            "trPositions": list(range(11, 25)),
            "spanish": (
                "¡Ay de los que habitan la tierra y el mar, "
                "porque el Diablo ha bajado a ustedes"
            ),
            "note": "TR οὐαὶ τοῖς κατοικοῦσιν τὴν γῆν καὶ τὴν θάλασσαν",
        },
        444: {
            "trPositions": list(range(1, 11)),
            "spanish": "y a la mujer le fueron dadas dos alas del gran águila",
            "note": "TR δύο πτέρυγες (no αἱ)",
        },
        447: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y la serpiente lanzó detrás de la mujer, de su boca, "
                "agua como un río"
            ),
            "note": "TR ὀπίσω τῆς γυναικὸς ἐκ τοῦ στόματος",
        },
        451: {
            "trPositions": list(range(18, 31)),
            "spanish": (
                "los que guardan los mandamientos de Dios y tienen "
                "el testimonio de Jesús Cristo."
            ),
            "note": "TR τοῦ Ἰησοῦ Χριστοῦ",
        },
        452: {
            "trPositions": [],
            "spanish": "",
            "note": "TR has no 12:18; ἐστάθην ἐπὶ τὴν ἄμμον is 13:1",
        },
        # Revelation 13
        453: {
            "trPositions": list(range(1, 21)),
            "spanish": (
                "Y me paré sobre la arena del mar. Y vi que del mar subía "
                "una bestia que tenía siete cabezas y diez cuernos,"
            ),
            "note": "TR καὶ ἐστάθην (1sg); κεφαλὰς ἑπτά καὶ κέρατα δέκα",
        },
        454: {
            "trPositions": list(range(21, 35)),
            "spanish": (
                "y sobre sus cuernos diez diademas, y sobre sus cabezas "
                "nombre de blasfemia."
            ),
            "note": "TR ὄνομα (singular)",
        },
        458: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y vi una de sus cabezas como degollada hasta la muerte;",
            "note": "TR καὶ εἶδον μίαν τῶν κεφαλῶν (no ἐκ)",
        },
        459: {
            "trPositions": list(range(11, 18)),
            "spanish": "y su herida mortal fue sanada",
            "note": "TR καὶ ἡ πληγή",
        },
        460: {
            "trPositions": list(range(18, 26)),
            "spanish": "y toda la tierra se maravilló siguiendo a la bestia.",
            "note": "SCV ἐθαύμασεν ὅλη ἡ γῆ (not ἐθαυμάσθη ἐν ὅλῃ τῇ γῇ)",
        },
        461: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y adoraron al dragón, que dio autoridad a la bestia,",
            "note": "TR τόν δράκοντα ὅς ἔδωκεν ἐξουσίαν (not ὅτι / τὴν)",
        },
        462: {
            "trPositions": list(range(10, 15)),
            "spanish": "y adoraron a la bestia, diciendo:",
            "note": "TR τὸ θηρίον",
        },
        463: {
            "trPositions": list(range(15, 24)),
            "spanish": (
                "¿Quién es semejante a la bestia? ¿Quién puede combatir contra ella?"
            ),
            "note": "TR no καὶ before the second Τίς",
        },
        465: {
            "trPositions": list(range(1, 11)),
            "spanish": "y abrió su boca para blasfemia contra Dios,",
            "note": "TR εἰς βλασφημίαν (singular)",
        },
        466: {
            "trPositions": list(range(11, 19)),
            "spanish": "para blasfemar su nombre y su morada,",
            "note": "βλασφημῆσαι τὸ ὄνομα … τὴν σκηνήν",
        },
        467: {
            "trPositions": list(range(19, 25)),
            "spanish": "y a los que habitan en el cielo.",
            "note": "TR καὶ τοὺς ἐν τῷ οὐρανῷ σκηνοῦντας",
        },
        468: {
            "trPositions": list(range(1, 12)),
            "spanish": "Y le fue dado hacer guerra contra los santos y vencerlos,",
            "note": "TR πόλεμον ποιῆσαι (ποιῆσαι after πόλεμον)",
        },
        469: {
            "trPositions": list(range(12, 23)),
            "spanish": (
                "y le fue dada autoridad sobre toda tribu, lengua y nación."
            ),
            "note": "TR no λαόν",
        },
        470: {
            "trPositions": list(range(1, 10)),
            "spanish": "y todos los que habitan sobre la tierra la adorarán,",
            "note": "TR προσκυνήσουσιν αὐτῷ",
        },
        471: {
            "trPositions": list(range(10, 26)),
            "spanish": (
                "cuyos nombres no están escritos en el libro de la vida "
                "del cordero degollado desde la fundación del mundo."
            ),
            "note": "TR ὧν … τὰ ὀνόματα; no αὐτοῦ; no τοῦ before ἐσφαγμένου",
        },
        473: {
            "trPositions": list(range(1, 8)),
            "spanish": "Si alguien lleva al cautiverio, al cautiverio va;",
            "note": "TR αἰχμαλωσίαν συνάγει εἰς αἰχμαλωσίαν ὑπάγει",
        },
        474: {
            "trPositions": list(range(8, 18)),
            "spanish": (
                "si alguien mata con espada, es necesario que él sea "
                "matado con espada."
            ),
            "note": "TR ἐν μαχαίρᾳ ἀποκτενεῖ δεῖ αὐτὸν ἐν μαχαίρᾳ ἀποκτανθῆναι",
        },
        479: {
            "trPositions": list(range(11, 26)),
            "spanish": (
                "y hace que la tierra y los que habitan en ella adoren "
                "a la primera bestia"
            ),
            "note": "TR τοὺς κατοικοῦντας ἐν αὐτῇ",
        },
        481: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "Y hace grandes señales, hasta hacer que fuego baje "
                "del cielo a la tierra delante de la gente."
            ),
            "note": "TR πῦρ ποιῇ καταβαίνειν ἐκ τοῦ οὐρανοῦ",
        },
        486: {
            "trPositions": list(range(10, 29)),
            "spanish": (
                "para que también hable la imagen de la bestia y haga "
                "que todos los que no adoren la imagen de la bestia sean matados."
            ),
            "note": "TR τὴν εἰκόνα; ἵνα ἀποκτανθῶσιν",
        },
        489: {
            "trPositions": list(range(21, 36)),
            "spanish": "reciban una marca en su mano derecha o en sus frentes.",
            "note": "TR δώσῃ; ἐπὶ τῶν μετώπων (plural)",
        },
        490: {
            "trPositions": list(range(1, 16)),
            "spanish": "y que nadie pueda comprar ni vender, sino el que tiene la marca,",
            "note": "TR ἢ τὸ ὄνομα (ἢ after χάραγμα)",
        },
        491: {
            "trPositions": list(range(16, 26)),
            "spanish": "o el nombre de la bestia o el número de su nombre.",
            "note": "TR ἢ τὸ ὄνομα … ἢ τὸν ἀριθμόν",
        },
        492: {
            "trPositions": list(range(1, 5)),
            "spanish": "Aquí está la sabiduría.",
            "note": "ὧδε ἡ σοφία ἐστίν",
        },
        493: {
            "trPositions": list(range(5, 14)),
            "spanish": "El que tiene entendimiento, calcule el número de la bestia,",
            "note": "TR τὸν νοῦν",
        },
        495: {
            "trPositions": list(range(18, 23)),
            "spanish": "y su número es seiscientos sesenta y seis.",
            "note": "TR χξϛ (numeral abbreviation = 666)",
        },
        # Revelation 14
        496: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y vi, y he aquí: un cordero de pie sobre el monte Sion,",
            "note": "TR ἰδού; ἀρνίον (no τό); ἑστηκός",
        },
        497: {
            "trPositions": list(range(11, 29)),
            "spanish": (
                "y con él ciento cuarenta y cuatro mil, que tenían escrito "
                "sobre sus frentes el nombre de su Padre."
            ),
            "note": "TR only τὸ ὄνομα τοῦ πατρός (no ὄνομα αὐτοῦ καί)",
        },
        499: {
            "trPositions": list(range(16, 25)),
            "spanish": "y oí una voz de arpistas que tocaban sus arpas.",
            "note": "TR καὶ φωνὴν ἤκουσα κιθαρῳδῶν (no ὡς / ἣν)",
        },
        504: {
            "trPositions": list(range(11, 20)),
            "spanish": "estos son los que siguen al cordero adondequiera que va;",
            "note": "TR οὗτοι εἰσιν; ἀρνίῳ lowercase",
        },
        505: {
            "trPositions": list(range(20, 31)),
            "spanish": (
                "estos fueron comprados de entre los hombres como primicias "
                "para Dios y para el cordero."
            ),
            "note": "TR ἀπὸ τῶν ἀνθρώπων; ἀπαρχή",
        },
        506: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "y en su boca no fue hallado engaño; pues son intachables "
                "delante del trono de Dios."
            ),
            "note": "TR δόλος; ἄμωμοι γάρ εἰσιν ἐνώπιον τοῦ θρόνου τοῦ Θεοῦ",
        },
        507: {
            "trPositions": list(range(1, 26)),
            "spanish": (
                "Y vi otro ángel que volaba en medio del cielo, teniendo "
                "evangelio eterno para anunciar a los que habitan sobre la tierra, "
                "y a toda nación, tribu, lengua y pueblo."
            ),
            "note": "TR τοὺς κατοικοῦντας (not καθημένους); no ἐπί before πᾶν",
        },
        508: {
            "trPositions": list(range(1, 5)),
            "spanish": "diciendo con gran voz:",
            "note": "λέγοντα ἐν φωνῇ μεγάλῃ",
        },
        510: {
            "trPositions": list(range(19, 34)),
            "spanish": "y adoren al que hizo el cielo, la tierra, el mar y las fuentes de aguas.",
            "note": "TR καὶ τὴν θάλασσαν",
        },
        511: {
            "trPositions": list(range(1, 6)),
            "spanish": "Y otro ángel siguió, diciendo:",
            "note": "TR no δεύτερος",
        },
        512: {
            "trPositions": list(range(6, 25)),
            "spanish": (
                "¡Cayó, cayó Babilonia, la ciudad grande, porque del vino "
                "de la furia de su prostitución ha dado de beber a todas las naciones!"
            ),
            "note": "TR ἡ πόλις ἡ μεγάλη ὅτι; no τά before ἔθνη",
        },
        513: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y un tercer ángel los siguió, diciendo con gran voz:",
            "note": "TR τρίτος ἄγγελος (no ἄλλος)",
        },
        514: {
            "trPositions": list(range(10, 19)),
            "spanish": "Si alguien adora a la bestia y a su imagen",
            "note": "TR τὸ θηρίον προσκυνεῖ",
        },
        517: {
            "trPositions": list(range(20, 34)),
            "spanish": (
                "y será atormentado con fuego y azufre delante de los santos "
                "ángeles y delante del cordero."
            ),
            "note": "TR τῶν ἁγίων ἀγγέλων; ἀρνίου lowercase",
        },
        518: {
            "trPositions": list(range(1, 11)),
            "spanish": "y el humo de su tormento sube por siglos de siglos",
            "note": "TR ἀναβαίνει εἰς αἰῶνας αἰώνων (no articles)",
        },
        521: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Aquí está la perseverancia de los santos; aquí los que guardan "
                "los mandamientos de Dios y la fe de Jesús."
            ),
            "note": "TR ὧδε … ὧδε",
        },
        522: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y oí una voz del cielo que me decía: Escribe:",
            "note": "TR λεγούσης μοι",
        },
        523: {
            "trPositions": list(range(10, 18)),
            "spanish": "Dichosos los muertos que desde ahora mueren en el Señor.",
            "note": "TR ἀπαρτί (one token)",
        },
        525: {
            "trPositions": list(range(28, 35)),
            "spanish": "y sus obras los siguen.",
            "note": "TR τὰ δὲ ἔργα (not γάρ)",
        },
        526: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y vi, y he aquí: una nube blanca, y sobre la nube uno sentado "
                "semejante a un hijo de hombre"
            ),
            "note": "TR ἰδού",
        },
        528: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y otro ángel salió del santuario, gritando con gran voz "
                "al que estaba sentado sobre la nube:"
            ),
            "note": "TR ἐν μεγάλῃ φωνῇ",
        },
        529: {
            "trPositions": list(range(17, 30)),
            "spanish": "Envía tu hoz y siega, porque te ha llegado la hora de segar,",
            "note": "TR ἦλθέν σοι ἡ ὥρα τοῦ θερίσαι",
        },
        534: {
            "trPositions": list(range(1, 13)),
            "spanish": "y otro ángel salió del altar, teniendo autoridad sobre el fuego",
            "note": "TR ἐξῆλθεν; ἔχων (not ὁ ἔχων)",
        },
        535: {
            "trPositions": list(range(13, 24)),
            "spanish": "y gritó con gran voz al que tenía la hoz afilada, diciendo:",
            "note": "κραυγῇ μεγάλῃ",
        },
        # Revelation 15
        541: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y vi otra señal en el cielo, grande y maravillosa:",
            "note": "TR ἐν τῷ οὐρανῷ μέγα καὶ θαυμαστόν",
        },
        543: {
            "trPositions": list(range(1, 36)),
            "spanish": (
                "Y vi como un mar de vidrio mezclado con fuego, y a los que "
                "vencían de la bestia y de su imagen y de su marca, del número "
                "de su nombre, de pie sobre el mar de vidrio,"
            ),
            "note": "TR καὶ ἐκ τοῦ χαράγματος αὐτοῦ ἐκ τοῦ ἀριθμοῦ",
        },
        544: {
            "trPositions": list(range(36, 40)),
            "spanish": "teniendo arpas de Dios.",
            "note": "ἔχοντας κιθάρας",
        },
        545: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "y cantan el cántico de Moisés, el siervo de Dios, y el "
                "cántico del cordero, diciendo:"
            ),
            "note": "TR ἀρνίου lowercase; ᾠδήν",
        },
        547: {
            "trPositions": list(range(27, 37)),
            "spanish": "justos y verdaderos son tus caminos, Rey de los santos.",
            "note": "TR ὁ βασιλεὺς τῶν ἁγίων (not αἰώνων)",
        },
        548: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "¿Quién no te temerá, Señor, y glorificará tu nombre? "
                "Porque solo tú eres santo,"
            ),
            "note": "TR φοβηθῇ σε; μόνος ὅσιος (no εἶ)",
        },
        551: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y después de esto vi, y he aquí: se abrió el templo de la "
                "tienda del testimonio en el cielo."
            ),
            "note": "TR καὶ ἰδού",
        },
        552: {
            "trPositions": list(range(1, 13)),
            "spanish": "y salieron del templo los siete ángeles que tenían las siete plagas,",
            "note": "TR ἔχοντες (no οἱ ἔχοντες)",
        },
        553: {
            "trPositions": list(range(13, 25)),
            "spanish": (
                "vestidos de lino limpio y brillante, y ceñidos alrededor "
                "del pecho con cinturones de oro."
            ),
            "note": "TR λίνον καθαρὸν καὶ λαμπρόν",
        },
        554: {
            "trPositions": list(range(1, 26)),
            "spanish": (
                "y uno de los cuatro seres vivientes dio a los siete ángeles "
                "siete copas de oro llenas de la ira de Dios, que vive por "
                "los siglos de los siglos."
            ),
            "note": "TR εἰς τοὺς αἰῶνας τῶν αἰώνων",
        },
        # Revelation 16
        557: {
            "trPositions": list(range(1, 12)),
            "spanish": "Y oí una gran voz desde el templo que decía a los siete ángeles:",
            "note": "TR φωνῆς μεγάλης",
        },
        558: {
            "trPositions": list(range(12, 24)),
            "spanish": "Vayan y derramen las copas de la ira de Dios sobre la tierra.",
            "note": "TR τὰς φιάλας (no ἑπτά)",
        },
        560: {
            "trPositions": list(range(13, 34)),
            "spanish": (
                "y apareció una llaga mala y dolorosa sobre las personas "
                "que tenían la marca de la bestia y que adoraban su imagen."
            ),
            "note": "TR τῇ εἰκόνι αὐτοῦ προσκυνοῦντας",
        },
        561: {
            "trPositions": list(range(1, 12)),
            "spanish": "Y el segundo ángel derramó su copa en el mar",
            "note": "TR ὁ δεύτερος ἄγγελος",
        },
        562: {
            "trPositions": list(range(12, 25)),
            "spanish": (
                "y se convirtió en sangre como de muerto, y toda alma "
                "viviente murió en el mar."
            ),
            "note": "TR πᾶσα ψυχὴ ζῶσα ἀπέθανεν ἐν τῇ θαλάσσῃ",
        },
        563: {
            "trPositions": list(range(1, 21)),
            "spanish": (
                "Y el tercer ángel derramó su copa en los ríos y en las "
                "fuentes de las aguas, y se convirtió en sangre."
            ),
            "note": "TR ὁ τρίτος ἄγγελος; εἰς τὰς πηγάς; ἐγένετο singular",
        },
        564: {
            "trPositions": list(range(1, 8)),
            "spanish": "y oí al ángel de las aguas, diciendo:",
            "note": "λέγοντος",
        },
        565: {
            "trPositions": list(range(8, 22)),
            "spanish": (
                "Justo eres, Señor, el que es y el que era y el que ha de ser, "
                "porque has juzgado estas cosas."
            ),
            "note": "TR Κύριε εἶ; καὶ ὁ ἐσόμενος (not ὁ ὅσιος)",
        },
        566: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "porque derramaron sangre de santos y profetas, y les diste "
                "sangre para beber; porque son dignos."
            ),
            "note": "TR ἄξιοί γάρ εἰσιν",
        },
        567: {
            "trPositions": list(range(1, 8)),
            "spanish": "y oí a otro desde el altar, que decía:",
            "note": "TR ἤκουσα ἄλλου ἐκ τοῦ θυσιαστηρίου",
        },
        569: {
            "trPositions": list(range(1, 12)),
            "spanish": "Y el cuarto ángel derramó su copa sobre el sol",
            "note": "TR ὁ τέταρτος ἄγγελος",
        },
        572: {
            "trPositions": list(range(7, 20)),
            "spanish": "y blasfemaron el nombre de Dios, que tiene autoridad sobre estas plagas,",
            "note": "TR ἐξουσίαν (no τήν)",
        },
        573: {
            "trPositions": list(range(20, 26)),
            "spanish": "y no se arrepintieron para darle gloria.",
            "note": "TR καὶ οὐ μετενόησαν",
        },
        574: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y el quinto ángel derramó su copa sobre el trono de la bestia",
            "note": "TR ὁ πέμπτος ἄγγελος",
        },
        577: {
            "trPositions": list(range(16, 23)),
            "spanish": "y no se arrepintieron de sus obras.",
            "note": "TR καὶ οὐ μετενόησαν",
        },
        578: {
            "trPositions": list(range(1, 16)),
            "spanish": "Y el sexto ángel derramó su copa sobre el gran río Éufrates",
            "note": "TR ὁ ἕκτος ἄγγελος",
        },
        579: {
            "trPositions": list(range(16, 31)),
            "spanish": (
                "y su agua se secó para que se preparara el camino de los "
                "reyes que vienen de donde sale el sol."
            ),
            "note": "TR τῶν ἀπὸ ἀνατολῶν ἡλίου",
        },
        581: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "porque son espíritus de demonios que hacen señales, que "
                "salen hacia los reyes de la tierra y de toda la tierra habitada"
            ),
            "note": "TR τῆς γῆς καὶ τῆς οἰκουμένης ὅλης",
        },
        582: {
            "trPositions": list(range(18, 32)),
            "spanish": (
                "para reunirlos para la guerra de aquel gran día de Dios, "
                "el Todopoderoso."
            ),
            "note": "TR τῆς ἡμέρας ἐκείνης τῆς μεγάλης",
        },
        583: {
            "trPositions": list(range(1, 5)),
            "spanish": "He aquí, vengo como ladrón.",
            "note": "TR Ἰδού",
        },
        587: {
            "trPositions": list(range(1, 26)),
            "spanish": (
                "Y el séptimo ángel derramó su copa en el aire, y salió una "
                "gran voz desde el templo del cielo, desde el trono, que decía: "
                "¡Está hecho!"
            ),
            "note": "TR ὁ ἕβδομος ἄγγελος; τοῦ ναοῦ τοῦ οὐρανοῦ",
        },
        588: {
            "trPositions": list(range(1, 12)),
            "spanish": "y hubo voces, truenos y relámpagos, y un gran terremoto",
            "note": "TR φωναὶ καὶ βρονταὶ καὶ ἀστραπαί",
        },
        589: {
            "trPositions": list(range(12, 27)),
            "spanish": (
                "como no había habido desde que los hombres existieron sobre "
                "la tierra: un terremoto tan grande, tan fuerte."
            ),
            "note": "TR ἀφ’ οὗ οἱ ἄνθρωποι ἐγένοντο",
        },
        592: {
            "trPositions": list(range(16, 35)),
            "spanish": (
                "y Babilonia la grande fue recordada delante de Dios, para "
                "darle la copa del vino de la furia de su ira."
            ),
            "note": "TR τοῦ οἴνου τοῦ θυμοῦ τῆς ὀργῆς αὐτοῦ",
        },
        # Revelation 17
        598: {
            "trPositions": list(range(13, 19)),
            "spanish": "y habló conmigo, diciéndome:",
            "note": "TR λέγων μοι",
        },
        599: {
            "trPositions": list(range(19, 35)),
            "spanish": (
                "Ven, te mostraré el juicio de la gran prostituta que está "
                "sentada sobre las muchas aguas."
            ),
            "note": "TR ἐπὶ τῶν ὑδάτων τῶν πολλῶν",
        },
        600: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "con la cual los reyes de la tierra se prostituyeron, y se "
                "embriagaron del vino de su prostitución los que habitan la tierra."
            ),
            "note": "TR ἐμεθύσθησαν ἐκ τοῦ οἴνου … οἱ κατοικοῦντες τὴν γῆν",
        },
        604: {
            "trPositions": list(range(1, 9)),
            "spanish": "y la mujer estaba vestida de púrpura y escarlata",
            "note": "SCV καὶ ἡ γυνὴ ἦν περιβεβλημένη",
        },
        605: {
            "trPositions": list(range(9, 17)),
            "spanish": "y adornada con oro, piedra preciosa y perlas,",
            "note": "κεχρυσωμένη χρυσῷ",
        },
        606: {
            "trPositions": list(range(17, 30)),
            "spanish": (
                "teniendo una copa de oro en su mano llena de abominaciones "
                "y de la impureza de su prostitución."
            ),
            "note": "TR ποτήριον; ἀκαθάρτητος singular",
        },
        607: {
            "trPositions": list(range(1, 9)),
            "spanish": "y en su frente un nombre escrito: Misterio,",
            "note": "Μυστήριον as the inscribed name",
        },
        610: {
            "trPositions": list(range(18, 24)),
            "spanish": "y me asombré al verla, asombro grande.",
            "note": "TR ἐθαύμασα ἰδὼν αὐτὴν θαῦμα μέγα",
        },
        612: {
            "trPositions": list(range(9, 22)),
            "spanish": "Yo te diré el misterio de la mujer y de la bestia que la lleva,",
            "note": "TR ἐγὼ σοί ἐρῶ",
        },
        616: {
            "trPositions": list(range(19, 39)),
            "spanish": (
                "y los que habitan sobre la tierra, cuyos nombres no están "
                "escritos sobre el libro de la vida desde la fundación del mundo, "
                "se asombrarán"
            ),
            "note": "TR τὰ ὀνόματα ἐπὶ τὸ βιβλίον",
        },
        617: {
            "trPositions": list(range(39, 50)),
            "spanish": "al ver a la bestia, que era y no es, aunque es.",
            "note": "TR ὅ τι ἦν καὶ οὐκ ἔστιν καίπερ ἔστιν",
        },
        619: {
            "trPositions": list(range(7, 19)),
            "spanish": (
                "Las siete cabezas son siete montes, donde la mujer está "
                "sentada sobre ellos."
            ),
            "note": "TR ὄρη εἰσίν ἑπτά",
        },
        620: {
            "trPositions": [],
            "spanish": "",
            "note": "TR καὶ βασιλεῖς ἑπτά εἰσιν belongs to 17:10",
        },
        621: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Y son siete reyes: los cinco cayeron, uno es, el otro "
                "todavía no ha venido,"
            ),
            "note": "TR καὶ βασιλεῖς ἑπτά εἰσιν οἱ πέντε ἔπεσαν",
        },
        624: {
            "trPositions": list(range(9, 18)),
            "spanish": "también él es un octavo y es de los siete",
            "note": "TR καὶ αὐτός ὄγδοός ἐστιν",
        },
        628: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Estos tienen un mismo propósito y dan su poder y su "
                "autoridad a la bestia."
            ),
            "note": "TR τὴν ἐξουσίαν ἑαυτῶν",
        },
        629: {
            "trPositions": list(range(1, 11)),
            "spanish": "Estos pelearán contra el cordero, y el cordero los vencerá,",
            "note": "TR ἀρνίον lowercase",
        },
        631: {
            "trPositions": list(range(1, 4)),
            "spanish": "Y me dice:",
            "note": "λέγει μοι",
        },
        634: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y los diez cuernos que viste sobre la bestia,",
            "note": "TR ἐπὶ τὸ θηρίον (not καὶ τὸ θηρίον)",
        },
        638: {
            "trPositions": list(range(13, 24)),
            "spanish": "y hacer un mismo propósito y dar su reino a la bestia,",
            "note": "TR τὴν βασιλείαν αὐτῶν",
        },
        # Revelation 18
        641: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y después de esto vi a otro ángel que bajaba del cielo",
            "note": "TR Καὶ μετὰ ταῦτα",
        },
        643: {
            "trPositions": list(range(1, 8)),
            "spanish": "y gritó con fuerza, con gran voz, diciendo:",
            "note": "TR ἐν ἰσχύϊ φωνῇ μεγάλῃ",
        },
        644: {
            "trPositions": list(range(8, 29)),
            "spanish": (
                "¡Cayó, cayó Babilonia la grande! Y se ha convertido en "
                "morada de demonios, y prisión de todo espíritu impuro, y "
                "prisión de toda ave impura y odiada."
            ),
            "note": "TR no φυλακὴ παντὸς θηρίου",
        },
        645: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "porque del vino de la furia de su prostitución han bebido "
                "todas las naciones,"
            ),
            "note": "TR πέπωκεν (not πέπτωκαν)",
        },
        648: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y oí otra voz del cielo, que decía:",
            "note": "λέγουσαν",
        },
        649: {
            "trPositions": list(range(9, 21)),
            "spanish": "Salgan de ella, pueblo mío, para que no participen de sus pecados",
            "note": "TR Ἐξέλθετε ἐξ αὐτῆς",
        },
        650: {
            "trPositions": list(range(21, 29)),
            "spanish": "y para que no reciban de sus plagas.",
            "note": "TR καὶ ἵνα μὴ λάβητε ἐκ τῶν πληγῶν",
        },
        652: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Devuélvanle como ella también les devolvió, y denle el "
                "doble según sus obras"
            ),
            "note": "TR ἀπέδωκεν ὑμῖν",
        },
        655: {
            "trPositions": list(range(12, 20)),
            "spanish": "porque dice en su corazón: Estoy sentada como reina",
            "note": "TR no ὅτι before Κάθημαι",
        },
        659: {
            "trPositions": list(range(19, 27)),
            "spanish": "porque fuerte es el Señor Dios que la juzga.",
            "note": "TR ὁ κρίνων (present)",
        },
        660: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y llorarán por ella y se golpearán el pecho sobre ella los "
                "reyes de la tierra que se prostituyeron con ella y vivieron en lujo,"
            ),
            "note": "TR κλαύσονται αὐτήν; kings after the verbs",
        },
        662: {
            "trPositions": list(range(1, 11)),
            "spanish": "de pie a distancia por temor a su tormento, diciendo:",
            "note": "λέγοντες",
        },
        664: {
            "trPositions": list(range(22, 30)),
            "spanish": "porque en una sola hora llegó tu juicio.",
            "note": "TR ὅτι ἐν μιᾷ ὥρᾳ",
        },
        667: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "carga de oro y de plata y de piedra preciosa y de perla y "
                "de lino fino y de púrpura y de seda y de escarlata"
            ),
            "note": "TR μαργαρίτου singular",
        },
        669: {
            "trPositions": list(range(1, 21)),
            "spanish": (
                "y canela, inciensos, mirra y olíbano, y vino, aceite, flor "
                "de harina, trigo, ganado y ovejas"
            ),
            "note": "TR no ἄμωμον",
        },
        671: {
            "trPositions": list(range(1, 12)),
            "spanish": "y el fruto del deseo de tu alma se fue de ti,",
            "note": "TR τῆς ψυχῆς σου",
        },
        673: {
            "trPositions": list(range(22, 28)),
            "spanish": "y nunca más las hallarás.",
            "note": "TR οὐκέτι οὐ μὴ εὑρήσῃς αὐτά",
        },
        675: {
            "trPositions": list(range(1, 3)),
            "spanish": "y diciendo:",
            "note": "TR καὶ λέγοντες",
        },
        676: {
            "trPositions": list(range(3, 25)),
            "spanish": (
                "¡Ay, ay, gran ciudad, vestida de lino fino, púrpura y "
                "escarlata, y adornada con oro, piedra preciosa y perlas!"
            ),
            "note": "TR κεχρυσωμένη ἐν χρυσῷ",
        },
        678: {
            "trPositions": list(range(8, 18)),
            "spanish": "Y todo piloto, y toda la compañía sobre los barcos,",
            "note": "TR πᾶς ἐπὶ τῶν πλοίων ὁ ὅμιλος",
        },
        681: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "y echaron polvo sobre sus cabezas y gritaban, llorando y "
                "haciendo duelo, diciendo:"
            ),
            "note": "ἔκραζον imperfect",
        },
        682: {
            "trPositions": list(range(14, 34)),
            "spanish": (
                "¡Ay, ay, gran ciudad, en la cual se enriquecieron todos "
                "los que tienen barcos en el mar de su riqueza!"
            ),
            "note": "TR ἔχοντες πλοῖα; ἐκ τῆς τιμιότητος",
        },
        684: {
            "trPositions": list(range(1, 12)),
            "spanish": "Alégrate por ella, cielo, y los santos apóstoles y los profetas,",
            "note": "TR οἱ ἅγιοι ἀπόστολοι (not three groups)",
        },
        687: {
            "trPositions": list(range(10, 16)),
            "spanish": "y la arrojó al mar, diciendo:",
            "note": "λέγων",
        },
        688: {
            "trPositions": list(range(16, 28)),
            "spanish": (
                "Así, con violencia, será arrojada Babilonia, la gran ciudad, "
                "y nunca más será hallada."
            ),
            "note": "TR οὕτως ὁρμήματι βληθήσεται",
        },
        695: {
            "trPositions": list(range(30, 39)),
            "spanish": "porque en tu hechicería fueron engañadas todas las naciones.",
            "note": "TR ἐν τῇ φαρμακείᾳ σου",
        },
        # Revelation 19
        697: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y después de estas cosas oí una gran voz de una multitud "
                "numerosa en el cielo, diciendo: ¡Aleluya!"
            ),
            "note": "TR Καὶ; no ὡς; φωνὴν … μεγάλην",
        },
        698: {
            "trPositions": list(range(14, 29)),
            "spanish": (
                "La salvación y la gloria y el honor y el poder al Señor "
                "nuestro Dios."
            ),
            "note": "TR καὶ ἡ τιμή; Κυρίῳ τῷ Θεῷ ἡμῶν",
        },
        701: {
            "trPositions": list(range(22, 33)),
            "spanish": "y vengó la sangre de sus siervos de la mano de ella.",
            "note": "TR ἐκ τῆς χειρός",
        },
        702: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y por segunda vez dijeron: ¡Aleluya! Y el humo de ella "
                "sube por los siglos de los siglos."
            ),
            "note": "drop guillemets",
        },
        703: {
            "trPositions": list(range(1, 13)),
            "spanish": "Y los veinticuatro ancianos y los cuatro seres vivientes cayeron",
            "note": "TR εἴκοσι καὶ τέσσαρες",
        },
        704: {
            "trPositions": list(range(13, 25)),
            "spanish": "y adoraron a Dios, sentado en el trono, diciendo: Amén. ¡Aleluya!",
            "note": "drop guillemets",
        },
        706: {
            "trPositions": list(range(8, 16)),
            "spanish": "Alaben a nuestro Dios todos sus siervos,",
            "note": "drop guillemets",
        },
        707: {
            "trPositions": list(range(16, 26)),
            "spanish": "y los que le temen, y los pequeños y los grandes.",
            "note": "TR καὶ οἱ φοβούμενοι … καὶ οἱ μικροί",
        },
        709: {
            "trPositions": list(range(18, 26)),
            "spanish": "¡Aleluya!, porque el Señor Dios, el Todopoderoso, ha reinado.",
            "note": "drop guillemets",
        },
        711: {
            "trPositions": list(range(9, 21)),
            "spanish": "porque llegó la boda del cordero, y su mujer se preparó.",
            "note": "TR ἀρνίου; ἡ γυνὴ αὐτοῦ",
        },
        712: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y le fue dado vestirse de lino fino, limpio y brillante; "
                "porque el lino fino es los actos justos de los santos."
            ),
            "note": "TR καθαρὸν καὶ λαμπρόν; δικαιώματα ἐστιν",
        },
        713: {
            "trPositions": list(range(1, 5)),
            "spanish": "Y me dice: Escribe:",
            "note": "drop guillemets",
        },
        714: {
            "trPositions": list(range(5, 18)),
            "spanish": (
                "Dichosos los llamados a la cena de la boda del cordero. "
                "Y me dice:"
            ),
            "note": "TR ἀρνίου",
        },
        715: {
            "trPositions": list(range(18, 25)),
            "spanish": "Estas son las palabras verdaderas de Dios.",
            "note": "TR ἀληθινοί εἰσιν τοῦ Θεοῦ",
        },
        716: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y caí delante de sus pies para adorarlo, y me dice: ¡Mira, no!",
            "note": "TR καὶ λέγει μοι· Ὅρα μή",
        },
        717: {
            "trPositions": list(range(14, 30)),
            "spanish": (
                "Soy consiervo tuyo y de tus hermanos que tienen el "
                "testimonio de Jesús. Adora a Dios,"
            ),
            "note": "TR τὴν μαρτυρίαν τοῦ Ἰησοῦ",
        },
        718: {
            "trPositions": list(range(30, 40)),
            "spanish": "porque el testimonio de Jesús es el espíritu de la profecía.",
            "note": "TR ἡ μαρτυρία τοῦ Ἰησοῦ",
        },
        719: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y vi el cielo abierto, y he aquí: un caballo blanco.",
            "note": "TR ἰδού",
        },
        720: {
            "trPositions": list(range(10, 19)),
            "spanish": "Y el que está sentado sobre él, llamado Fiel y Verdadero,",
            "note": "TR καλούμενος πιστὸς καὶ ἀληθινός",
        },
        721: {
            "trPositions": list(range(19, 25)),
            "spanish": "y con justicia juzga y combate.",
            "note": "TR ἐν δικαιοσύνῃ κρίνει καὶ πολεμεῖ",
        },
        722: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "Y sus ojos como llama de fuego, y sobre su cabeza hay "
                "muchas diademas;"
            ),
            "note": "TR ὡς φλὸξ πυρός",
        },
        725: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y los ejércitos que están en el cielo lo seguían sobre "
                "caballos blancos, vestidos de lino fino blanco y limpio."
            ),
            "note": "TR λευκὸν καὶ καθαρόν",
        },
        726: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y de su boca sale una espada afilada,",
            "note": "TR καί",
        },
        728: {
            "trPositions": list(range(22, 38)),
            "spanish": (
                "Y él pisa el lagar del vino de la furia y de la ira de "
                "Dios, el Todopoderoso."
            ),
            "note": "TR τοῦ θυμοῦ καὶ τῆς ὀργῆς",
        },
        730: {
            "trPositions": list(range(13, 18)),
            "spanish": "Rey de reyes y Señor de señores.",
            "note": "drop guillemets",
        },
        733: {
            "trPositions": list(range(21, 30)),
            "spanish": "Vengan y reúnanse para la cena del gran Dios,",
            "note": "TR Δεῦτε καὶ συνάγεσθε εἰς τὸ δεῖπνον τοῦ μεγάλου Θεοῦ",
        },
        735: {
            "trPositions": list(range(19, 30)),
            "spanish": "y carne de todos, libres y siervos, pequeños y grandes.",
            "note": "drop guillemets",
        },
        736: {
            "trPositions": list(range(1, 28)),
            "spanish": (
                "Y vi a la bestia, a los reyes de la tierra y a sus ejércitos "
                "reunidos para hacer guerra contra el que está sentado sobre "
                "el caballo y contra su ejército."
            ),
            "note": "TR ποιῆσαι πόλεμον (no τόν)",
        },
        737: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Y la bestia fue capturada, y con este el falso profeta que "
                "había hecho las señales delante de ella,"
            ),
            "note": "TR μετὰ τούτου",
        },
        739: {
            "trPositions": list(range(31, 45)),
            "spanish": (
                "Los dos fueron arrojados vivos al lago de fuego que arde "
                "en el azufre."
            ),
            "note": "TR καιομένην ἐν τῷ θείῳ",
        },
        # Revelation 20
        742: {
            "trPositions": list(range(1, 20)),
            "spanish": (
                "Y vi un ángel que bajaba del cielo, que tenía la llave del "
                "abismo y una gran cadena sobre su mano."
            ),
            "note": "TR ἄγγελον (no ἕνα)",
        },
        744: {
            "trPositions": list(range(9, 19)),
            "spanish": "que es el Diablo y Satanás, y lo ató por mil años.",
            "note": "TR Σατανᾶς (no ὁ)",
        },
        745: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y lo arrojó al abismo, y lo cerró, y lo selló sobre él,",
            "note": "TR ἔκλεισεν αὐτόν",
        },
        746: {
            "trPositions": list(range(14, 25)),
            "spanish": (
                "para que no engañara más a las naciones, hasta que se "
                "cumplieran los mil años."
            ),
            "note": "TR πλανήσῃ τὰ ἔθνη ἔτι",
        },
        747: {
            "trPositions": list(range(25, 33)),
            "spanish": "Y después de estas cosas debe ser soltado por un poco de tiempo.",
            "note": "TR καὶ μετὰ ταῦτα δεῖ αὐτὸν λυθῆναι",
        },
        749: {
            "trPositions": list(range(12, 27)),
            "spanish": (
                "Y las almas de los decapitados por el testimonio de Jesús "
                "y por la palabra de Dios,"
            ),
            "note": "καὶ τὰς ψυχάς",
        },
        750: {
            "trPositions": list(range(27, 51)),
            "spanish": (
                "y quienes no adoraron a la bestia ni a su imagen, y no "
                "recibieron la marca sobre su frente ni sobre su mano."
            ),
            "note": "TR ἐπὶ τὸ μέτωπον αὐτῶν",
        },
        751: {
            "trPositions": list(range(51, 60)),
            "spanish": "Y vivieron y reinaron con Cristo los mil años.",
            "note": "TR ἔζησαν; μετὰ Χριστοῦ τὰ χίλια ἔτη",
        },
        752: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Pero los demás de los muertos no volvieron a vivir hasta "
                "que se cumplieran los mil años. Esta es la primera resurrección."
            ),
            "note": "TR οἱ δὲ λοιποί; ἀνέζησαν",
        },
        754: {
            "trPositions": list(range(12, 21)),
            "spanish": "sobre estos la muerte segunda no tiene autoridad,",
            "note": "TR ὁ θάνατος ὁ δεύτερος",
        },
        757: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y cuando se cumplan los mil años, Satanás será soltado de su prisión.",
            "note": "TR Καὶ ὅταν",
        },
        758: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "Y saldrá a engañar a las naciones que están en las cuatro "
                "esquinas de la tierra,"
            ),
            "note": "καὶ ἐξελεύσεται",
        },
        759: {
            "trPositions": list(range(13, 22)),
            "spanish": "a Gog y a Magog, para reunirlos para guerra;",
            "note": "TR τὸν Γὼγ καὶ τὸν Μαγώγ; εἰς πόλεμον",
        },
        760: {
            "trPositions": list(range(22, 30)),
            "spanish": "cuyo número es como la arena del mar.",
            "note": "TR ὧν ὁ ἀριθμός (no αὐτῶν)",
        },
        761: {
            "trPositions": list(range(1, 19)),
            "spanish": (
                "Y subieron sobre la extensión de la tierra y rodearon el "
                "campamento de los santos y la ciudad amada."
            ),
            "note": "TR καί",
        },
        762: {
            "trPositions": list(range(19, 31)),
            "spanish": "Y bajó fuego de Dios desde el cielo y los devoró.",
            "note": "TR πῦρ ἀπὸ τοῦ Θεοῦ ἐκ τοῦ οὐρανοῦ",
        },
        764: {
            "trPositions": list(range(15, 31)),
            "spanish": (
                "donde están la bestia y el falso profeta; y serán "
                "atormentados día y noche por los siglos de los siglos."
            ),
            "note": "TR ὅπου τὸ θηρίον (no ὅπου καί)",
        },
        765: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y vi un trono blanco grande y al que está sentado sobre él.",
            "note": "TR θρόνον λευκὸν μέγαν",
        },
        766: {
            "trPositions": list(range(11, 20)),
            "spanish": "De delante de su rostro huyeron la tierra y el cielo,",
            "note": "TR οὗ ἀπὸ προσώπου (no τοῦ)",
        },
        768: {
            "trPositions": list(range(1, 8)),
            "spanish": "Y vi a los muertos, pequeños y grandes,",
            "note": "TR μικρούς καὶ μεγάλους",
        },
        769: {
            "trPositions": list(range(8, 15)),
            "spanish": "de pie delante de Dios, y se abrieron libros.",
            "note": "TR ἐνώπιον τοῦ Θεοῦ (not θρόνου)",
        },
        770: {
            "trPositions": list(range(15, 23)),
            "spanish": "Y se abrió otro libro, que es el de la vida.",
            "note": "TR βιβλίον ἄλλο ἠνεῴχθη",
        },
        772: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y el mar entregó a los muertos que había en él,",
            "note": "TR τοὺς ἐν αὐτῇ νεκρούς",
        },
        773: {
            "trPositions": list(range(9, 20)),
            "spanish": "y la muerte y el Hades entregaron a los muertos que había en ellos;",
            "note": "TR τοὺς ἐν αὐτοῖς νεκρούς",
        },
        776: {
            "trPositions": list(range(13, 18)),
            "spanish": "Esta es la segunda muerte.",
            "note": "TR no ἡ λίμνη τοῦ πυρός after δεύτερος θάνατος",
        },
        782: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y yo, Juan, vi la ciudad santa, la nueva Jerusalén, que "
                "bajaba de parte de Dios desde el cielo,"
            ),
            "note": "TR ἐγὼ Ἰωάννης εἶδον; ἀπὸ τοῦ Θεοῦ ἐκ τοῦ οὐρανοῦ",
        },
        784: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y oí una gran voz desde el cielo, que decía:",
            "note": "TR ἐκ τοῦ οὐρανοῦ (not θρόνου)",
        },
        785: {
            "trPositions": list(range(9, 17)),
            "spanish": "He aquí, la tienda de Dios está con los hombres,",
            "note": "Ἰδοὺ; τῶν ἀνθρώπων",
        },
        786: {
            "trPositions": list(range(17, 26)),
            "spanish": "y morará con ellos, y ellos serán sus pueblos,",
            "note": "σκηνώσει; λαοὶ plural",
        },
        787: {
            "trPositions": list(range(26, 35)),
            "spanish": "y Dios mismo estará con ellos, Dios de ellos.",
            "note": "TR ἔσται μετ’ αὐτῶν Θεός αὐτῶν",
        },
        788: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y Dios enjugará toda lágrima de los ojos de ellos,",
            "note": "TR ὁ Θεὸς; ἀπὸ τῶν ὀφθαλμῶν",
        },
        790: {
            "trPositions": list(range(17, 30)),
            "spanish": (
                "ni duelo, ni grito, ni dolor existirá ya más, porque las "
                "primeras cosas pasaron."
            ),
            "note": "TR ὅτι τὰ πρῶτα ἀπῆλθον",
        },
        792: {
            "trPositions": list(range(8, 15)),
            "spanish": "He aquí, hago nuevas todas las cosas. Y me dice:",
            "note": "TR καινὰ πάντα ποιῶ; λέγει μοι",
        },
        793: {
            "trPositions": list(range(15, 24)),
            "spanish": "Escribe, porque estas palabras son verdaderas y fieles.",
            "note": "TR ἀληθινοί καὶ πιστοί",
        },
        794: {
            "trPositions": list(range(1, 5)),
            "spanish": "Y me dijo: Ha sucedido.",
            "note": "TR γέγονεν singular",
        },
        795: {
            "trPositions": list(range(5, 17)),
            "spanish": "Yo soy el Alfa y la Omega, el principio y el fin.",
            "note": "TR ἐγώ εἰμι",
        },
        796: {
            "trPositions": list(range(17, 29)),
            "spanish": (
                "Yo daré al que tiene sed de la fuente del agua de la vida, "
                "gratuitamente."
            ),
            "note": "δωρεάν final",
        },
        797: {
            "trPositions": list(range(1, 15)),
            "spanish": (
                "El que vence heredará todas las cosas, y yo seré su Dios "
                "y él será mi hijo."
            ),
            "note": "TR πάντα (not ταῦτα); ὁ υἱός",
        },
        798: {
            "trPositions": list(range(1, 30)),
            "spanish": (
                "Pero a los cobardes e incrédulos y abominables y asesinos "
                "y sexualmente inmorales y hechiceros e idólatras y todos "
                "los mentirosos, su parte estará en el lago que arde con "
                "fuego y azufre,"
            ),
            "note": "TR δειλοῖς δὲ (no τοῖς); φαρμακεῦσιν",
        },
        799: {
            "trPositions": list(range(30, 34)),
            "spanish": "que es segunda muerte.",
            "note": "TR ὅ ἐστιν δεύτερος θάνατος (no ὁ θάνατος ὁ)",
        },
        800: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y vino a mí uno de los siete ángeles que tenían las siete copas",
            "note": "TR ἦλθεν πρὸς με εἷς (no ἐκ)",
        },
        802: {
            "trPositions": list(range(26, 35)),
            "spanish": "Ven, te mostraré a la novia del cordero, la esposa.",
            "note": "TR τὴν νύμφην τοῦ ἀρνίου τὴν γυναῖκα",
        },
        804: {
            "trPositions": list(range(11, 28)),
            "spanish": (
                "y me mostró la ciudad grande, la santa Jerusalén, que "
                "bajaba del cielo de parte de Dios."
            ),
            "note": "TR τὴν πόλιν τὴν μεγάλην τὴν ἁγίαν Ἰερουσαλήμ",
        },
        805: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Tenía la gloria de Dios, y su resplandor era semejante a "
                "una piedra muy preciosa, como piedra de jaspe cristalino."
            ),
            "note": "TR καὶ ὁ φωστήρ",
        },
        806: {
            "trPositions": list(range(1, 10)),
            "spanish": "Tenía también un muro grande y alto, con doce puertas,",
            "note": "TR ἔχουσαν τε",
        },
        807: {
            "trPositions": list(range(10, 27)),
            "spanish": (
                "y sobre las puertas doce ángeles y nombres escritos, que "
                "son los de las doce tribus de los hijos de Israel."
            ),
            "note": "TR τῶν υἱῶν Ἰσραήλ",
        },
        808: {
            "trPositions": list(range(1, 9)),
            "spanish": "Al este, tres puertas; al norte, tres puertas;",
            "note": "TR no καὶ before βορρᾶ",
        },
        809: {
            "trPositions": list(range(9, 18)),
            "spanish": "al sur, tres puertas; y al oeste, tres puertas.",
            "note": "TR no καὶ before νότου; καὶ ἀπὸ δυσμῶν",
        },
        811: {
            "trPositions": list(range(9, 18)),
            "spanish": "y en ellos nombres de los doce apóstoles del cordero.",
            "note": "TR ἐν αὐτοῖς ὀνόματα (no δώδεκα ὀνόματα)",
        },
        812: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y el que hablaba conmigo tenía una caña de oro,",
            "note": "TR κάλαμον χρυσοῦν (no μέτρον)",
        },
        813: {
            "trPositions": list(range(9, 21)),
            "spanish": "para medir la ciudad y sus puertas y su muro.",
            "note": "ἵνα μετρήσῃ",
        },
        814: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Y la ciudad está puesta en cuadrado, y su largo es tanto "
                "como también el ancho."
            ),
            "note": "TR τοσοῦτόν ἐστιν ὅσον καὶ τὸ πλάτος",
        },
        815: {
            "trPositions": list(range(16, 26)),
            "spanish": "Y midió la ciudad con la caña: doce mil estadios.",
            "note": "τῷ καλάμῳ",
        },
        818: {
            "trPositions": list(range(1, 17)),
            "spanish": (
                "Y la construcción de su muro era de jaspe, y la ciudad "
                "era oro puro, semejante a vidrio puro."
            ),
            "note": "TR καὶ ἦν ἡ ἐνδόμησις",
        },
        819: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Y los cimientos del muro de la ciudad estaban adornados "
                "con toda piedra preciosa:"
            ),
            "note": "TR καὶ οἱ θεμέλιοι",
        },
        827: {
            "trPositions": list(range(1, 10)),
            "spanish": "Y no vi templo en ella, porque el Señor",
            "note": "καὶ ναὸν οὐκ εἶδον",
        },
        828: {
            "trPositions": list(range(10, 20)),
            "spanish": "Dios, el Todopoderoso, es su templo, y el cordero.",
            "note": "καὶ τὸ ἀρνίον",
        },
        830: {
            "trPositions": list(range(12, 23)),
            "spanish": (
                "para que brillen en ella, porque la gloria de Dios la iluminó,"
            ),
            "note": "TR ἵνα φαίνωσιν ἐν αὐτῇ",
        },
        831: {
            "trPositions": list(range(23, 29)),
            "spanish": "y su lámpara es el cordero.",
            "note": "τὸ ἀρνίον",
        },
        832: {
            "trPositions": list(range(1, 11)),
            "spanish": "Y las naciones de los salvados caminarán en su luz,",
            "note": "TR τὰ ἔθνη τῶν σωζομένων ἐν τῷ φωτί αὐτῆς περιπατήσουσιν",
        },
        833: {
            "trPositions": list(range(11, 25)),
            "spanish": (
                "y los reyes de la tierra llevan a ella la gloria y la "
                "honra de ellos."
            ),
            "note": "TR τὴν δόξαν καὶ τὴν τιμὴν αὐτῶν",
        },
        834: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y sus puertas nunca se cerrarán de día, porque allí no habrá noche.",
            "note": "καὶ οἱ πυλῶνες",
        },
        835: {
            "trPositions": list(range(1, 12)),
            "spanish": "Y llevarán a ella la gloria y la honra de las naciones.",
            "note": "καὶ οἴσουσιν",
        },
        836: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y de ningún modo entrará en ella nada que contamine ni "
                "que hace abominación y mentira,"
            ),
            "note": "TR πᾶν κοινοῦν καὶ ποιοῦν",
        },
        837: {
            "trPositions": list(range(14, 25)),
            "spanish": "sino solo los escritos en el libro de la vida del cordero.",
            "note": "τοῦ ἀρνίου",
        },
        838: {
            "trPositions": list(range(1, 11)),
            "spanish": (
                "Y me mostró un río puro de agua de vida, brillante como cristal,"
            ),
            "note": "TR καθαρὸν ποταμόν",
        },
        839: {
            "trPositions": list(range(11, 20)),
            "spanish": "que sale del trono de Dios y del cordero.",
            "note": "τοῦ ἀρνίου",
        },
        841: {
            "trPositions": list(range(6, 17)),
            "spanish": (
                "y a uno y otro lado del río está el árbol de vida, que "
                "produce doce frutos,"
            ),
            "note": "TR ἐντεῦθεν καὶ ἐντεῦθεν",
        },
        842: {
            "trPositions": list(range(17, 34)),
            "spanish": (
                "dando cada uno su fruto cada mes; y las hojas del árbol "
                "son para sanidad de las naciones."
            ),
            "note": "TR κατὰ μῆνα ἕνα ἕκαστον",
        },
        843: {
            "trPositions": list(range(1, 7)),
            "spanish": "Y ya no habrá ninguna maldición.",
            "note": "TR κατανάθεμα",
        },
        844: {
            "trPositions": list(range(7, 18)),
            "spanish": "Y el trono de Dios y del cordero estará en ella,",
            "note": "τοῦ ἀρνίου",
        },
        846: {
            "trPositions": list(range(1, 14)),
            "spanish": "Y verán su rostro, y su nombre estará sobre las frentes de ellos.",
            "note": "καὶ ὄψονται",
        },
        847: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "Y no habrá noche allí, y no tienen necesidad de lámpara "
                "ni de luz de sol,"
            ),
            "note": "TR ἐκεῖ; χρείαν οὐκ ἔχουσιν λύχνου καὶ φωτὸς ἡλίου",
        },
        848: {
            "trPositions": list(range(14, 27)),
            "spanish": (
                "porque el Señor Dios los ilumina, y reinarán por los "
                "siglos de los siglos."
            ),
            "note": "TR φωτίζει (present; no ἐπ’)",
        },
        850: {
            "trPositions": list(range(4, 12)),
            "spanish": "Estas palabras son fieles y verdaderas; y el Señor,",
            "note": "drop guillemets",
        },
        851: {
            "trPositions": list(range(12, 30)),
            "spanish": (
                "el Dios de los santos profetas, envió a su ángel para "
                "mostrar a sus siervos las cosas que deben suceder pronto."
            ),
            "note": "TR τῶν ἁγίων προφητῶν (not πνευμάτων)",
        },
        852: {
            "trPositions": list(range(1, 14)),
            "spanish": (
                "He aquí, vengo pronto. Dichoso el que guarda las palabras "
                "de la profecía de este libro."
            ),
            "note": "TR ἰδού (no καί)",
        },
        853: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y yo, Juan, el que ve estas cosas y oye.",
            "note": "TR Καὶ ἐγὼ Ἰωάννης ὁ βλέπων ταῦτα καὶ ἀκούων",
        },
        854: {
            "trPositions": list(range(9, 25)),
            "spanish": (
                "Y cuando oí y vi, caí para adorar delante de los pies "
                "del ángel que me mostraba estas cosas."
            ),
            "note": "καὶ ὅτε ἤκουσα καὶ ἔβλεψα",
        },
        855: {
            "trPositions": list(range(1, 6)),
            "spanish": "Y me dice: ¡Mira, no!",
            "note": "Ὅρα μή; drop guillemets",
        },
        856: {
            "trPositions": list(range(6, 27)),
            "spanish": (
                "Porque soy consiervo tuyo y de tus hermanos los profetas, "
                "y de los que guardan las palabras de este libro. Adora a Dios."
            ),
            "note": "TR σύνδουλός σού γάρ εἰμι",
        },
        858: {
            "trPositions": list(range(4, 13)),
            "spanish": "No selles las palabras de la profecía de este libro,",
            "note": "drop guillemets",
        },
        859: {
            "trPositions": list(range(13, 18)),
            "spanish": "porque el tiempo está cerca.",
            "note": "TR ὅτι ὁ καιρός",
        },
        860: {
            "trPositions": list(range(1, 10)),
            "spanish": (
                "El que hace injusticia, haga injusticia todavía; y el que "
                "está sucio, ensúciese todavía;"
            ),
            "note": "TR ὁ ῥυπῶν ῥυπωσάτω ἔτι",
        },
        861: {
            "trPositions": list(range(10, 20)),
            "spanish": (
                "y el justo sea justificado todavía; y el santo sea "
                "santificado todavía."
            ),
            "note": "TR δικαιωθήτω (not δικαιοσύνην ποιησάτω)",
        },
        862: {
            "trPositions": list(range(1, 18)),
            "spanish": (
                "Y he aquí, vengo pronto, y mi recompensa está conmigo "
                "para dar a cada uno según sea su obra."
            ),
            "note": "TR καὶ ἰδού; τὸ ἔργον αὐτοῦ ἔσται",
        },
        863: {
            "trPositions": list(range(1, 16)),
            "spanish": (
                "Yo soy el Alfa y la Omega, principio y fin, el primero y "
                "el último."
            ),
            "note": "TR ἐγὼ εἰμί; ἀρχὴ καὶ τέλος ὁ πρῶτος καὶ ὁ ἔσχατος",
        },
        864: {
            "trPositions": list(range(1, 24)),
            "spanish": (
                "Dichosos los que hacen sus mandamientos, para que su "
                "autoridad sea sobre el árbol de la vida y entren por las "
                "puertas a la ciudad."
            ),
            "note": "TR οἱ ποιοῦντες τὰς ἐντολὰς αὐτοῦ",
        },
        865: {
            "trPositions": list(range(1, 24)),
            "spanish": (
                "Pero fuera están los perros y los hechiceros y los "
                "sexualmente inmorales y los asesinos y los idólatras y "
                "todo el que ama y practica mentira."
            ),
            "note": "TR ἔξω δέ; ὁ φιλῶν",
        },
        867: {
            "trPositions": list(range(13, 22)),
            "spanish": "Yo soy la raíz y el linaje de David,",
            "note": "TR τοῦ Δαβίδ",
        },
        868: {
            "trPositions": list(range(22, 28)),
            "spanish": "la estrella brillante y matutina.",
            "note": "TR ὁ ἀστὴρ ὁ λαμπρὸς καὶ ὀρθρινός",
        },
        869: {
            "trPositions": list(range(1, 9)),
            "spanish": "Y el Espíritu y la novia dicen: Ven.",
            "note": "TR Ἐλθέ",
        },
        870: {
            "trPositions": list(range(9, 14)),
            "spanish": "Y el que oye diga: Ven.",
            "note": "TR Ἐλθέ",
        },
        871: {
            "trPositions": list(range(14, 26)),
            "spanish": (
                "Y el que tiene sed, venga; y el que quiere, tome el agua "
                "de vida, gratuitamente."
            ),
            "note": "TR καὶ ὁ θέλων λαμβανέτω τὸ ὕδωρ ζωῆς",
        },
        872: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Porque doy testimonio juntamente a todo el que oye las "
                "palabras de la profecía de este libro:"
            ),
            "note": "TR Συμμαρτυροῦμαι γάρ (no Μαρτυρῶ ἐγώ)",
        },
        873: {
            "trPositions": list(range(12, 29)),
            "spanish": (
                "si alguno añade a estas cosas, Dios añadirá sobre él las "
                "plagas escritas en este libro."
            ),
            "note": "TR ἐπιτιθῇ πρὸς ταῦτα; ἐν βιβλίῳ τούτῳ",
        },
        874: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "Y si alguno quita de las palabras del libro de esta profecía,"
            ),
            "note": "TR ἀφαιρῇ ἀπὸ τῶν λόγων βίβλου",
        },
        875: {
            "trPositions": list(range(12, 28)),
            "spanish": (
                "Dios quitará su parte del libro de la vida y de la ciudad santa"
            ),
            "note": "TR ἀπὸ βίβλου τῆς ζωῆς (not ξύλου)",
        },
        876: {
            "trPositions": list(range(28, 34)),
            "spanish": "y de las cosas escritas en este libro.",
            "note": "TR καὶ τῶν γεγραμμένων",
        },
        877: {
            "trPositions": list(range(1, 13)),
            "spanish": (
                "El que da testimonio de estas cosas dice: Sí, vengo "
                "pronto. Amén. Sí, ven, Señor Jesús."
            ),
            "note": "TR ναί … ἀμήν Ναί ἔρχου",
        },
        878: {
            "trPositions": list(range(1, 12)),
            "spanish": (
                "La gracia de nuestro Señor Jesús Cristo sea con todos "
                "ustedes. Amén."
            ),
            "note": "TR τοῦ Κυρίου ἡμῶν Ἰησοῦ Χριστοῦ μετὰ πάντων ὑμῶν ἀμήν",
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
        # Hand walks may intentionally be empty (TR omits Morph clause).
        rp["greek"] = tr_greek if hand else (tr_greek or p.get("greek", ""))
        rp["spanish"] = spanish
        rp["tokenRows"] = token_rows
        rp["trAlignStatus"] = status
        rp["textualBasis"] = "Scrivener 1894 TR"
        if hand:
            rp["trWalkNote"] = hand["note"]
        remapped.append(rp)

    (OUT_DIR / "revelation-phrases-tr.json").write_text(
        json.dumps(remapped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Revelation TR spine (Robinson-parsed)",
        "",
        "Textual basis: **Scrivener 1894 TR** via `robinson-parsed/RE.UTR`.",
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

    (OUT_DIR / "revelation-tr-diff-report.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )
    (OUT_DIR / "revelation-phrase-remap-issues.json").write_text(
        json.dumps(phrase_issues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    mapped = sum(1 for p in remapped if p.get("trAlignStatus") == "mapped")
    partial = sum(1 for p in remapped if p.get("trAlignStatus") == "partial")
    print(json.dumps(stats, indent=2))
    print(f"phrases mapped={mapped} partial={partial} issues={len(phrase_issues)}")
    print("wrote", OUT_DIR)
    # Spot-check 1:1 and 1:2
    for ref in ("1:1", "1:2"):
        v = spine_verses[ref]
        print(f"{ref}:", v["trText"])
        print(f"{ref} strongs sample:", [t["strongs"] for t in v["tokens"][:8]])


if __name__ == "__main__":
    main()
