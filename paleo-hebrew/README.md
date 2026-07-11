# Paleo-Hebrew

Investigative workspace toward **OT translation** — Paleo-Hebrew script, letter semantics, and parent-root research.

## Purpose

This project is not a published Bible yet. It collects:

1. **Script tools** — square Hebrew (OSHB / MNA) → Paleo-Hebrew display
2. **Letter semantics** — pictograph meanings for translation decisions
3. **External research** — [AHRC](https://www.ancient-hebrew.org) (Jeff A. Benner), starting with [introduction](https://www.ancient-hebrew.org/introduction.htm) and [AHLB — Aleph](https://www.ancient-hebrew.org/ahlb/aleph.html)

```
OSHB / MNA OT tokens
        ↓
letter meaning + parent-root study (AHRC, cgv-lexicon)
        ↓
gloss / translation hypotheses → Biblia-LBF
        ↓
optional Paleo display (square_to_paleo.py)
```

## Layout

| Path | Purpose |
|------|---------|
| `data/letter-map.json` | Square Hebrew ↔ Paleo Unicode |
| `data/letters/` | Per-letter study notes (e.g. `aleph.json`) |
| `data/sources/ahrc.json` | AHRC URL catalog |
| `scripts/` | Conversion and text helpers |
| `docs/sources/` | How we use external references |
| `samples/` | Hand-checked Hebrew snippets |
| `output/` | Generated Paleo text |

## Lemma compare (OT + AHRC)

Build indexes once, then compare any Strong's number:

```bash
cd paleo-hebrew

# import AHRC AHLB page (saved HTML or live URL)
python3 scripts/parse_ahlb_html.py --url https://www.ancient-hebrew.org/ahlb/aleph.html --merge

# index MNA OT tokens by Strong's (Torah books so far)
python3 scripts/build_ot_lemma_index.py
python3 scripts/build_lemma_compare.py

# side-by-side view
python3 scripts/compare_lemma.py H24
python3 scripts/compare_lemma.py H430
python3 scripts/compare_lemma.py --list --book genesis --linked-only
```

Output: `data/index/lemma-compare.jsonl` (MNA occurrences + CGV gloss + AHRC entry per H-number).

## Quick start

```bash
cd paleo-hebrew

python3 scripts/square_to_paleo.py --strip-vowels "בְּרֵאשִׁית"
python3 scripts/square_to_paleo.py --input samples/bereshit.txt --output output/bereshit.paleo.txt --strip-vowels
```

## AHRC references (OT investigation)

| Page | URL |
|------|-----|
| Introduction | https://www.ancient-hebrew.org/introduction.htm |
| AHLB — Aleph | https://www.ancient-hebrew.org/ahlb/aleph.html |
| Alphabet — Aleph | https://www.ancient-hebrew.org/ancient-alphabet/aleph.htm |

See [docs/sources/ahrc.md](docs/sources/ahrc.md) for full catalog and methodology.

## Related projects

| Project | Role |
|---------|------|
| `MNA/` | OT interlinear tokens |
| `Biblia-LBF/` | OT translation (La Biblia Fiel) |
| `cgv-lexicon/` | Lemma lookup |
| `cgv-data/` | Published assets |

## Status

- [x] Letter map + square ↔ paleo scripts
- [x] AHRC source catalog
- [x] Aleph letter notes + sample parent roots
- [ ] Remaining 21 AHLB letter pages
- [ ] Crosswalk AHRC Strong's → MNA lemmas
- [ ] OT verse investigation templates
