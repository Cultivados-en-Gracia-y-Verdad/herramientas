# BLE — Biblia Literal en Español

**Goal:** produce a literal Bible in Spanish — verse by verse, faithful to the form of the original languages, not a dynamic-equivalence paraphrase.

BLE is the **published text**. Everything else (MNA tokens, morphology, gloss rules) exists to create and audit that text.

## What “literal” means here

| | BLE | NBLA (reference) |
|---|-----|------------------|
| Unit | one Spanish gloss per Greek/Hebrew token | readable Spanish sentence |
| Word order | follows the source where glosses allow | natural Spanish |
| Articles, clitics | explicit (`a el`, `de la`) | smoothed (`al`, `de la`) |
| Purpose | see what the original says, word by word | read fluently in church |

Example — Mateo 1:1:

```text
BLE:  libro de genealogía de Jesús de Cristo de hijo de David de hijo de Abraham.
NBLA: Libro de la genealogía de Jesucristo, hijo de David, hijo de Abraham.
```

BLE is for study and interlinear work. NBLA remains the fluency reference in `MNA/SOURCES/NBLA/`.

## Product

One file per book, `{book}.ble.md`, in `output/`:

```text
Mateo 1:1 libro de genealogía de Jesús de Cristo de hijo de David de hijo de Abraham.
```

Install in a CGV library as `bibles/BLE/` for Writer and Presenter.

## How it is made

1. **Greek (NT)** — MorphGNT → `MNA/datasets/interlinear/NT/{book}.tokens.jsonl`
2. **Glosses** — each token has an `es` field (Spanish literal gloss); edited via MNA rules and patches
3. **Assembly** — `scripts/tokens_to_ble.py` joins glosses into verses (the BLE text)

```bash
cd ble
python3 scripts/tokens_to_ble.py mateo   # one book
python3 scripts/tokens_to_ble.py --all   # full NT
python3 scripts/validate_ble.py output/mateo.ble.md

# Interlinear reader (QA / gloss editing)
python3 scripts/tokens_to_reader.py mateo --chapter 1
python3 scripts/tokens_to_reader.py mateo              # all chapters, one .reader.md per chapter
python3 scripts/tokens_to_reader.py --all              # full NT interlinear export

# e-Sword Bible modules (NT only)
python3 scripts/ble_to_esword.py
# → output/esword/BLE.bblx  (Windows)
# → output/esword/BLE.bbli  (e-Sword X / macOS, iOS, Android)

# Convert an existing .bblx to .bbli
python3 scripts/bblx_to_bbli.py output/esword/BLE.bblx
```

Canonical rule: if a verse cannot be rebuilt from tokens by the producer script, it is not official BLE text. Gloss corrections go in MNA token data, not by hand-editing `.ble.md`.

## Scope

| Testament | Status |
|-----------|--------|
| **NT** | 27 books · ~137k tokens · glosses complete · ready to assemble |
| **OT** | not yet — `genesis.tokens.jsonl` only in MNA |

## Interlinear first, or literal Bible first?

**Both come from the same source** — `MNA/datasets/interlinear/NT/{book}.tokens.jsonl`. You are not building two independent translations.

```text
tokens.jsonl  ←  canonical (Greek + es gloss per word)
      │
      ├── interlinear output   ←  for editing & QA (see each gloss in context)
      │
      └── BLE .ble.md          ←  literal Bible (glosses joined into verses)
```

| If your priority is… | Start with… |
|----------------------|-------------|
| **Fixing and trusting the text** | **Interlinear** — review Greek ↔ Spanish token by token; fix glosses in MNA tokens/patches |
| **Reading or shipping something now** | **Literal Bible** — already built in `output/`; regenerate anytime with `tokens_to_ble.py` |

**Recommendation:** use **interlinear for editorial work**, **literal Bible for publication**. Assembly takes seconds; gloss quality is the slow part.

Practical loop:

1. Export interlinear for a book or chapter (table or aligned reader).
2. Correct `es` glosses in token data (MNA patches).
3. Re-run `tokens_to_ble.py` — the literal Bible updates automatically.

**Marcos** is the current exception: 243 tokens still lack glosses — fix those in interlinear/token form before treating that book as done.

The literal NT in `output/` is a **draft** you can read today; interlinear review is how you make it trustworthy.

## Docs

- [verse-format.md](docs/verse-format.md) — file layout for CGV apps
- [translation-principles.md](docs/translation-principles.md) — gloss and assembly conventions
- [gender-and-number.md](docs/gender-and-number.md) — morphology agreement and inclusive-plural policy
