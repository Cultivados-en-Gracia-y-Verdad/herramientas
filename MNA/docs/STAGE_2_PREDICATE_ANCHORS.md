# MNA Stage 2 — Predicate Anchors

## Status

FROZEN.

Stage 2 is an absolute-fact data layer.

Stage 2 is not intelligent.
Stage 2 is not interpretive.
Stage 2 performs no structural analysis.

## Purpose

Convert verified finite verbal forms into immutable predicate anchors.

## Inputs

- Stage 1 verified finite verbs
- Greek token stream

## Core Rule

One Stage 1 finite form equals one predicate anchor.

## Output

One predicate-anchor record per verified finite form.

## Allowed Output Only

- anchor existence
- immutable anchor id
- anchor order
- observable adjacency
- explicit connectors
- explicit lexical subjects

## Canonical Record

```json
{
  "record_type": "predicate_anchor",
  "anchor_id": "",
  "book": "",
  "chapter": 0,
  "verse": 0,
  "token_index": 0,
  "greek_form": "",
  "lemma": "",
  "morphology": "",
  "previous_anchor": "",
  "next_anchor": "",
  "adjacency_distance": 0,
  "explicit_connector_before": "",
  "explicit_subject_before": ""
}
```

## Mechanical Rules

1. One Stage 1 finite form equals one predicate anchor.
2. Anchor IDs are immutable.
3. Anchor order follows source token order only.
4. Adjacency is token-distance only.
5. Explicit means explicitly present in the token stream.

## Explicit Connector Rule

Stage 2 may output:

```text
explicit_connector_before
```

only if explicitly observable before the anchor.

No inferred connector relationships are allowed.

## Explicit Subject Rule

Stage 2 may output:

```text
explicit_subject_before
```

only if explicitly observable in the token stream.

No implied subjects are allowed.
No inferred subjects are allowed.

## Forbidden Operations

Stage 2 may not output or imply:

- subject continuity
- movement
- independency
- trunk
- grouping
- continuity theory
- structural segmentation
- discourse structure
- semantic structure
- inferred relationships
- units
- titles

## Validation Requirements

The validator must verify:

- anchor count equals Stage 1 finite count
- anchor order preserves source order
- anchor IDs remain unique
- adjacency is mechanically reproducible
- only explicit metadata is emitted

## Truthfulness Rule

Stage 2 may claim only what is directly observable from:

- finite morphology
- anchor existence
- anchor order
- explicit connectors
- explicit lexical subjects
- observable adjacency
