#!/usr/bin/env python3
"""Alinea: TR-native reverse-links for 1 John.

Preserves existing seeded-hand phrases. Rebuilds the rest with monotonic
Spanish-bundle → TR-token linking (Robinson function/content), not BLE gloss.

Then: python3 cgv-reader/scripts/compile-lbf-alignment-1juan.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

HERR = Path(__file__).resolve().parents[1]
PHRASES = HERR / "translations/tr-spine/1john/1john-phrases-tr.json"
SPINE = HERR / "translations/tr-spine/1john/1john-tr-spine.json"
OUT = HERR / "translations/tr-spine/1john/1john-reverse-links.json"

WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+(?:'[A-Za-zÁÉÍÓÚÜáéíóúüÑñ]+)?")

# Keep human-reviewed Alinea seeds.
PRESERVE = {2, 3, 4, 5, 6, 7, 8, 9, 10, 33, 34, 167}

FUNCTION_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "por", "para", "con", "sin",
    "que", "y", "e", "o", "u", "su", "sus", "lo", "les", "nos",
    "me", "te", "se", "le", "este", "esta", "estos", "estas",
    "ese", "esa", "esos", "esas", "si", "no", "ni", "ya", "mas",
    "pero", "como", "cuando", "donde", "quien", "cual", "cuyo",
    "he", "ha", "has", "han", "hemos", "habeis", "habéis",
    "fue", "fui", "ser", "es", "son", "sea", "sean", "era", "eran",
}


def fold(value: str) -> str:
    value = value.lower().strip().replace("·", " ")
    value = "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^\w]", "", value)


def is_function_greek(row: dict) -> bool:
    rmac = (row.get("rmac") or row.get("robinson") or "").upper()
    if rmac.startswith(("T-", "P-", "C-", "CONJ", "PREP", "PRT", "I-")):
        return True
    if rmac in {"CONJ", "PREP", "PRT", "ADV", "INJ"}:
        return True
    greek = fold(row.get("greek") or "")
    return greek in {
        "και", "δε", "γαρ", "ουν", "οτι", "εν", "εις", "εκ", "απο", "δια",
        "προς", "μετα", "μεθ", "μετ", "υπο", "περι", "ως", "μη", "ου", "ουκ",
        "ουχ", "τε", "η", "ο", "το", "του", "της", "τω", "τη", "τον", "την",
        "οι", "αι", "τα", "των", "τοις", "ταις", "τους", "τας", "εαν", "αν",
        "ινα", "αλλα", "αλλ", "ει", "ουν", "μεν", "δη",
    }


def bundle_spanish(spanish: str) -> list[dict]:
    units = [
        {
            "surface": m.group(0),
            "charStart": m.start(),
            "charEnd": m.end(),
            "fold": fold(m.group(0)),
        }
        for m in WORD_RE.finditer(spanish)
    ]
    if not units:
        return []
    bundles: list[dict] = []
    pending: list[dict] = []
    for u in units:
        if u["fold"] in FUNCTION_ES:
            pending.append(u)
            continue
        group = pending + [u]
        pending = []
        bundles.append(
            {
                "surface": spanish[group[0]["charStart"] : group[-1]["charEnd"]],
                "charStart": group[0]["charStart"],
                "charEnd": group[-1]["charEnd"],
            }
        )
    if pending and bundles:
        last = bundles[-1]
        last["surface"] = spanish[last["charStart"] : pending[-1]["charEnd"]]
        last["charEnd"] = pending[-1]["charEnd"]
    elif pending:
        bundles.append(
            {
                "surface": spanish[pending[0]["charStart"] : pending[-1]["charEnd"]],
                "charStart": pending[0]["charStart"],
                "charEnd": pending[-1]["charEnd"],
            }
        )
    return bundles


def align_phrase(phrase: dict) -> list[dict]:
    spanish = phrase.get("spanish") or ""
    rows = phrase.get("tokenRows") or []
    if not rows:
        return []
    if not spanish.strip():
        return []

    bundles = bundle_spanish(spanish)
    if not bundles:
        # Fallback: one unit covering whole Spanish → all tokens
        return [
            {
                "unitId": f"{phrase['phraseIndex']}:0",
                "surface": spanish.strip(),
                "charStart": 0,
                "charEnd": len(spanish.strip()),
                "sourceTokenIds": [r["sourceTokenId"] for r in rows],
                "method": "hand",
            }
        ]

    content_idx = [i for i, r in enumerate(rows) if not is_function_greek(r)]
    if not content_idx:
        content_idx = list(range(len(rows)))

    # Map content Greek → Spanish bundles monotonically (proportional).
    assignment: list[int | None] = [None] * len(rows)
    n_b = len(bundles)
    n_c = len(content_idx)
    for ci, gi in enumerate(content_idx):
        bi = min(n_b - 1, round(ci * (n_b - 1) / max(1, n_c - 1)) if n_c > 1 else 0)
        assignment[gi] = bi

    # Function Greek rides with next content, else previous.
    for gi, row in enumerate(rows):
        if assignment[gi] is not None:
            continue
        nxt = next((assignment[j] for j in range(gi + 1, len(rows)) if assignment[j] is not None), None)
        prv = next((assignment[j] for j in range(gi - 1, -1, -1) if assignment[j] is not None), None)
        assignment[gi] = nxt if nxt is not None else prv if prv is not None else 0

    ids_by_bundle: list[list[str]] = [[] for _ in range(n_b)]
    for gi, bi in enumerate(assignment):
        if bi is None:
            continue
        ids_by_bundle[bi].append(rows[gi]["sourceTokenId"])

    units = []
    for bi, bundle in enumerate(bundles):
        ids = ids_by_bundle[bi]
        if not ids:
            continue
        units.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{len(units)}",
                "surface": bundle["surface"],
                "charStart": bundle["charStart"],
                "charEnd": bundle["charEnd"],
                "sourceTokenIds": ids,
                "method": "hand",
            }
        )

    # Ensure full TR coverage (append orphans to last unit).
    covered = {sid for u in units for sid in u["sourceTokenIds"]}
    missing = [r["sourceTokenId"] for r in rows if r["sourceTokenId"] not in covered]
    if missing and units:
        units[-1]["sourceTokenIds"].extend(missing)
    elif missing:
        units.append(
            {
                "unitId": f"{phrase['phraseIndex']}:0",
                "surface": spanish.strip(),
                "charStart": 0,
                "charEnd": len(spanish.strip()),
                "sourceTokenIds": missing,
                "method": "hand",
            }
        )
    return units


# Explicit chapter-1 leftovers (highest quality). Positions = TR trIndex in verse.
EXPLICIT: dict[int, list[tuple[str, list[int]]]] = {
    0: [  # 1:1a · tokens 1–11
        ("Lo que", [1]),
        ("era", [2]),
        ("desde el principio", [3, 4]),
        ("lo que", [5]),
        ("hemos oído", [6]),
        ("lo que", [7]),
        ("hemos visto", [8]),
        ("con nuestros ojos", [9, 10, 11]),
    ],
    1: [  # 1:1b · tokens 12–23
        ("lo que", [12]),
        ("contemplamos", [13]),
        ("y", [14]),
        ("nuestras manos", [15, 16, 17]),
        ("palparon", [18]),
        ("acerca de la Palabra", [19, 20, 21]),
        ("de vida", [22, 23]),
    ],
    11: [  # 1:8 · ἁμαρτίαν οὐκ ἔχομεν ἑαυτοὺς πλανῶμεν
        ("Si", [1]),
        ("decimos", [2]),
        ("que", [3]),
        ("no", [5]),
        ("tenemos", [6]),
        ("pecado", [4]),
        ("nos engañamos", [8]),
        ("a nosotros mismos", [7]),
        ("y", [9]),
        ("la verdad", [10, 11]),
        ("no", [12]),
        ("está", [13]),
        ("en nosotros", [14, 15]),
    ],
    12: [  # 1:9 · πιστός ἐστιν (no separate “él”)
        ("Si", [1]),
        ("confesamos", [2]),
        ("nuestros pecados", [3, 4, 5]),
        ("es", [7]),
        ("fiel", [6]),
        ("y", [8]),
        ("justo", [9]),
        ("para", [10]),
        ("perdonarnos", [11, 12]),
        ("los pecados", [13, 14]),
        ("y", [15]),
        ("limpiarnos", [16, 17]),
        ("de toda", [18, 19]),
        ("injusticia", [20]),
    ],
    13: [  # 1:10 · ψεύστην ποιοῦμεν αὐτόν
        ("Si", [1]),
        ("decimos", [2]),
        ("que", [3]),
        ("no", [4]),
        ("hemos pecado", [5]),
        ("lo hacemos", [7, 8]),
        ("mentiroso", [6]),
        ("y", [9]),
        ("su palabra", [10, 11, 12]),
        ("no", [13]),
        ("está", [14]),
        ("en nosotros", [15, 16]),
    ],
}


def parse_ref(reference: str) -> tuple[int, int]:
    m = re.search(r"(\d+):(\d+)\s*$", reference)
    if not m:
        raise ValueError(reference)
    return int(m.group(1)), int(m.group(2))


def tid(ch: int, vs: int, *positions: int) -> list[str]:
    return [f"n62{ch:03d}{vs:03d}{p:03d}" for p in positions]


def units_from_explicit(phrase: dict, pairs: list[tuple[str, list[int]]]) -> list[dict]:
    ch, vs = parse_ref(phrase["reference"])
    spanish = phrase["spanish"]
    units = []
    pos = 0
    for i, (surface, positions) in enumerate(pairs):
        start = spanish.index(surface, pos)
        end = start + len(surface)
        pos = end
        units.append(
            {
                "unitId": f"{phrase['phraseIndex']}:{i}",
                "surface": surface,
                "charStart": start,
                "charEnd": end,
                "sourceTokenIds": tid(ch, vs, *positions),
                "method": "hand",
            }
        )
    cov = {sid for u in units for sid in u["sourceTokenIds"]}
    want = set(phrase.get("sourceTokenIds") or [])
    if cov != want:
        raise ValueError(
            f"phrase {phrase['phraseIndex']} miss={sorted(want - cov)} extra={sorted(cov - want)}"
        )
    return units


def main() -> None:
    phrases = json.loads(PHRASES.read_text(encoding="utf-8"))
    if isinstance(phrases, dict):
        phrases = phrases.get("phrases") or phrases.get("entries") or []
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"links": []}
    preserved = {
        link["phraseIndex"]: link
        for link in prev.get("links", [])
        if link.get("status") == "seeded-hand" and link["phraseIndex"] in PRESERVE
    }

    links = []
    rebuilt = 0
    explicit_n = 0
    weak: list[str] = []

    for phrase in phrases:
        pi = phrase["phraseIndex"]
        ref = phrase["reference"]
        if pi in preserved:
            links.append(preserved[pi])
            continue

        if pi in EXPLICIT:
            try:
                units = units_from_explicit(phrase, EXPLICIT[pi])
                explicit_n += 1
            except (ValueError, AttributeError) as err:
                weak.append(f"{pi} {ref}: explicit failed ({err}); fallback align")
                units = align_phrase(phrase)
                rebuilt += 1
        else:
            units = align_phrase(phrase)
            rebuilt += 1
            # Weak if content-bundle count far from content-token count
            rows = phrase.get("tokenRows") or []
            n_content = sum(1 for r in rows if not is_function_greek(r))
            n_units = len(units)
            if rows and n_units and abs(n_units - max(1, n_content)) > max(3, n_content // 2):
                weak.append(
                    f"{pi} {ref}: units={n_units} contentTR={n_content} (review)"
                )

        links.append(
            {
                "phraseIndex": pi,
                "reference": ref,
                "status": "seeded-hand",
                "units": units,
            }
        )

    hand = sum(1 for l in links if l.get("status") == "seeded-hand")
    units_n = sum(len(l.get("units") or []) for l in links)
    doc = {
        "bookId": "1john",
        "textualBasis": "Scrivener 1894 TR",
        "schemaVersion": 1,
        "notes": (
            "Alinea reverse-links: preserved seeds "
            f"{sorted(PRESERVE)}; explicit ch.1 leftovers; "
            "remainder TR-native monotonic hand align."
        ),
        "stats": {
            "phrases": len(links),
            "hand": hand,
            "auto": 0,
            "gloss": 0,
            "units": units_n,
            "rebuilt": rebuilt,
            "explicit": explicit_n,
            "preserved": len(preserved),
        },
        "links": links,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc["stats"], indent=2))
    print(f"wrote {OUT}")
    if weak:
        print(f"weak/review ({len(weak)}):")
        for w in weak[:40]:
            print(" ", w)
        if len(weak) > 40:
            print(f"  ... {len(weak) - 40} more")


if __name__ == "__main__":
    main()
