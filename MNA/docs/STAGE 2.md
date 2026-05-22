# Stage 2 — Predicate Anchor Extraction

## Purpose

Stage 2 converts verified finite verbal forms into immutable predicate anchors.

Stage 2 is a pure observable data layer.

Stage 2 performs no interpretation, no structure generation, and no discourse analysis.

------

# Inputs

Stage 2 requires:

- Stage 1 verified finite verbs,
- Greek token stream.

------

# Output

Stage 2 outputs only:

- anchor existence,
- immutable anchor ids,
- anchor order,
- observable adjacency,
- explicit connectors,
- explicit lexical subjects.

------

# Allowed Data

Stage 2 may output:

- anchor_id
- token_index
- greek_form
- lemma
- morphology
- previous_anchor
- next_anchor
- adjacency_distance
- explicit_connector_before
- explicit_subject_before

------

# Canonical Stage 2 Record

```
{
  "anchor_id": "",
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

------

# Mechanical Rules

```
1 Stage 1 finite form = 1 predicate anchor
Anchor IDs are immutable
Anchor order follows source token order only
Adjacency is token-distance only
Explicit means explicitly present in the token stream
```

------

# Explicit Connector Rule

Stage 2 may output:

```
explicit_connector_before
```

only if the connector is explicitly observable before the anchor.

No inferred connector relationships are allowed.

------

# Explicit Subject Rule

Stage 2 may output:

```
explicit_subject_before
```

only if an explicit lexical subject is visibly present in the token stream.

No implied subjects are allowed.

No inferred subjects are allowed.

------

# Forbidden Operations

Stage 2 may NOT perform:

- subject continuity analysis,
- lexical subject change analysis,
- movement analysis,
- independency testing,
- trunk extraction,
- grouping,
- continuity theory,
- structural segmentation,
- discourse analysis,
- semantic analysis,
- inferred relationships.

------

# Architectural Boundary

Stage 2 is not intelligent.

Stage 2 is not interpretive.

Stage 2 is a mechanical anchor extraction layer only.

------

# Validation Requirements

Stage 2 must provide:

- immutable anchor tracking,
- reproducible anchor ordering,
- auditable adjacency,
- explicit observable metadata only.

------

# Truthfulness Constraint

Stage 2 may not claim any structure beyond explicitly observable anchor metadata.