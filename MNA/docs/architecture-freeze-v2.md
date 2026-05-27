# MNA Architecture Freeze v2

## Status

This document freezes the corrected architectural direction for MNA.

No further structural scripting should proceed until all earlier documentation and terminology are reconciled with this freeze.

This freeze exists to prevent interpretive drift.

---

# Core Corrections

## Correction 1 — Predicate Anchor Is Not An Independent Clause

A predicate anchor is:

> one verified finite verb inherited from Stage 1.

A predicate anchor is NOT:

- an independent clause,
- a trunk section,
- a discourse unit,
- a final predicate span.

A predicate anchor is only:

```text
finite-clause center candidate
```

---

# Correction 2 — Trunk Is Independent-Clause Structure

The real trunk is:

```text
independent-clause structure
```

not:

```text
all predicate anchors
```

not:

```text
all finite clauses
```

not:

```text
all finite verbs
```

Therefore:

- the current Stage 3 output is NOT final trunk,
- the current Stage 3 output is only an anchor skeleton,
- trunk extraction requires independent/dependent determination.

---

# Correction 3 — Connectors Do Not Create Structure

Connectors are not primary structure generators.

Connectors:

- may signal relationships,
- may signal dependency,
- may signal continuation,
- may signal qualification,
- may signal grounding.

But connectors do NOT:

- create trunk,
- create units,
- create sections,
- create titles.

---

# Correction 4 — Independent-Clause Recognition Must Not Depend Primarily On Connectors

This is a critical architectural constraint.

Connector-first parsing leads rapidly to:

- interpretive drift,
- discourse assumptions,
- unstable restructuring,
- subjective dependency assignment.

Therefore:

```text
independency must be established before connector interpretation dominates the system
```

This means:

```text
predicate completeness and clausal independency testing must precede full connector dependency logic
```

---

# Linguistic Validation

## Traditional Grammar Alignment

The corrected architecture aligns more closely with traditional grammar and linguistic practice.

Validated principles:

```text
finite verb ≠ independent clause
```

```text
finite verb = clause center candidate
```

```text
dependent clauses may still contain finite verbs
```

```text
independent clauses must be distinguished from dependent clauses
```

```text
connectors may signal dependency but do not fully determine dependency
```

---

# Corrected Architectural Direction

## Frozen Direction

The corrected architecture should now proceed conceptually as:

```text
Stage 1  finite verbs
Stage 2  predicate anchors
Stage 3  finite-clause candidates
Stage 4  independency testing / predicate completeness
Stage 5  trunk extraction (independent clauses only)
Stage 6  connector relationships
Stage 7  [S] + [M]
Stage 8  labels / patterns / units
Stage 9  titles
```

This sequence is still provisional and may require refinement before implementation.

No additional scripting should proceed until these definitions are stabilized.

---

# Current Dataset Status

## What Remains Valid

The following remain valid and should NOT be deleted:

```text
Stage 1 finite verbs
Stage 2 predicate anchors
```

Reason:

These layers only establish:

- finite verbal extraction,
- predicate-anchor stabilization,
- reproducible structural coordinates.

These remain objective and mechanically valid.

---

# Current Stage 3 Reclassification

## Important Reclassification

The current Stage 3 dataset previously called:

```text
trunk
```

must now be understood as:

```text
anchor skeleton
```

or:

```text
ordered predicate-anchor sequence
```

It is NOT final trunk.

It does NOT yet establish:

- independent clauses,
- dependency,
- sections,
- units.

---

# [S] and [M] Freeze

## Subject Change

Current `[S]` remains mechanically valid as:

```text
person/number signature change
```

This is still reproducible and auditable.

---

## Movement

Current `[M]` is NOT final movement logic.

Current `[M]` only represents:

```text
provisional movement signal
```

currently derived from:

```text
mood change
```

This must NOT yet carry major structural authority.

---

# Freeze Rule

## Non-Negotiable Constraint

No new structural scripts should be added until:

- all terminology is reconciled,
- all stage definitions are corrected,
- all lower-layer assumptions are frozen,
- dependency theory is formally defined,
- independency testing is formally defined,
- trunk extraction is formally defined.

---

# Anti-Drift Rule

## Required Constraint

The MNA system must never:

- imply certainty beyond mechanical verification,
- silently reinterpret lower layers,
- allow connectors to generate structure,
- collapse provisional signals into final conclusions,
- present heuristic structure as verified structure.

Every layer must remain:

- explicit,
- auditable,
- reproducible,
- mechanically constrained.

---

# Final Freeze Statement

## Current Position

The project is currently in:

```text
architectural correction and stabilization phase
```

not:

```text
final structural implementation phase
```

The purpose of this freeze is to prevent the system from drifting into subjective discourse interpretation before the foundational mechanics are properly defined.
