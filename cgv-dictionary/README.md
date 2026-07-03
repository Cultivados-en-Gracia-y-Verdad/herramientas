CGV Dictionary
Purpose

The CGV Dictionary documents every biblical lemma found in the Hebrew and Greek source texts.

It exists to support the translation of La Biblia Fiel and other CGV tools by providing a consistent, observable, and reproducible record of each lemma.

Philosophy

The dictionary is governed by the same principle as LBF:

Dejar que las Escrituras hablen por sí mismas.

Therefore, the dictionary seeks to distinguish between:

observation and interpretation
lexical usage and theological conclusions
textual evidence and translation decisions
Guiding Principles
The biblical text defines usage.
Strong's numbers are used only as identifiers.
Meanings arise from biblical usage, not etymology alone.
Translation notes document LBF decisions, not universal rules.
Every entry should be traceable to the biblical text.

## Validate and build indexes

From the `herramientas` repo root:

```bash
npm run dictionary:validate
```

This will:

1. Read every `cgv-dictionary/greek/G*/lemma.json`
2. Validate against `schema/lemma.schema.json`
3. Report invalid JSON, missing fields, duplicates, and status errors
4. Write `indexes/greek.json` (compact lookup index)

## Extract occurrences

```bash
npm run dictionary:extract -- G3341
```

Reads `MNA/datasets/interlinear/NT/*.tokens.jsonl` and writes
`greek/G3341/occurrences.json` with observable token data only (no translation notes).

## Analyze occurrences

```bash
npm run dictionary:analyze -- G3341
```

Reads `greek/G3341/occurrences.json` and writes `analysis.json` with objective statistics
(count, books, morphology, forms, cases, nearby words, repeated phrases).