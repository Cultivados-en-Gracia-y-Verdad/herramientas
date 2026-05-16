# Predicate Anchors Defined

## Purpose

This document defines the formal mechanics for Stage 2A predicate anchors in the MNA system.

The purpose of Stage 2A is:

- deterministic extraction,
- reproducible anchor generation,
- stable structural coordinates,
- source-bound mechanics,
- auditability.

Stage 2A intentionally avoids:

- full predicate spans,
- attachment theory,
- clause interpretation,
- semantic relationships,
- connector structure,
- implied syntax.

# Foundational Principle

## Predicate Anchor

A predicate anchor is:

> one verified finite verb inherited directly from Stage 1.

This is the only valid Stage 2A definition.

# Stage Relationship

## Dependency

Stage 2A depends entirely on verified Stage 1 finite verbs.

If Stage 1 has not passed verification for a book, Stage 2A may not run.

# Core Rule Set

## Rule PA.1 — Anchor Source

Predicate anchors may only originate from verified Stage 1 finite verbs.

No other source may create predicate anchors.

## Rule PA.2 — One-to-One Relationship

Each verified finite verb produces exactly one predicate anchor.

Therefore:

finite verbs = predicate anchors

Example:

1corintios

1027 finite verbs

1027 predicate anchors

## Rule PA.3 — No Implied Anchors

If a verb is implied but not present as a verified finite MorphGNT token, no predicate anchor exists.

## Rule PA.4 — No Nonfinite Anchors

The following never create predicate anchors:

- participles,
- infinitives,
- verbal adjectives,
- implied copulas,
- semantic verbal ideas.

Only verified finite verbs create predicate anchors.

## Rule PA.5 — No Translation Anchors

Translations may not create predicate anchors.

This includes:

- NBLA,
- English translations,
- glosses,
- paraphrases,
- inferred structures.

Predicate anchors are Greek-source-bound.

## Rule PA.6 — Anchor Permanence

Once created, a predicate anchor is permanent.

No downstream stage may:

- remove it,
- merge it,
- collapse it,
- reinterpret it,
- absorb it into another anchor.

Predicate anchors are immutable structural coordinates.

# Predicate Anchor Identity

## Required Identity

Each predicate anchor must have a stable unique identifier.

Recommended format:

<book>-<chapter>-<verse>-pa-<token_index>

Example:

1corintios-1-4-pa-1

The identifier must remain stable across all downstream stages.

# Predicate Anchor Output

## Required Fields

Each predicate anchor record must contain:

- predicate_anchor_id,
- book,
- chapter,
- verse,
- reference,
- source_line_number,
- token_index_in_verse,
- greek_surface,
- greek_clean,
- lemma,
- morphology,
- mood,
- person,
- number,
- stage1_source_reference,
- anchor_status.

# Anchor Status

## Initial Status

Initial anchor_status:

finite_anchor

No additional structural claims are permitted at this stage.

# Stage Limits

## Stage 2A Does NOT Determine

Stage 2A does not determine:

- predicate spans,
- predicate boundaries,
- subjects,
- objects,
- complements,
- clause structure,
- connector relationships,
- semantic roles,
- discourse structure,
- attachment relationships.

Stage 2A only establishes stable predicate anchors.

# Mechanical Characteristics

## Predicate Anchors Must Be

- enumerable,
- reproducible,
- auditable,
- source-bound,
- deterministic,
- immutable.

# Required Output Location

## Dataset Path

Primary dataset path:

datasets/predicate-anchors/<book>.jsonl

Example:

datasets/predicate-anchors/1corintios.jsonl

# Validation Requirements

## Stage 2A Validation

The validator must verify:

- every Stage 1 finite verb appears exactly once,
- finite verb count equals predicate anchor count,
- no duplicate predicate anchors exist,
- no nonfinite token became a predicate anchor,
- no unresolved token became a predicate anchor,
- all predicate_anchor_id values are unique,
- all predicate_anchor_id values are stable.

# Failure Conditions

## Stage 2A Fails If

- Stage 1 verification failed,
- finite verb counts do not match anchor counts,
- duplicate anchors exist,
- nonfinite forms became anchors,
- unresolved forms became anchors,
- unstable identifiers are generated,
- downstream stages modified anchors.

# Ledger Relationship

## Dependency Chain

Predicate anchors inherit authority from:

Stage 1 verification ledger

If Stage 1 changes:

- predicate anchors must be regenerated,
- downstream references must be revalidated.

# Truthfulness Rule

## Required Language

At Stage 2A the system must say:

predicate anchors

not:

full predicates

unless later stages formally define and audit predicate boundaries.

# Architectural Purpose

## Why Predicate Anchors Exist

Predicate anchors create:

- permanent structural coordinates,
- stable downstream references,
- reproducible movement tracking,
- reproducible continuity analysis,
- reproducible structural segmentation.

This allows later stages to evolve without corrupting the foundational verbal layer.

# Example

## 1corintios

Verified Stage 1:

1309 verbal tokens

1027 finite verbs

182 participles

100 infinitives

0 unresolved

PASS

Therefore:

1027 predicate anchors

This relationship must remain invariant.

# Final Definition

## Safe Formal Definition

At the current stage of MNA:

> a predicate anchor is one verified finite verb inherited directly from Stage 1.

This definition is:

- objective,
- reproducible,
- auditable,
- deterministic,
- mechanically constrained,
- source-bound.