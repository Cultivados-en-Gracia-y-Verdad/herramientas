# Stage 1 — Finite Verbal Extraction

## Purpose

Stage 1 exists to mechanically verify finite verbal forms from the Greek text.

Stage 1 is a pure observable data layer.

Stage 1 performs no interpretation, no structure generation, and no discourse analysis.

------

# Inputs

Stage 1 requires:

- Greek token stream,
- MorphGNT morphology data.

------

# Output

Stage 1 outputs only:

- finite verbal existence,
- finite morphology,
- grammatical data,
- token location.

------

# Allowed Data

Stage 1 may output:

- greek_form
- lemma
- morphology
- tense
- voice
- mood
- person
- number
- token_index
- is_finite

------

# Canonical Stage 1 Record

```
{
  "token_index": 0,
  "greek_form": "",
  "lemma": "",
  "morphology": "",
  "is_finite": true,
  "person": "",
  "number": "",
  "tense": "",
  "voice": "",
  "mood": ""
}
```

------

# Mechanical Rules

```
1 finite form = 1 Stage 1 record
No finite form may be skipped silently
Stage 1 follows source token order only
```

------

# Forbidden Operations

Stage 1 may NOT perform:

- structure generation,
- continuity analysis,
- movement analysis,
- independency testing,
- trunk extraction,
- connector interpretation,
- grouping,
- unit formation,
- semantic analysis,
- discourse analysis,
- inferred relationships.

------

# Architectural Boundary

Stage 1 is not intelligent.

Stage 1 is not interpretive.

Stage 1 is a mechanical extraction layer only.

------

# Validation Requirements

Stage 1 must provide:

- reproducible counts,
- deterministic extraction,
- auditable outputs,
- source-bound verification.

------

# Truthfulness Constraint

Stage 1 may not claim any structure beyond explicitly observable finite morphology.