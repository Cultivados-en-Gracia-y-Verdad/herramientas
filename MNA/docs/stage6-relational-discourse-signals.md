# MNA Stage 6 — Relational Discourse Signal Observation

## Core Definition

Stage 6 observes surviving non-dependency relational discourse signals inside independent-clause candidacy environments.

## Purpose

Stage 6 preserves observable discourse-flow information that remains after dependency-pressure filtering and Stage 5 candidacy auditing.

Stage 6 does not remove dependency. That work belongs upstream.

Stage 6 does not establish hierarchy. It observes relational discourse signals that remain visible inside surviving independent-clause candidacy environments.

## Input

Primary input:

```text
datasets/stage5/<book>/trunk-candidacy-environments.jsonl
```

Stage 6 consumes Stage 5 environments because Stage 5 has already preserved surviving independent-clause candidacy rows with audit-safe metadata.

## Output

Primary output:

```text
datasets/stage6/<book>/relational-discourse-signals.jsonl
```

## Initial Row Fields

```json
{
  "record_type": "relational_discourse_signal",
  "book": "",
  "chapter": 0,
  "verse": 0,
  "reference": "",
  "unit_id": "",
  "clause_id": "",
  "finite_verb": "",
  "connector_surface": "",
  "connector_lemma": "",
  "signal_category": "",
  "signal_status": "",
  "source_stage5_environment": "",
  "notes": ""
}
```

## Approved Signal Categories

Stage 6 may use only these initial categories:

```text
continuity_signal
development_signal
contrast_signal
inferential_signal
explanatory_signal
result_signal
alternative_signal
emphasis_signal
unknown_signal
no_connector_signal
```

## Signal Status Values

```text
SIGNAL_OBSERVED
NO_CONNECTOR_OBSERVED
SIGNAL_PRESENT_CATEGORY_UNRESOLVED
```

## Allowed Claims

Stage 6 may claim:

- a connector is present in a surviving independent-clause candidacy environment;
- a connector carries an observable non-dependency relational signal category;
- no connector signal is observed;
- a connector signal is present but unresolved by the current approved signal vocabulary.

## Forbidden Claims

Stage 6 must not claim:

- dependency removal;
- parent/child relationship;
- governing clause;
- subordinate relation;
- final hierarchy;
- final discourse structure;
- theological meaning;
- rhetorical outline;
- final movement label;
- final section boundary.

## Forbidden Field Names

Stage 6 datasets and audits must not introduce fields such as:

```text
parent_clause
child_clause
governing_clause
subordinate_clause
structural_parent
structural_child
hierarchy
attachment_target
```

## Initial Connector Signal Mapping

This initial mapping is intentionally conservative and observational.

```text
καί   -> continuity_signal
δέ    -> development_signal
γάρ   -> explanatory_signal
οὖν   -> inferential_signal
ἀλλά  -> contrast_signal
ἀλλ’  -> contrast_signal
ἤ     -> alternative_signal
τε    -> continuity_signal
```

Unmapped connectors must be assigned:

```text
unknown_signal
```

unless there is no connector, in which case:

```text
no_connector_signal
```

## Audit Philosophy

Stage 6 validation must protect against conceptual drift.

Initial audits must ensure:

- every row links back to a Stage 5 source row;
- every signal category is approved;
- every signal status is approved;
- no forbidden hierarchy/dependency fields appear;
- no Stage 6 row claims dependency removal;
- no Stage 6 row claims final structure.

## Summary

Stage 6 preserves relational discourse signal observations without granting them structural authority.
