# Trunk + Subject Change + Movement Defined

## Purpose

This document defines the formal mechanics for Stage 3 of the MNA system.

Stage 3 uses verified predicate anchors to produce an early structural skeleton.

Stage 3 identifies:

- trunk sequence,
- subject/person-number change markers `[S]`,
- movement change markers `[M]`.

Stage 3 does NOT use connectors.

Stage 3 does NOT assign labels.

Stage 3 does NOT form patterns or units.

Stage 3 does NOT create titles.

---

# Foundational Principle

## Anchor-First Structure

Stage 3 structure comes from predicate anchors.

It does not come from:

- connectors,
- English translation structure,
- theological interpretation,
- semantic guessing,
- discourse assumptions,
- full predicate spans.

The input to Stage 3 is the verified Stage 2A predicate-anchor dataset.

---

# Stage Relationship

## Required Previous Stage

Stage 3 may run only after Stage 2A has passed validation for the book.

For 1corintios:

```text
FINITE_VERBS: 1027
PREDICATE_ANCHORS: 1027
STATUS: PASS
```

These predicate anchors become the ordered input sequence for Stage 3.

---

# Stage 3 Output

## Primary Output

Stage 3 produces a trunk skeleton from predicate anchors.

The trunk skeleton is an ordered list of predicate anchors with structural markers.

Each row may include:

- predicate_anchor_id,
- book,
- chapter,
- verse,
- reference,
- anchor_order,
- greek_surface,
- greek_clean,
- lemma,
- morphology,
- mood,
- person,
- number,
- subject_signature,
- previous_subject_signature,
- subject_change_marker,
- movement_signature,
- previous_movement_signature,
- movement_marker,
- trunk_status.

---

# Trunk Defined

## Formal Definition

At Stage 3, trunk means:

> the ordered predicate-anchor sequence used as the structural skeleton of the text.

This is not yet a full clause structure.

This is not yet a predicate span structure.

This is not yet a connector structure.

The trunk is the visible sequence of verified predicate anchors.

---

# Trunk Rules

## Rule T3.1 — Trunk Source

The trunk comes only from verified Stage 2A predicate anchors.

No non-anchor token may create trunk structure.

---

## Rule T3.2 — Trunk Order

Trunk order follows source order.

Source order is inherited from Stage 1 and Stage 2A.

No downstream stage may reorder trunk anchors.

---

## Rule T3.3 — One Trunk Row Per Anchor

Each predicate anchor produces exactly one trunk row.

Therefore:

```text
predicate anchors = trunk rows
```

For 1corintios:

```text
1027 predicate anchors = 1027 trunk rows
```

---

## Rule T3.4 — Anchor Permanence

Every predicate anchor remains permanent in the trunk.

Stage 3 may add markers to an anchor row.

Stage 3 may not:

- remove anchors,
- merge anchors,
- split anchors,
- reinterpret anchors,
- collapse anchors.

---

# Subject Change [S]

## Formal Definition

At Stage 3, `[S]` marks a mechanical subject-signature change between consecutive predicate anchors.

The initial subject_signature is derived only from Greek finite verbal morphology.

The initial subject_signature is:

```text
person + number
```

Examples:

```text
1S
2P
3S
3P
```

---

# Subject Change Rules

## Rule S3.1 — Subject Signature Source

The subject_signature comes only from the finite verb morphology inherited by the predicate anchor.

The system may use:

- person_code,
- number_code.

The system may not use:

- inferred subject nouns,
- pronoun resolution,
- English translation subject,
- semantic role guessing,
- theological interpretation.

---

## Rule S3.2 — First Anchor

The first predicate anchor in a book has no previous subject_signature.

Its subject_change_marker is blank unless a later rule defines a book-opening marker.

---

## Rule S3.3 — Consecutive Comparison

For each predicate anchor after the first, compare:

```text
previous subject_signature
current subject_signature
```

If they differ, mark:

```text
[S]
```

If they match, leave subject_change_marker blank.

---

## Rule S3.4 — No Subject Resolution

`[S]` does not claim the identity of the subject.

`[S]` only claims that the grammatical person/number signature changed.

Example:

```text
1S → 2P = [S]
3S → 3S = no [S]
3S → 3P = [S]
```

---

## Rule S3.5 — Known Limitation

Because `[S]` initially uses person/number only, it cannot distinguish different subjects with the same person/number.

Example:

```text
3S → 3S
```

may still involve a subject change in the text, but Stage 3 does not infer that.

Such cases must remain unmarked unless a later formally defined rule adds subject-identity mechanics.

---

# Movement Change [M]

## Formal Definition

At Stage 3, `[M]` marks a mechanical movement-signature change between consecutive predicate anchors.

The movement_signature must be derived only from formal anchor data.

The initial movement_signature should be conservative.

Recommended initial movement_signature:

```text
mood
```

Examples:

```text
indicative
subjunctive
imperative
optative
```

---

# Movement Change Rules

## Rule M3.1 — Movement Signature Source

The movement_signature comes only from predicate-anchor morphology.

The initial movement_signature may use:

- mood,
- mood_code.

The system may not use:

- connector meaning,
- discourse interpretation,
- semantic topic shifts,
- paragraph headings,
- English translation structure,
- theological categories.

---

## Rule M3.2 — First Anchor

The first predicate anchor in a book has no previous movement_signature.

Its movement_marker is blank unless a later rule defines a book-opening marker.

---

## Rule M3.3 — Consecutive Comparison

For each predicate anchor after the first, compare:

```text
previous movement_signature
current movement_signature
```

If they differ, mark:

```text
[M]
```

If they match, leave movement_marker blank.

---

## Rule M3.4 — No Semantic Movement Claims

`[M]` does not claim:

- topic change,
- argument shift,
- rhetorical move,
- theological development,
- new section,
- new unit.

At Stage 3, `[M]` only claims that the formal movement_signature changed.

---

## Rule M3.5 — Known Limitation

A real textual movement may occur without a mood change.

Stage 3 does not infer such movement.

If a later rule expands movement_signature beyond mood, that rule must be formally documented and audited.

---

# Combined Marker Rules

## Rule C3.1 — Both Markers May Occur

A predicate anchor may receive both markers:

```text
[S] [M]
```

if both the subject_signature and movement_signature changed from the previous anchor.

---

## Rule C3.2 — Independent Evaluation

`[S]` and `[M]` are evaluated independently.

A subject change does not imply movement change.

A movement change does not imply subject change.

---

# Stage 3 Does NOT Use Connectors

## Connector Prohibition

Connectors are not part of Stage 3.

Stage 3 must not use:

- conjunctions,
- subordinators,
- discourse particles,
- connective meaning,
- A/B connector relationships.

Connectors are delayed until the later connector + label stage.

---

# Stage 3 Does NOT Assign Labels

## Label Prohibition

Stage 3 must not assign labels.

Labels belong to the later connector + label stage.

Stage 3 only produces trunk rows and mechanical markers.

---

# Stage 3 Does NOT Form Units

## Unit Prohibition

Stage 3 must not form:

- patterns,
- units,
- sections,
- titles.

Those belong to later stages.

---

# Required Output Location

## Dataset Path

Primary dataset path:

```text
datasets/trunk/<book>.jsonl
```

Example:

```text
datasets/trunk/1corintios.jsonl
```

---

# Validation Requirements

## Stage 3 Validation

The Stage 3 validator must verify:

- predicate anchor count equals trunk row count,
- every predicate anchor appears exactly once,
- no duplicate trunk rows exist,
- trunk order matches predicate-anchor order,
- every row has subject_signature,
- every row has movement_signature,
- `[S]` appears only where subject_signature changed,
- `[M]` appears only where movement_signature changed,
- no connector data appears,
- no labels appear,
- no unit claims appear.

---

# Failure Conditions

## Stage 3 Fails If

- Stage 2A validation has not passed,
- predicate anchor count does not match trunk row count,
- predicate anchors are missing,
- predicate anchors are duplicated,
- predicate anchors are reordered,
- `[S]` is marked without a subject_signature change,
- `[S]` is missing where a subject_signature change exists,
- `[M]` is marked without a movement_signature change,
- `[M]` is missing where a movement_signature change exists,
- connector data is introduced,
- labels are introduced,
- unit claims are introduced.

---

# Truthfulness Rule

## Required Language

At Stage 3, the system may say:

```text
subject-signature change
movement-signature change
trunk row
anchor skeleton
```

The system must not say:

```text
identified subject
full movement unit
connector relationship
labeled section
final unit
```

unless those have been formally defined and validated in later stages.

---

# Implementation Target

## Builder Script

```bash
python3 scripts/stage3/build_trunk_subject_movement.py 1corintios
```

Expected output:

```text
datasets/trunk/1corintios.jsonl
```

---

## Validation Script

```bash
python3 scripts/stage3/validate_trunk_subject_movement.py 1corintios
```

Required result:

```text
PREDICATE_ANCHORS: 1027
TRUNK_ROWS: 1027
STATUS: PASS
```

---

# Final Definition

## Safe Formal Definition

At Stage 3:

> trunk is the ordered predicate-anchor skeleton.

`[S]` means:

> the person/number subject_signature changed from the previous predicate anchor.

`[M]` means:

> the formal movement_signature changed from the previous predicate anchor.

These definitions are mechanical, reproducible, and auditable.

They do not yet claim full subject identity, full movement units, connectors, labels, patterns, units, or titles.
