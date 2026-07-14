#!/usr/bin/env python3
"""Automate OT Hebrew lemma lexicon batches for BLE alignment.

Replaces the manual loop:
  1) inspect TOP lemmas still ?
  2) paste suggested lemma -> es
  3) update hbo_lemma_lexicon.json
  4) git commit / push
  5) python3 MNA/scripts/next_stepOT.py --book <book>

Examples (run from repo root `herramientas`):

  # Propose next batch (auto suggestions + unknowns for review)
  python3 MNA/scripts/ot_lemma_batch.py --book 1reyes --propose

  # Apply all high-confidence auto suggestions, update tokens, optional commit
  python3 MNA/scripts/ot_lemma_batch.py --book 1reyes --apply-auto --commit

  # Apply an explicit updates JSON object/file, then refresh tokens
  python3 MNA/scripts/ot_lemma_batch.py --book 1reyes --apply-json batch.json --commit

  # Keep applying auto batches until none remain
  python3 MNA/scripts/ot_lemma_batch.py --book 1reyes --apply-auto --loop --commit
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEXICON = REPO_ROOT / "MNA" / "datasets" / "rules" / "hbo_lemma_lexicon.json"
DEFAULT_RULES = REPO_ROOT / "MNA" / "datasets" / "rules"
DEFAULT_OT = REPO_ROOT / "MNA" / "datasets" / "interlinear" / "OT"
NEXT_STEP = REPO_ROOT / "MNA" / "scripts" / "next_stepOT.py"
PALEO_SCRIPTS = REPO_ROOT / "paleo-hebrew" / "scripts"

if str(PALEO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PALEO_SCRIPTS))

try:
    from ahrc_gloss_es import (  # type: ignore
        load_ahrc,
        load_compare,
        load_letter_notes,
        paleo_evidence_for_lemma,
    )
except Exception:  # pragma: no cover - paleo optional at import time
    load_ahrc = load_compare = load_letter_notes = paleo_evidence_for_lemma = None  # type: ignore

PREFIX_GLOSS = {
    "c": "y",
    "d": "el",
    "b": "en",
    "l": "a",
    "m": "de",
    "k": "según",
    "i": "¡",
    "s": "que",
}
PREF_SET = set(PREFIX_GLOSS)

BOOK_COMMIT_NAMES = {
    "genesis": "Genesis",
    "exodo": "Exodus",
    "levitico": "Leviticus",
    "numeros": "Numbers",
    "deuteronomio": "Deuteronomy",
    "josue": "Joshua",
    "jueces": "Judges",
    "rut": "Ruth",
    "1samuel": "1 Samuel",
    "2samuel": "2 Samuel",
    "1reyes": "1 Kings",
    "2reyes": "2 Kings",
    "1cronicas": "1 Chronicles",
    "2cronicas": "2 Chronicles",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, data) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path):
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception as e:
            raise SystemExit(f"{path}:{i}: invalid JSON: {e}")
    return rows


def split_lemma(lemma: str) -> tuple[list[str], str]:
    parts = lemma.split("/")
    prefs: list[str] = []
    i = 0
    while i < len(parts) - 1 and parts[i] in PREF_SET:
        prefs.append(parts[i])
        i += 1
    return prefs, "/".join(parts[i:])


def bare_num(bare: str) -> str:
    m = re.match(r"^(\d+)", bare)
    return m.group(1) if m else bare


def compose(prefs: list[str], base: str) -> str:
    if not prefs:
        return base
    return "·".join([PREFIX_GLOSS[p] for p in prefs] + [base])


def strip_prefix_gloss(gloss: str, prefs: list[str]) -> str | None:
    parts = gloss.split("·")
    expected = [PREFIX_GLOSS[p] for p in prefs]
    if len(parts) <= len(expected):
        return None
    if parts[: len(expected)] != expected:
        # tolerate missing article gender variants later if needed
        return None
    return "·".join(parts[len(expected) :])


def remaining_lemma_counts(book: str, rows: list[dict]) -> Counter:
    c: Counter = Counter()
    for r in rows:
        if r.get("book") == book and r.get("es") == "?":
            c[str(r.get("lemma", ""))] += 1
    return c


def sample_surfaces(rows: list[dict], book: str, lemma: str, limit: int = 3) -> list[str]:
    out = []
    for r in rows:
        if r.get("book") == book and r.get("es") == "?" and r.get("lemma") == lemma:
            out.append(f"{r.get('ch')}:{r.get('vs')} {r.get('surface')}")
            if len(out) >= limit:
                break
    return out


def build_base_index(lex: dict[str, str]) -> dict[str, Counter]:
    """Map bare Strong's stem -> candidate Spanish bases from existing lexicon."""
    by_bare: dict[str, Counter] = defaultdict(Counter)
    for key, gloss in lex.items():
        prefs, bare = split_lemma(key)
        if not prefs:
            by_bare[bare][gloss] += 3  # prefer explicit bare entries
            by_bare[bare_num(bare)][gloss] += 1
            continue
        base = strip_prefix_gloss(gloss, prefs)
        if base:
            by_bare[bare][base] += 2
            by_bare[bare_num(bare)][base] += 1
    return by_bare


def best_base(
    lex: dict[str, str],
    by_bare: dict[str, Counter],
    bare: str,
    *,
    allow_family: bool,
) -> tuple[str | None, str]:
    # Strict default: only reuse an exact bare lexicon key.
    if bare in lex:
        return lex[bare], "bare_exact"
    if not allow_family:
        return None, "unknown"
    if bare in by_bare and by_bare[bare]:
        return by_bare[bare].most_common(1)[0][0], "bare_family"
    num = bare_num(bare)
    if num in by_bare and by_bare[num]:
        return by_bare[num].most_common(1)[0][0], "num_family"
    return None, "unknown"


def propose_updates(
    book: str,
    tokens_path: Path,
    lex: dict[str, str],
    top: int | None = None,
    only_auto: bool = False,
    allow_family: bool = False,
    use_paleo: bool = True,
) -> tuple[dict[str, str], dict[str, dict], list[tuple[str, int]]]:
    rows = read_jsonl(tokens_path)
    counts = remaining_lemma_counts(book, rows)
    by_bare = build_base_index(lex)
    ranked = counts.most_common(top)

    ahrc_by = compare = letters = None
    if use_paleo and paleo_evidence_for_lemma is not None:
        ahrc_by = load_ahrc()
        compare = load_compare()
        letters = load_letter_notes()

    updates: dict[str, str] = {}
    meta: dict[str, dict] = {}
    unknowns: list[tuple[str, int]] = []

    for lemma, n in ranked:
        if lemma in lex:
            continue
        prefs, bare = split_lemma(lemma)
        base, source = best_base(lex, by_bare, bare, allow_family=allow_family)
        samples = sample_surfaces(rows, book, lemma)
        paleo = None
        if use_paleo and paleo_evidence_for_lemma is not None:
            paleo = paleo_evidence_for_lemma(
                lemma, ahrc_by=ahrc_by, compare=compare, letters=letters
            )
            if not base and paleo.get("es_candidates"):
                base = paleo["es_candidates"][0]
                source = "paleo_ahrc"

        if base:
            gloss = compose(prefs, base)
            updates[lemma] = gloss
            meta[lemma] = {
                "count": n,
                "source": source,
                "bare": bare,
                "base": base,
                "samples": samples,
                "paleo": summarize_paleo(paleo) if paleo else None,
            }
        else:
            unknowns.append((lemma, n))
            meta[lemma] = {
                "count": n,
                "source": "unknown",
                "bare": bare,
                "samples": samples,
                "paleo": summarize_paleo(paleo) if paleo else None,
            }

    if only_auto:
        unknowns = []
    return updates, meta, unknowns


def summarize_paleo(paleo: dict | None) -> dict | None:
    if not paleo:
        return None
    ahrc_short = []
    for row in paleo.get("ahrc") or []:
        ahrc_short.append({
            "translation": row.get("translation"),
            "definition": row.get("definition"),
            "hebrew": row.get("hebrew"),
            "parent_root": row.get("parent_root"),
            "parent_root_gloss": row.get("parent_root_gloss"),
            "kjv": row.get("kjv"),
        })
    return {
        "strongs": paleo.get("strongs"),
        "es_candidates": paleo.get("es_candidates") or [],
        "letter_hints": paleo.get("letter_hints") or [],
        "cgv_from_compare": paleo.get("cgv_from_compare") or [],
        "ahrc": ahrc_short,
        "notes": (paleo.get("notes") or [])[:4],
    }


def next_batch_number(book_label: str) -> int:
    try:
        out = subprocess.check_output(
            ["git", "log", "--oneline", "--grep", f"{book_label}: add Hebrew lemma batch", "-50"],
            cwd=REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return 1
    nums = []
    for line in out.splitlines():
        m = re.search(r"batch\s+(\d+)", line)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def run_next_step(book: str, top: int, *, force: bool = False) -> int:
    cmd = [
        sys.executable,
        str(NEXT_STEP),
        "--book",
        book,
        "--top",
        str(top),
        "--rules-dir",
        str(DEFAULT_RULES),
        "--tokens",
        str(DEFAULT_OT / f"{book}.tokens.jsonl"),
        "--overrides",
        str(DEFAULT_OT / "_overrides" / f"{book}.overrides.jsonl"),
    ]
    if force:
        cmd.append("--force")
    print("RUN:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def git_commit_lexicon(book: str, batch_no: int, push: bool) -> None:
    book_label = BOOK_COMMIT_NAMES.get(book, book)
    msg = f"{book_label}: add Hebrew lemma batch {batch_no}"
    subprocess.check_call(
        ["git", "add", "MNA/datasets/rules/hbo_lemma_lexicon.json"],
        cwd=REPO_ROOT,
    )
    # Also stage token file if changed by next_stepOT
    token_rel = f"MNA/datasets/interlinear/OT/{book}.tokens.jsonl"
    token_path = REPO_ROOT / token_rel
    if token_path.exists():
        subprocess.call(["git", "add", token_rel], cwd=REPO_ROOT)
    subprocess.check_call(["git", "commit", "-m", msg], cwd=REPO_ROOT)
    print("COMMIT:", msg)
    if push:
        subprocess.check_call(["git", "push"], cwd=REPO_ROOT)
        print("PUSHED")


def apply_updates(lex_path: Path, updates: dict[str, str]) -> dict[str, str]:
    data = load_json(lex_path)
    before = len(data)
    data.update(updates)
    write_json(lex_path, data)
    print(f"UPDATED {lex_path} +{len(updates)} (size {before} -> {len(data)})")
    return data


def print_proposal(book: str, updates: dict[str, str], meta: dict[str, dict], unknowns: list[tuple[str, int]]):
    print(f"\n{BOOK_COMMIT_NAMES.get(book, book)} — proposed lemma -> es")
    if updates:
        by_count: dict[int, list[str]] = defaultdict(list)
        for lemma, gloss in updates.items():
            by_count[int(meta[lemma]["count"])].append(lemma)
        for count in sorted(by_count, reverse=True):
            print(f"\ncount = {count}")
            for lemma in by_count[count]:
                m = meta[lemma]
                print(f"{lemma} → {updates[lemma]}  [{m['source']}]  samples={m.get('samples')}")
                paleo = m.get("paleo") or {}
                if paleo.get("ahrc") or paleo.get("letter_hints") or paleo.get("notes"):
                    ahrc0 = (paleo.get("ahrc") or [{}])[0]
                    print(
                        f"    paleo {paleo.get('strongs')}: "
                        f"AHRC={ahrc0.get('translation')!r} "
                        f"letters={paleo.get('letter_hints')[:3]} "
                        f"notes={paleo.get('notes')[:2]}"
                    )
    if unknowns:
        print("\nUNKNOWN (need manual/AI gloss):")
        for lemma, n in unknowns:
            m = meta[lemma]
            paleo = m.get("paleo") or {}
            print(f"{lemma}\t{n}\tsamples={m.get('samples')}")
            if paleo:
                ahrc0 = (paleo.get("ahrc") or [{}])[0]
                print(
                    f"    paleo {paleo.get('strongs')}: "
                    f"AHRC={ahrc0.get('translation')!r} "
                    f"def={ahrc0.get('definition')!r} "
                    f"cands={paleo.get('es_candidates')} "
                    f"letters={paleo.get('letter_hints')[:3]}"
                )
    print(f"\nAuto updates: {len(updates)} | Unknown: {len(unknowns)}")


def parse_updates_arg(raw: str) -> dict[str, str]:
    path = Path(raw)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit("--apply-json must be a JSON object of lemma -> gloss")
    return {str(k): str(v) for k, v in data.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", required=True)
    ap.add_argument("--top", type=int, default=30, help="lemma batch size / audit top N")
    ap.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--tokens", type=Path, default=None)
    ap.add_argument("--propose", action="store_true", help="print proposed auto updates + unknowns")
    ap.add_argument("--apply-auto", action="store_true", help="apply auto suggestions for remaining lemmas")
    ap.add_argument(
        "--allow-family",
        action="store_true",
        help="with --apply-auto/--propose, also infer from related Strong's family glosses (noisier)",
    )
    ap.add_argument(
        "--paleo",
        dest="use_paleo",
        action="store_true",
        default=True,
        help="use paleo-hebrew / AHRC evidence when suggesting glosses (default on)",
    )
    ap.add_argument(
        "--no-paleo",
        dest="use_paleo",
        action="store_false",
        help="disable paleo-hebrew / AHRC suggestions",
    )
    ap.add_argument("--apply-json", default="", help="JSON file or inline object of lemma->gloss updates")
    ap.add_argument("--all-remaining-auto", action="store_true", help="with --apply-auto, do not limit to --top")
    ap.add_argument("--loop", action="store_true", help="repeat --apply-auto until no auto suggestions remain")
    ap.add_argument("--commit", action="store_true", help="git commit lexicon (+ tokens) after apply")
    ap.add_argument("--push", action="store_true", help="git push after commit")
    ap.add_argument("--skip-next", action="store_true", help="do not run next_stepOT after apply")
    ap.add_argument("--write-proposal", type=Path, default=None, help="write proposal JSON for review")
    args = ap.parse_args()

    book = args.book
    tokens_path = args.tokens or (DEFAULT_OT / f"{book}.tokens.jsonl")
    if not tokens_path.exists():
        raise SystemExit(f"tokens not found: {tokens_path}")

    if not (args.propose or args.apply_auto or args.apply_json):
        args.propose = True

    batch_no = next_batch_number(BOOK_COMMIT_NAMES.get(book, book))
    loops = 0
    while True:
        loops += 1
        lex = load_json(args.lexicon)
        top = None if (args.apply_auto and args.all_remaining_auto) else args.top
        updates, meta, unknowns = propose_updates(
            book,
            tokens_path,
            lex,
            top=top,
            only_auto=args.apply_auto and not args.apply_json,
            allow_family=args.allow_family,
            use_paleo=args.use_paleo,
        )

        if args.apply_json:
            manual = parse_updates_arg(args.apply_json)
            updates = manual
            unknowns = []
            for lemma, gloss in manual.items():
                meta[lemma] = meta.get(lemma, {"count": 0, "source": "manual", "samples": []})
                meta[lemma]["source"] = "manual"
                meta[lemma]["gloss"] = gloss

        if args.propose and not (args.apply_auto or args.apply_json):
            print_proposal(book, updates, meta, unknowns)
            if args.write_proposal:
                payload = {
                    "book": book,
                    "updates": updates,
                    "unknowns": [{"lemma": l, "count": n, **meta[l]} for l, n in unknowns],
                    "meta": meta,
                }
                write_json(args.write_proposal, payload)
                print("WROTE", args.write_proposal)
            return 0

        if not updates:
            print("No updates to apply.")
            if not args.skip_next:
                run_next_step(book, args.top)
            return 0

        print_proposal(book, updates, meta, unknowns if not args.apply_auto else [])
        apply_updates(args.lexicon, updates)

        if not args.skip_next:
            rc = run_next_step(book, args.top)
            if rc != 0:
                return rc

        if args.commit:
            git_commit_lexicon(book, batch_no, push=args.push)
            batch_no += 1

        if not (args.loop and args.apply_auto):
            break

        # Stop looping when auto can no longer propose anything for remaining ?
        lex = load_json(args.lexicon)
        more, _, _ = propose_updates(
            book,
            tokens_path,
            lex,
            top=None if args.all_remaining_auto else args.top,
            only_auto=True,
            allow_family=args.allow_family,
            use_paleo=args.use_paleo,
        )
        if not more:
            print(f"Auto loop complete after {loops} batch(es).")
            break
        print(f"\n--- loop {loops + 1} ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
