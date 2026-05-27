# Predicates Defined

## Purpose

This document defines the formal predicate-anchor mechanics for the MNA system.

The purpose of this stage is not interpretation.

The purpose is:

- reproducible extraction,
- deterministic structure,
- source-bound mechanics,
- visible auditability,
- elimination of hidden assumptions.

Every claim made by this stage must be mechanically reproducible from the source text.

No invisible linguistic intuition is permitted.

# Foundational Principle

## Stage Separation

MNA separates:

1. finite verbal extraction,
2. predicate-anchor extraction,
3. predicate-boundary assignment.

These are not the same operation.

They must not be merged conceptually or mechanically.

# Stage 1

## Finite Verbs

Stage 1 establishes:

- finite verbal tokens,
- finite verbal verification,
- verbal accounting,
- finite verbal reproducibility.

Stage 1 is the exclusive source for Stage 2A predicate anchors.

No later stage may redefine or reinterpret Stage 1 finite verbs.

# Stage 1 Verified Example

## 1corintios

Verified from:

SOURCES/MorphGNT/1corintios-morphgnt.txt

Verified counts:

- 1309 verbal tokens,
- 1027 finite verbs,
- 182 participles,
- 100 infinitives,
- 0 unresolved verbal forms,
- PASS.

Forward extraction and reverse verification both produce:

1027 finite verbs

This verified finite-verb layer becomes the permanent anchor source for Stage 2A.

# Stage 2A

## Predicate Anchors

Stage 2A does NOT extract full predicates.

Stage 2A extracts:

predicate anchors

A predicate anchor is:

> one verified finite verb inherited directly from Stage 1.

This is the only currently valid formal definition.

# Predicate Anchor Rules

## Rule P2A.1 — Anchor Source

Predicate anchors come exclusively from verified Stage 1 finite verbs.

No other source may create predicate anchors.

## Rule P2A.2 — One Anchor Per Finite Verb

Each verified finite verb produces exactly one predicate anchor.

Therefore:

finite verbs = predicate anchors

For 1corintios:

1027 finite verbs = 1027 predicate anchors

## Rule P2A.3 — Anchor Permanence

Once a predicate anchor is created, it is permanent.

No downstream stage may:

- remove it,
- merge it,
- collapse it,
- reinterpret it,
- absorb it into another anchor.

Predicate anchors are immutable downstream reference points.

## Rule P2A.4 — No Implied Anchors

If a verb is implied but not present as a finite MorphGNT token, no predicate anchor exists.

Implied verbs are not mechanically extractable at this stage.

## Rule P2A.5 — No Nonfinite Anchors

The following never create predicate anchors:

- participles,
- infinitives,
- verbal adjectives,
- implied copulas,
- implied verbal ideas.

Only verified finite verbs create predicate anchors.

## Rule P2A.6 — No Translation Anchors

Translations may not create predicate anchors.

This includes:

- NBLA,
- English translations,
- glosses,
- paraphrases,
- inferred verbal structures.

Predicate anchors are source-bound to the Greek finite verbal layer.

## Rule P2A.7 — Failure Condition

If Stage 1 verification has not passed for a book, Stage 2A may not run.

# Predicate Anchor Output

## Required Fields

Each predicate anchor must contain:

- book,
- chapter,
- verse,
- predicate_anchor_id,
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

Initial anchor_status:

finite_anchor

# Predicate Boundaries

## Not Yet Mechanically Defined

Predicate anchors are not the same thing as predicate boundaries.

Stage 2A does not determine:

- full predicate spans,
- subjects,
- objects,
- complements,
- clause boundaries,
- connector relationships,
- semantic roles,
- discourse structure.

Those belong to later stages.

No full predicate span may be claimed until formal boundary rules exist.

# Stage 2B

## Predicate Boundary Mechanics

Stage 2B is not yet finalized.

Stage 2B will eventually determine:

- attachment rules,
- boundary rules,
- interruption rules,
- continuity rules,
- coordination rules,
- embedding rules,
- quotation rules,
- parenthetical rules,
- unassigned-token rules.

These rules must be:

- deterministic,
- auditable,
- reproducible,
- source-bound.

# Boundary Safety Principle

## Conservative Default

Until boundary rules are formally verified:

- each predicate anchor initially contains only itself,
- unattached material remains unassigned,
- ambiguity remains visible,
- uncertainty is recorded instead of resolved.

The system must prefer under-attachment over over-attachment.

# Token Assignment Principle

## No Silent Attachment

No token may be attached to a predicate boundary unless:

- the attachment rule exists,
- the rule has a stable rule_id,
- the rule is reproducible,
- the attachment is auditable.

Every assignment must remain traceable.

# Unassigned Material

## Explicit Visibility

If material has not yet been assigned by a verified rule, it must remain explicitly unassigned.

The system must never silently absorb material into a predicate span.

# Non-Negotiable Constraints

## The System MUST NOT:

- invent implied words,
- assume omitted subjects,
- infer theology,
- merge structures by interpretation,
- create invisible syntax,
- rely on translation structure,
- resolve ambiguity silently,
- reinterpret Stage 1 anchors,
- create boundaries from intuition,
- attach tokens without a rule_id,
- hide unresolved states.

# Audit Requirements

## Stage 2A Audit

The Stage 2A audit must verify:

- finite verb count equals predicate anchor count,
- every Stage 1 finite verb appears exactly once,
- no duplicate anchors exist,
- no nonfinite form became an anchor,
- no unresolved form became an anchor.

## Stage 2B Audit

The Stage 2B audit must verify:

- every assigned token has a rule_id,
- every unassigned token is explicitly marked,
- no boundary crosses a hard boundary without a rule,
- no boundary was created from translation structure,
- no Stage 2A anchor was modified downstream.

# Current Reproducibility Status

## Currently Reproducible

The following are currently reproducible:

- finite verb extraction,
- finite verb verification,
- finite verbal accounting,
- predicate-anchor extraction,
- predicate-anchor counts.

## Not Yet Reproducible

The following are not yet formally reproducible:

- full predicate spans,
- subject assignment,
- object assignment,
- complement assignment,
- connector relationships,
- clause structures,
- semantic relationships.

These must not be claimed prematurely.

# Required Language

## Truthfulness Rule

Until Stage 2B is formally verified, the system must say:

predicate anchors

not:

full predicates

unless a full predicate boundary has been mechanically assigned and audited.

# Stage 2A Implementation Target

## Builder Script

python3 scripts/stage2/build_predicate_anchors.py 1corintios

Expected output:

datasets/predicate-anchors/1corintios.jsonl

## Validation Script

python3 scripts/stage2/validate_predicate_anchors.py 1corintios

Required result:

FINITE_VERBS: 1027

PREDICATE_ANCHORS: 1027

STATUS: PASS

# Final Definition

## Safe Formal Definition

At the current stage of MNA:

> a predicate anchor is one verified finite verb inherited directly from Stage 1.

This definition is:

- objective,
- reproducible,
- auditable,
- mechanically constrained,
- source-bound.

## Unsafe Claim

At the current stage of MNA:

> full predicate spans are not yet mechanically defined.

No system may claim full predicate boundaries until formal Stage 2B boundary rules exist and are audited.

Rewrote the entire file into a stricter formal specification focused on:

- immutable Stage 1 anchors,
- deterministic Stage 2A mechanics,
- explicit prohibition of hidden interpretation,
- separation of anchors vs boundaries,
- auditability and traceability,
- downstream immutability,
- conservative attachment philosophy.