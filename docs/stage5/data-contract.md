# Stage 5 Data Contract

## Purpose

This document defines the minimum input and output contract for Stage 5 true trunk extraction.

Stage 5 must remain mechanical, reproducible, and auditable.

## Input Contract

Stage 5 reads Stage 4 audited structural material.

The preferred input format is JSONL: one JSON object per structural record.

Minimum expected input fields:

```json
{
  "book": "1corintios",
  "chapter": 1,
  "verse": 1,
  "unit_id": "1corintios-1-1-u1",
  "clause_id": "1corintios-1-1-c1",
  "finite_verb": null,
  "connector": null,
  "connector_greek": null,
  "dependency_status": null,
  "stage4_decision": null,
  "stage4_reason": null,
  "warnings": [],
  "flags": []
}
```

Stage 5 must not infer missing fields silently. Missing required fields should produce a machine-readable warning or failure depending on severity.

## Output Contract

Stage 5 emits JSONL: one JSON object per survival decision.

Minimum output fields:

```json
{
  "book": "1corintios",
  "chapter": 1,
  "verse": 1,
  "unit_id": "1corintios-1-1-u1",
  "clause_id": "1corintios-1-1-c1",
  "survival_decision": "SURVIVE",
  "survival_rule_id": "S5-PRESERVE-INDEPENDENT-001",
  "survival_reason": "Independent clause survives unless removed by explicit rule.",
  "source_stage4_decision": null,
  "warnings": [],
  "flags": []
}
```

## Allowed Survival Decisions

```text
SURVIVE
REMOVE
PRESERVE_WARN
```

## Decision Meanings

### SURVIVE

The structure survives by explicit mechanical survival rule.

### REMOVE

The structure is removed by explicit mechanical survival rule.

### PRESERVE_WARN

The structure is preserved because certainty is insufficient for removal.

PRESERVE_WARN is not a final claim of trunk certainty. It is a conservative mechanical holding state.

## Required Provenance

Every survival decision must include:

```text
survival_rule_id
survival_reason
source_stage4_decision
```

No survival decision may be emitted without rule provenance.

## Forbidden Output Content

Stage 5 output must not include:

```text
main idea
emphasis
central
important
primary
secondary
supporting idea
theological center
rhetorical climax
```

These are semantic-importance terms and are outside Stage 5.
