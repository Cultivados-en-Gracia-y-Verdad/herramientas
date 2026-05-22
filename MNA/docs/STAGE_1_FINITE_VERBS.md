# MNA Stage 1 — Finite Verbs

## Status

FROZEN.

Stage 1 is an absolute-fact data layer.

Stage 1 is not intelligent.
Stage 1 is not interpretive.
Stage 1 performs no structural analysis.

## Purpose

Extract verified finite verbal forms from the Greek text using MorphGNT morphology.

## Inputs

- Greek token stream
- MorphGNT morphology

## Output

One record for every verified finite verbal form.

## Allowed Output Only

- finite form existence
- Greek form
- lemma
- morphology
- tense
- voice
- mood
- person
- number
- token location

## Canonical Record

```json
{
  "record_type": "finite_verb",
  "book": "",
  "chapter": 0,
  "verse": 0,
  "token_index": 0,
  "greek_form": "",
  "lemma": "",
  "morphology": "",
  "is_finite": true,
  "tense": "",
  "voice": "",
  "mood": "",
  "person": "",
  "number": ""
}
```

## Mechanical Rules

1. One verified finite form equals one Stage 1 record.
2. No finite form may be skipped silently.
3. Records preserve source token order.
4. Stage 1 may only report morphology-derived facts.

## Forbidden Operations

Stage 1 may not output or imply:

- clause structure
- semantic structure
- discourse structure
- continuity
- movement
- independency
- trunk
- connectors
- grouping
- units
- titles
- inferred relationships

## Validation Requirements

The validator must verify:

- finite count equals extracted record count
- all records preserve source order
- every record has morphology
- no duplicate finite records
- no unresolved finite form is silently ignored

## Truthfulness Rule

Stage 1 may claim only what is directly observable from Greek morphology and token location.
