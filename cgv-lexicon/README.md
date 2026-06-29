# CGV Lexicon — Greek & Hebrew

Unified lemma lookup for CGV tools: **Writer**, **Presenter**, interlinear QA, and future study apps.

This is **not** a full BDAG/BDB replacement. v1 assembles what the CGV pipeline already maintains:

| Source | Language | What it provides |
|--------|----------|------------------|
| `MNA/datasets/rules/grc_lemma_lexicon.json` | Greek | Spanish gloss (BLE-oriented) |
| `MNA/datasets/rules/grc_lemma_strongs.json` | Greek | Strong's G-number per lemma |
| `MNA/datasets/rules/grc_lemma_strongs_supplement.json` | Greek | MorphGNT spelling gaps |
| `MNA/datasets/rules/hbo_lemma_lexicon.json` | Hebrew | Spanish gloss |
| OSHB lemma ids in OT tokens | Hebrew | Strong's H-number (numeric lemmas) |

Later layers can add full definitions (OpenScriptures Strong's, BDB snippets, usage counts from tokens).

## Entry format (v1)

One JSON object per line in `data/grc.entries.jsonl` / `data/hbo.entries.jsonl`:

```json
{
  "lang": "grc",
  "lemma": "ἐκλέγομαι",
  "strongs": "G1586",
  "gloss_es": "escoger",
  "sources": ["grc_lemma_lexicon", "grc_lemma_strongs"]
}
```

Hebrew (OSHB-style lemma keys):

```json
{
  "lang": "hbo",
  "lemma": "1254 a",
  "strongs": "H1254",
  "gloss_es": "crear",
  "sources": ["hbo_lemma_lexicon"]
}
```

## Build

```bash
cd cgv-lexicon
python3 scripts/build_lexicon.py
```

Writes `data/grc.entries.jsonl`, `data/hbo.entries.jsonl`, and `data/manifest.json`.

## TypeScript lookup (Writer / web)

```ts
import { lookupLemma, formatLexiconLine } from "cgv-lexicon";

lookupLemma("grc", "ἐκλέγομαι");
// → { lang, lemma, strongs: "G1586", gloss_es: "escoger", ... }
```

## Integration roadmap

| Phase | Deliverable |
|-------|-------------|
| **v1 (now)** | Merge rules → JSONL + `cgv-lexicon` lookup package |
| **v2** | Strong's definition text (Greek + Hebrew) in Spanish or English |
| **v3** | Token frequency + sample verses from interlinear JSONL |
| **v4** | Writer: click lemma in interlinear / definition blocks |

## Project layout

```
cgv-lexicon/
  README.md
  package.json
  scripts/build_lexicon.py
  data/              # generated entries + manifest
  src/               # TS lookup (cgv-bible style)
```

## Related projects

| Project | Role |
|---------|------|
| **MNA** | Canonical lemmas, glosses, morphology |
| **BLE** | Spanish glosses per token |
| **cgv-bible** | Verse lookup by reference |
| **cgv-writer** | Course manuals; future lexicon popups |
