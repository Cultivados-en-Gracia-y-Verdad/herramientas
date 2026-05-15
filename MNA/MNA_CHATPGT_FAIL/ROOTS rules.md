# ROOTS — Formal System Rules

## 1. General Foundation

### 1.1

ROOTS is a mechanical structural observation system for biblical text.

### 1.2

ROOTS exists to expose observable grammatical structure.

### 1.3

ROOTS does not interpret, theologize, harmonize, deduce doctrine, infer author psychology, assign rhetorical intent, or apply the text.

### 1.4

ROOTS states what can be observed from the text itself.

### 1.5

The Greek text governs clauses, connectors, relationships, subordination, coordination, and structural continuity.

### 1.6

The NBLA provides readable Spanish surface, but the NBLA does not govern structure.

---

## 2. Central Principle

### 2.1

A Greek finite verb establishes the existence of a finite clause.

### 2.2

Every Greek finite clause must remain visible in ROOTS.

### 2.3

A clause does not disappear because the NBLA reorganizes, compresses, transforms, smooths, or omits explicit verbal surface.

### 2.4

ROOTS may show that a clause exists without forcing a final interpretive conclusion about its broader meaning.

---

## 3. Clause Relationships

### 3.1

A connector does not belong to a clause.

### 3.2

A connector establishes a relationship.

### 3.3

ROOTS operates by:

```text
Connector + B → search for A
```

### 3.4

Clause B is the clause introduced, governed, or affected by the connector.

### 3.5

Clause A is the clause to which B is related.

### 3.6

ROOTS may identify B with greater certainty than A.

### 3.7

When A cannot be established mechanically with certainty, ROOTS must state the facts and may list possible A-clause candidates without forcing a conclusion.

------

## 4. Relationship Certainty

### 4.1

ROOTS distinguishes between established facts and possible attachments.

### 4.2

Established facts may include:

- the connector exists
- the connector is clause-level
- the connector governs or affects B
- the connector has a grammatical relationship type
- the connector has a direction
- the connector has a hierarchy effect

### 4.3

Possible attachments may include:

- nearest previous finite clause
- nearest following finite clause
- previous context clause
- structurally compatible nearby clause

### 4.4

ROOTS must not present a possible attachment as certain unless the grammar mechanically establishes it.

------

## 5. Clause-Level Connector Rule

### 5.1

ROOTS tracks connectors that participate in finite-clause relationships.

### 5.2

ROOTS does not track connectors merely because they appear in the text.

### 5.3

Excluded connectors include those functioning only at the level of:

- noun coordination
- phrase coordination
- list coordination
- apposition
- non-clausal joining

### 5.4

Coordinating connectors are retained when they connect finite clauses, because they provide real grammatical relationship information.

------

## 6. Approved Relationship Types

### 6.1

ROOTS may only use controlled grammatical relationship labels.

### 6.2

Approved relationship types are:

```
reason
content
purpose
result
condition
coordination
contrast
inference
comparison
```

### 6.3

These labels are allowed only when they are:

- connector-triggered
- clause-level
- grammatically observable
- structurally constrained

### 6.4

ROOTS must prefer minimal grammatical categories over nuanced discourse categories.

------

## 7. Forbidden Relationship Types

### 7.1

ROOTS must not use categories that infer hidden meaning, rhetorical intent, emotion, theology, application, or author psychology.

### 7.2

Forbidden categories include:

```
encouragement
warning
rebuke
comfort
persuasion
motivation
emphasis
application
doctrine
emotion
theme
author_intent
rhetorical_force
spiritual_meaning
```

### 7.3

If a label cannot be mechanically and consistently derived from explicit grammatical triggers, it must not be used.

------

## 8. Direction

### 8.1

Relationship direction must be controlled.

### 8.2

Approved direction values are:

```
backward
forward
parallel
```

### 8.3

Direction describes how the connector grammatically points in relation to nearby clauses.

### 8.4

Direction does not establish interpretation.

------

## 9. Hierarchy

### 9.1

Hierarchy describes structural relationship, not importance.

### 9.2

Approved hierarchy values are:

```
same_level
subordinate
```

### 9.3

Subordinate means B is grammatically dependent under A.

### 9.4

Same-level means B is grammatically coordinated, explanatory, contrastive, inferential, or otherwise non-subordinate in hierarchy.

### 9.5

Hierarchy must not imply that one clause is more important than another.

------

## 10. Indentation

### 10.1

Indentation represents grammatical hierarchy.

### 10.2

Indentation does not merely represent connector presence.

### 10.3

Subordinate clauses indent.

### 10.4

Coordinated clauses remain at the same level.

### 10.5

Backward explanatory connectors such as γάρ normally do not create indentation.

------

## 11. Mechanical Reconstruction

### 11.1

ROOTS may restore implied material only when Greek structure requires it and the NBLA suppresses it.

### 11.2

Restoration must be minimal.

### 11.3

ROOTS must not paraphrase, explain, interpret, or stylistically improve the text.

### 11.4

All restored material must be visibly marked.

------

## 12. Visual Marking

### 12.1

Explicit connectors are marked with parentheses.

```
(cn1: porque — ὅτι)
```

### 12.2

Implied or supplied connectors are marked with brackets.

```
[cn1: porque — ὅτι]
```

### 12.3

Explicit verbs are marked with double equals.

```
==dijo==
```

### 12.4

Implied or supplied verbs are marked with brackets inside double equals.

```
==[dijo]==
```

------

## 13. Spanish Output

### 13.1

ROOTS development rules may be written in English.

### 13.2

ROOTS user-facing output must be in Spanish.

### 13.3

Relationship descriptions used in Spanish output must remain controlled, minimal, and grammatical.

### 13.4

Spanish output must not introduce interpretation.

------

## 14. Relationship Descriptions

### 14.1

Relationship descriptions must explain only the grammatical relationship.

### 14.2

Approved Spanish descriptions may include:

```
B da razón gramatical para A.
B presenta contenido relacionado con A.
B expresa propósito o resultado relacionado con A.
B establece condición relacionada con A.
B se coordina gramaticalmente con A.
B contrasta gramaticalmente con A.
B presenta inferencia gramatical desde A.
B expresa comparación gramatical con A.
```

### 14.3

Descriptions must not mention motive, emotion, theology, application, or rhetorical effect.

------

## 15. Objectivity Rule

### 15.1

Every structural claim must answer:

```
What observable grammatical evidence triggered this?
```

### 15.2

If the evidence is not mechanically observable, ROOTS must not make the claim.

### 15.3

ROOTS observes what is present in the grammar.

### 15.4

ROOTS does not infer what is hidden.

------

## 16. Student / Interpreter Boundary

### 16.1

ROOTS provides grammatical facts and structural observations.

### 16.2

ROOTS may expose possible A-clause candidates.

### 16.3

ROOTS must not force interpretive conclusions.

### 16.4

Interpretation, synthesis, and application belong to the interpreter.

------

## 17. Implementation Rule

### 17.1

The connector JSON must comply with this rules file.

### 17.2

The connector JSON must use controlled enum values, not free-form interpretive prose.

### 17.3

If a connector category cannot comply with these rules, it must be excluded or marked unresolved.

### 17.4

The engine must prefer under-claiming over over-claiming.