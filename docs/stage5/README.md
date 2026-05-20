# Stage 5 — True Trunk Extraction

## Purpose

Stage 5 extracts stable surviving trunk structures from Stage 4 audited clause relationships.

Stage 5 is mechanical infrastructure. It does not replace ROOTS. It prepares structural material for ROOTS by determining what survives as trunk structure under explicit rules.

## Stage 4 vs Stage 5

Stage 4 is independency testing.

Stage 5 is survivability extraction.

Stage 4 asks:

```text
Can this clause stand independently?
```

Stage 5 asks:

```text
Does this structure survive in the trunk?
```

These are not the same question.

## Non-Goals

Stage 5 must not perform semantic importance ranking.

Stage 5 must not decide:

- main idea
- author emphasis
- theological center
- rhetorical climax
- discourse prominence
- semantic priority
- reviewer preference

Structural survival must never be confused with semantic importance.

## Governing Principles

1. A structure survives only by explicit mechanical rule.
2. Dependency does not automatically mean removability.
3. Survival is structural, not semantic.
4. False deletion is more dangerous than temporary over-preservation.
5. When certainty is insufficient, preserve and warn rather than destroy.
6. Stage 5 must remain auditable and reproducible.

## Input

Stage 5 consumes Stage 4 outputs, including:

- clause identifiers
- finite-verb anchors
- dependency classifications
- connector metadata
- conditional-unit metadata
- WARN records
- FLAG records
- audit provenance

## Output

Stage 5 emits trunk survivability records, including:

- source reference
- clause or unit id
- survival decision
- survival rule id
- preservation reason
- removal reason, when removed
- warnings, when certainty is insufficient

Stage 5 output must not include interpretive summaries.

## Current Fixed Policy

Conditional structures introduced by:

```text
εἰ
ἐὰν
```

are treated as preserved conditional logical units when the protasis and apodosis are structurally bound.

The system does not automatically prioritize the apodosis or discard the protasis.

## Open Warning-Sensitive Connectors

The following remain active refinement areas:

```text
ὅτι
ἵνα
ὡς
καθὼς
```

They must not be forced into certainty prematurely.

## Relationship to Stage 6

Stage 5 establishes stable survivability before Stage 6 maps connector relationships on the surviving structure.

Stage 6 may expose weaknesses in Stage 5, but Stage 6 must not silently redefine Stage 5 behavior.
