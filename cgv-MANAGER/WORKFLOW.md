# CGV Workflow Standard

**Status:** Draft — foundational specification  
**Scope:** All CGV manuals  
**Version:** 0.1

---

## 1. Purpose

This document defines the universal production and verification workflow for every CGV manual.

It is the governing standard for source preparation, source/alignment validation, compilation, structural generation, observation, interpretation, writing, specialist verification, editorial processing, final audit, human approval, and release.

A manual-specific specification may add requirements, but it may not silently weaken this workflow.

## 2. Governing Principle

A CGV manual is not considered correct because an AI model, agent, script, compiler, or reviewer says that it looks correct.

A manual is complete only when:

1. its declared source and alignment have passed the required validation;
2. the applicable manual specification has been satisfied;
3. every required workflow gate has passed;
4. unresolved findings have been classified and dispositioned;
5. the final artifact has been regenerated from the validated inputs;
6. the final artifact has passed required automated and human review;
7. a human has authorized release.

**Evidence is not a verdict. A finding is not automatically a defect. A polished manuscript is not automatically a verified manuscript.**

## 3. Source of Truth

Every project must explicitly declare its source hierarchy.

For CGV manuals using the CGV Spanish Bible, **LBF is the declared Spanish biblical source** because there is no existing Spanish equivalent serving the required function.

The workflow must never silently substitute another Spanish Bible for LBF.

Each project must record:

- source identity;
- source version/revision;
- source location;
- alignment revision;
- alignment validation status;
- compiler/version information;
- generated-artifact identity.

## 4. Gate 0 — Source and Alignment Validation

**Gate 0 is mandatory and precedes the first compiled manual.**

The LBF alignment is a foundational dependency. If the alignment is wrong, downstream manual output may be invalid.

Gate 0 must establish source completeness, verse/order integrity, reproducibility, span/clause integrity, source-word accounting appropriate to the CGV method, boundary integrity, absence of unexplained duplication or loss, appropriate handling of ambiguous cases, and defensible linguistic alignment.

### Mechanical validation

Scripts may verify completeness, numbering, ordering, IDs, span boundaries, duplication, gaps, token/word accounting, reproducibility, and checksums/version identity.

### Human/linguistic validation

Qualified review is required for questions such as whether a clause boundary is linguistically defensible, whether an independent clause has been buried, whether a span creates a false relationship, whether an alignment represents the intended source, and whether Hebrew/Aramaic/Greek relationships have been represented correctly.

**Gate rule: if a required alignment validation fails, block compilation.**

No downstream agent may compensate for an unresolved alignment defect by rewriting, rearranging, or inventing content.

## 5. Compiler and Artifact Provenance

Compilation is a controlled transformation, not an editorial judgment.

The compiler generates the skeleton/artifact from validated inputs.

Every generated artifact must be traceable to source revision, alignment revision, compiler version, generation date/time, and project/manual identity.

A source change invalidates the prior generated artifact unless the workflow explicitly establishes that the change does not affect it.

**No artifact may be called current until it has been regenerated from the current validated inputs.**

## 6. Evidence Classes

Findings must be classified before repair.

### Deterministic
A machine can establish the condition directly: malformed Markdown, duplicate identifiers, unmatched tags, missing required fields, excessive blank-line runs, and similar conditions.

### Textual / linguistic
Requires examination of the source and alignment.

### Historical
Requires appropriate historical evidence and specialist judgment.

### Lexical / language
Requires competent review of Hebrew, Aramaic, Greek, or other relevant language data.

### Interpretive
Requires distinction between what the text states, what follows from it, and what the CGV framework proposes.

### Architectural / telos
Requires Arquitecto-level judgment and must not be silently invented by a writing or editing agent.

## 7. Evidence Is Not Verdict

Automated reports are diagnostic evidence.

An automated finding must not automatically become a repair instruction.

Before repair, the finding must be classified as:

- confirmed defect;
- expected/legitimate structure;
- false positive;
- unresolved;
- requires specialist review.

Uncertainty must be recorded rather than hidden.

## 8. Agent Authority

Agents are specialized workers, not general authorities.

Each agent must have a defined purpose, permitted inputs, permitted modifications, prohibited modifications, required evidence, required output format, and escalation conditions.

An agent may not exceed its authority because it believes another change would improve the manuscript.

### Separation of responsibilities

**Arquitecto:** approved architecture, scope, and high-level CGV reasoning.

**Escriba:** authorized writing; preserves the distinction between source observation and interpretation.

**Editor:** authorized editorial/structural cleanup; must not silently introduce facts, theology, historical claims, lexical claims, or new interpretation.

**Verifier:** identifies and classifies defects; verification does not authorize silent rewriting.

**Specialists:** designated historical, textual, linguistic, or other specialist questions.

**Release Gate:** determines whether all required conditions for release have been satisfied.

No single writing agent may perform all of these roles.

## 9. Model Assignment

Models are interchangeable workers, not authorities.

The workflow should route work according to capability and cost.

Typical allocation:

- deterministic scripts/Python: mechanical validation;
- local small model: mechanical triage and simple classification;
- local larger model: deeper local review;
- Claude/Sonnet-class model: difficult textual, historical, linguistic, or writing judgment;
- Opus-class model: architecture/telos and high-level judgment;
- human: final authority and release approval.

The workflow must not require an expensive model to repeat checks that deterministic tooling can establish.

## 10. Change Control

Every substantive modification must be attributable to agent/person, task, input revision, output revision, reason, findings addressed, and evidence used.

Protected content must not change without explicit authorization.

Examples include source Scripture, source alignment, clause identifiers, approved architectural decisions, verified technical data, and specialist-approved claims.

A downstream agent may not silently overwrite upstream evidence.

## 11. Required Workflow

A project normally progresses through:

```text
0. SOURCE / ALIGNMENT VALIDATION
1. COMPILER GENERATE
2. STRUCTURAL / MECHANICAL VALIDATION
3. TEXTUAL VALIDATION
4. SPECIALIST VALIDATION
5. ARCHITECTURAL REVIEW
6. AUTHORIZED WRITING
7. EDITORIAL PROCESSING
8. FINAL VERIFICATION
9. HUMAN REVIEW
10. RELEASE GATE
```

A project may not skip a required gate merely because a later agent believes the result is acceptable.

## 12. Blockers

**BLOCKER** prevents progression. Examples: failed required LBF alignment validation, source corruption, unresolved critical textual loss, unauthorized source modification, missing required structural data, unresolved critical factual error.

**REVIEW REQUIRED** means the workflow may proceed only to the designated review stage.

**WARNING** does not necessarily block progression but must remain recorded.

**PASS** means no unresolved issue within the checking stage's authority.

## 13. Workflow State

Every project must maintain explicit state.

At minimum:

```yaml
project:
workflow_version:
manual:
source:
source_revision:
alignment_revision:
alignment_status:
compiler_version:
artifact_revision:
current_gate:
gates:
findings:
blockers:
last_generated:
last_verified:
release_status:
```

The workflow manager is responsible for maintaining this state. Agents must not infer project state from conversation history.

## 14. Workflow Manager

The CGV Workflow Manager is the orchestration layer.

It does not write the manual.

Its responsibilities are to:

- load the applicable workflow and manual specification;
- maintain project state;
- enforce gate ordering;
- prevent blocked transitions;
- dispatch approved tasks;
- route tasks to appropriate models/tools;
- collect structured findings;
- preserve provenance;
- compare revisions;
- require regeneration when necessary;
- determine what work is eligible next;
- prepare release status.

The manager must treat the workflow specification as authoritative.

## 15. Structured Agent Results

Agents should return structured results rather than only prose.

At minimum:

```yaml
status: PASS | FAIL | REVIEW_REQUIRED
findings:
  - id:
    severity:
    location:
    type:
    evidence:
    disposition:
    action:
```

An agent must not declare an unresolved finding closed merely by rewriting the affected text.

## 16. Regeneration Rule

Whenever a change affects compiled output:

```text
source/alignment change
        ↓
required validation
        ↓
Compiler Generate
        ↓
new artifact
        ↓
validation
```

The old artifact must not be treated as evidence of the new state.

## 17. Definition of Done

A CGV manual is **DONE** only when:

- [ ] source is declared and versioned;
- [ ] LBF alignment has passed required Gate 0 validation;
- [ ] the applicable manual specification is identified;
- [ ] the artifact was generated from the validated inputs;
- [ ] structural/mechanical validation passed;
- [ ] textual validation passed;
- [ ] required specialist validation passed;
- [ ] architectural decisions are approved;
- [ ] authorized writing is complete;
- [ ] editorial processing is complete;
- [ ] final verification passed;
- [ ] all critical/high findings are resolved or explicitly dispositioned;
- [ ] final artifact provenance is recorded;
- [ ] human review is complete;
- [ ] human release approval is recorded.

**If any mandatory item is incomplete, the manual is not FINAL.**

## 18. Non-Negotiable Rules

1. Do not invent.
2. Do not silently substitute sources.
3. Do not silently repair upstream defects downstream.
4. Do not treat automated findings as verdicts.
5. Do not treat fluent prose as evidence.
6. Do not let an agent exceed its authority.
7. Do not call an artifact current when its inputs have changed and it has not been regenerated.
8. Do not release with unresolved blockers.
9. Do not allow model confidence to substitute for verification.
10. Preserve an auditable trail from source to released artifact.

## 19. Human Authority

The workflow manager enforces the process, but **human approval remains the final release authority**.

The system exists to make the process disciplined and auditable—not to remove human responsibility.
