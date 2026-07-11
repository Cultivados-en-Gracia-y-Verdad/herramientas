# AHRC sources

Investigative references for OT translation work. Live content lives on [ancient-hebrew.org](https://www.ancient-hebrew.org); this repo keeps URLs, letter notes, and links into CGV pipelines — not full lexicon copies.

## Primary entry points

| Resource | URL | Use |
|----------|-----|-----|
| Introduction | [introduction.htm](https://www.ancient-hebrew.org/introduction.htm) | Culture, concrete/function thought, why translations lose nuance |
| AHLB index | [ahlb/index.html](https://www.ancient-hebrew.org/ahlb/index.html) | Parent-root lexicon organized by first letter |
| AHLB — Aleph | [ahlb/aleph.html](https://www.ancient-hebrew.org/ahlb/aleph.html) | All parent roots beginning with א (אב, אל, אם, …) |
| Alphabet — Aleph | [ancient-alphabet/aleph.htm](https://www.ancient-hebrew.org/ancient-alphabet/aleph.htm) | Pictograph, history, sound |

Machine-readable catalog: `data/sources/ahrc.json`.

## How this feeds OT translation

1. **Letter layer** — pictograph meanings (ox = strength, lamed = staff, etc.) inform gloss choices in MNA/LBF.
2. **Parent-root layer** — AHLB groups two-letter roots with action/object/abstract tags and Strong's links.
3. **Culture layer** — introduction stresses nomadic, concrete, function-oriented reading (not Western abstract glosses).

## CGV cross-links

| CGV asset | Link |
|-----------|------|
| OSHB / MNA OT tokens | Square Hebrew + morphology per word |
| `cgv-lexicon` | Lemma observations and gloss lookup |
| `Biblia-LBF` | OT translation target |
| `paleo-hebrew` scripts | Square → Paleo display (`data/letter-map.json`) |

## Working notes

- Treat AHRC as **research input**, not automatic truth — verify against OSHB, BDB/Strong's, and CGV lexicon.
- Add one letter file at a time under `data/letters/` as we study each AHLB page.
- Full AHLB letter URLs are listed in `data/sources/ahrc.json` → `ahlb_letter_pages`.

## Credit

Content and methodology from **Jeff A. Benner**, [Ancient Hebrew Research Center](https://www.ancient-hebrew.org).
