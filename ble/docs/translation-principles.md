# BLE translation principles

BLE aims at **formal literalness**: each word (or morpheme) in the source should have a corresponding Spanish expression, in source order, without adding interpretive smoothing.

## Gloss layer (MNA tokens)

Each token carries:

| Field | Role |
|-------|------|
| `surface` | word as printed in Greek/Hebrew |
| `lemma` | dictionary form |
| `morph` | morphology tag |
| `es` | **BLE gloss** — the Spanish literal rendering of this token |

Glosses are written for **transparency**, not pulpit fluency.

### Conventions

- **Mid-dot (`·`)** — joins article or preposition to the following word in the gloss (`de·genealogía`, `a·el`). Expanded to a space in published verses.
- **Punctuation** — stays on the gloss of the token that carries it in Greek (`de·Abraham.`).
- **Proper names** — Spanish forms (`Jesús`, `Abraham`, `Judá`).
- **Particles** — one gloss each (`δέ` → `y`, `καί` → `y`); not merged away.
- **Gender and number** — Spanish glosses must agree with the Greek `morph` tag (not just the lemma). See [gender-and-number.md](gender-and-number.md).

## Verse assembly

Published BLE text is **mechanical assembly** of glosses:

1. Group tokens by verse.
2. Order by `tok`.
3. Expand `·` → space in each gloss.
4. Join with single spaces.

No post-processing for “better Spanish” in the default pipeline. If a verse should read more naturally while staying literal, **change the glosses**, not the assembler.

## What BLE is not

- Not a replacement for NBLA or other readable translations.
- Not commentary, theology, or interpretive paraphrase.
- Not word-study notes — those belong in interlinear tables and MNA analysis layers.

## Quality bar

A verse is ready for BLE publication when:

- Every token has a non-`?` gloss.
- The assembled line parses as a valid BLE verse file line.
- A reader can align Spanish words to Greek tokens using the interlinear dataset.
