# Connectors + Labels Defined

## Purpose

This document defines Stage 4 of the MNA system.

Stage 4 handles connector and label data as an overlay tied to predicate anchors.

Stage 4 does not create structure.

Stage 4 does not reinterpret structure.

Stage 4 does not define sections.

Stage 4 does not define units.

Stage 4 does not define titles.

---

# Foundational Correction

## Connectors Are Not Trunk Sections

Stage 3 produces trunk rows from predicate anchors.

Stage 3 does not produce final trunk sections.

Therefore, Stage 4 must not speak of connectors as connecting trunk sections.

That would overclaim structure.

Connectors are handled as local relational data tied to predicate-anchor environments.

---

# Stage Relationship

## Stage 4 Dependency

Stage 4 is tied primarily to Stage 2A predicate anchors.

Stage 4 may reference Stage 3 trunk order, but Stage 4 does not depend on Stage 3 for section structure.

Stage 4 must not change:

- Stage 1 finite verbs,
- Stage 2A predicate anchors,
- Stage 3 trunk rows,
- Stage 3 subject-signature markers,
- Stage 3 provisional movement signals.

---

# Stage 4 Scope

## What Stage 4 Does

Stage 4 identifies connector data and attaches it to the nearest relevant predicate-anchor environment according to formal rules.

Stage 4 may record:

- connector token,
- connector lemma,
- connector location,
- connector type,
- connector function,
- connector relationship candidate,
- affected predicate anchor or anchor range,
- rule_id,
- status.

---

# What Stage 4 Does NOT Do

## Prohibited Actions

Stage 4 must not:

- create predicate anchors,
- remove predicate anchors,
- merge predicate anchors,
- reorder predicate anchors,
- redefine trunk rows,
- create trunk sections,
- redefine `[S]`,
- redefine movement signals,
- create patterns,
- create units,
- create titles,
- infer theology,
- rely on translation structure.

---

# Connector Overall Purpose

## Definition

A connector is a visible source-token that signals a local relationship in the text.

At Stage 4, connectors are not structural generators.

They are relational signals.

They may help explain how existing predicate-anchor environments relate, but they do not create those environments.

---

# Connector Source

## Source Rule

Connector detection must come from Greek source data.

The system may use:

- Greek token,
- lemma,
- morphology/tagging,
- source position,
- predicate-anchor order.

The system may not use:

- English translation connectors,
- Spanish translation connectors,
- paraphrase wording,
- theological assumptions,
- paragraph headings,
- manual titles.

---

# Connector Environment

## Definition

A connector environment is the local source context around a connector token.

The connector environment may include:

- the connector token,
- its source reference,
- its source token index,
- nearest previous predicate anchor,
- nearest following predicate anchor,
- current predicate anchor if applicable.

The connector environment is not a section.

The connector environment is not a unit.

The connector environment is not a full clause unless later rules formally define that claim.

---

# Connector Type

## Definition

connector_type identifies the formal class of connector.

Examples may include:

- coordinating,
- subordinating,
- causal,
- explanatory,
- adversative,
- conditional,
- inferential,
- temporal,
- comparative,
- purpose/result.

The type must be assigned by rule, not by intuition.

If connector_type cannot be assigned mechanically, it must be marked:

```text
unresolved
```

---

# Connector Function

## Definition

connector_function describes the local operation of the connector.

Examples may include:

- continues,
- contrasts,
- explains,
- grounds,
- qualifies,
- introduces condition,
- introduces purpose,
- introduces result.

connector_function must remain local and source-bound.

It must not create units or titles.

If connector_function cannot be assigned mechanically, it must be marked:

```text
unresolved
```

---

# Connector Relationship Candidate

## Definition

connector_relationship_candidate records the possible local relationship suggested by the connector.

At Stage 4, this is a candidate relationship, not a final structural claim.

A connector relationship candidate may include:

- connector_anchor_id,
- previous_anchor_id,
- next_anchor_id,
- possible_left_anchor_range,
- possible_right_anchor_range,
- relationship_status.

Relationship status may be:

```text
observed
candidate
verified
unresolved
```

At initial Stage 4, relationship_status should normally begin as:

```text
candidate
```

unless a formal rule verifies the relationship.

---

# Labels

## Definition

Labels are controlled descriptions assigned after connector data is identified.

Labels must describe observed connector behavior.

Labels must not create structure.

Labels must not create theology.

Labels must not create titles.

Labels must not override Stage 3.

---

# Label Timing

## Rule

Labels may only be assigned after connector data exists.

The system must not assign labels directly from intuition.

A label must be tied to:

- connector token,
- predicate-anchor environment,
- rule_id,
- status.

---

# Connector vs Structure

## Non-Negotiable Rule

Connectors may annotate structure.

Connectors may not create structure.

Connectors may indicate possible relationships.

Connectors may not define final units.

Connectors may not reinterpret previous stages.

---

# Stage 4 Output

## Required Output Fields

A connector-label record should include:

- record_type,
- book,
- chapter,
- verse,
- connector_id,
- connector_surface,
- connector_clean,
- connector_lemma,
- source_line_number,
- token_index_in_verse,
- nearest_previous_predicate_anchor_id,
- nearest_following_predicate_anchor_id,
- connector_type,
- connector_function,
- connector_relationship_candidate,
- label_candidate,
- rule_id,
- status.

---

# Required Output Location

## Dataset Path

Primary dataset path:

```text
datasets/connectors-labels/<book>.jsonl
```

Example:

```text
datasets/connectors-labels/1corintios.jsonl
```

---

# Validation Requirements

## Stage 4 Validator Must Verify

The validator must verify:

- every connector record has a source token,
- every connector record has a stable connector_id,
- every connector record is tied to predicate-anchor environment data,
- no predicate anchors were added,
- no predicate anchors were removed,
- no predicate anchors were reordered,
- no Stage 3 markers were altered,
- every connector_type has a rule_id or unresolved status,
- every connector_function has a rule_id or unresolved status,
- every label_candidate has a rule_id or unresolved status.

---

# Failure Conditions

## Stage 4 Fails If

- connector data modifies previous stages,
- connector data creates sections,
- connector data creates units,
- connector data creates titles,
- connector records lack source evidence,
- connector records lack anchor-environment linkage,
- labels are assigned without connector data,
- labels are assigned without rule_id or unresolved status.

---

# Truthfulness Rule

## Required Language

At Stage 4, the system may say:

```text
connector observed
connector type candidate
connector function candidate
connector relationship candidate
label candidate
```

The system must not say:

```text
unit established
section established
movement proven
title determined
full structure defined
```

unless later stages formally define and validate those claims.

---

# Final Definition

## Safe Formal Definition

At Stage 4:

> connector data is a local relational overlay tied to predicate-anchor environments.

It is not a restructuring mechanism.

It is not a sectioning mechanism.

It is not a unit-forming mechanism.

It is not a title-generating mechanism.

Stage 4 must remain descriptive, local, auditable, and subordinate to the verified anchor layer.
