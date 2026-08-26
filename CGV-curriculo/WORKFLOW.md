# CGV Workflow Standard

**Status:** Draft — foundational specification
**Scope:** All CGV biblical translation, analysis, and manual-production projects
**Version:** 0.2

------

# 1. Authority

This document defines the canonical CGV production workflow.

It governs the movement of a biblical book from source-language text through:

**LBF Translation → Alignment → Reader Analysis → Observer Marking → Compiled Skeleton → Manual Architecture → Writing → Editing → Verification → Human Approval**

Application-specific workflows may define detailed procedures for their own stage, but they may not silently weaken, bypass, or contradict this workflow.

Examples:

- `MANUAL_STANDARD.md` — how a manual is built
- `contracts/GATE0_CONTRACT.md` — what evidence the translator handoff requires
- `.cursor/agents/` — the clearance and procedure of Arquitecto, Escriba, Editor, Corrector

See `DOCUMENT_MAP.md` for which document owns which rule.

This document defines **what must happen and in what order**.

Application-specific workflows define **how that work is performed**.

------

# 2. Purpose

The purpose of the CGV workflow is not merely to produce polished manuals.

The purpose is to produce manuals whose development can be traced, verified, and defended from the biblical text.

The system must preserve an auditable chain from:

**Original-language source**

↓

**LBF Spanish translation and alignment**

↓

**Textual observation, analysis, and Observer marking**

↓

**Compiled Skeleton**

↓

**Manual architecture**

↓

**Written manual**

↓

**Edited and verified manual**

↓

**Approved release**

The workflow exists to prevent unsupported interpretation, silent source changes, accidental corruption, unauthorized downstream repair, and loss of provenance.

------

# 3. Governing Principle

A CGV artifact is not considered correct merely because an AI model, agent, script, compiler, reviewer, or human says that it looks correct.

Every phase must produce evidence appropriate to its responsibility.

Work advances only when the applicable gate has been satisfied.

A project or artifact is considered approved only when:

1. its declared inputs are known;
2. those inputs are versioned;
3. required validation has passed;
4. unresolved findings have been classified;
5. required human or specialist review has occurred;
6. the artifact has been explicitly approved;
7. its provenance has been recorded.

**Evidence is not a verdict.**

**A finding is not automatically a defect.**

**Fluent prose is not evidence of textual faithfulness.**

**A polished manuscript is not automatically a verified manuscript.**

------

# 4. Source Hierarchy

Every CGV project must explicitly declare its source hierarchy.

For projects using the CGV Spanish Bible, the working hierarchy is:

```text
Original-language biblical source
        ↓
LBF Spanish translation
        ↓
Original-language ↔ LBF alignment
        ↓
CGV Reader analysis
        ↓
Observer marking (progress JSON)
        ↓
Compiled Skeleton
        ↓
Manual architecture
        ↓
CGV Manual
```

LBF is the declared Spanish biblical source for CGV manual production.

The workflow must never silently substitute another Spanish Bible for LBF.

Every project must record, where applicable:

- biblical book;
- source identity;
- source revision;
- LBF translation revision;
- alignment revision;
- alignment validation status;
- Reader revision;
- skeleton revision;
- architecture revision;
- manual revision;
- workflow version;
- relevant compiler/tool version;
- approval status;
- generated-artifact identity.

------

# 5. Fundamental Ownership Rule

## Every kind of work must be corrected in the system that owns it.

Downstream systems must not silently repair upstream defects.

Examples:

### Translation problem

Return to:

**cgv-translator**

### Alignment problem

Return to:

**cgv-translator**

### Reader observation or clause-analysis problem

Return to:

**cgv-reader**

### Compiled Skeleton problem

Return to:

**cgv-reader / skeleton compilation process**

### H1/H2/H3 or structural architecture problem

Return to:

**Architect**

### Manual-writing problem

Return to:

**Escriba**

### Editorial-language problem

Return to:

**Editor**

If an Editor discovers an alignment problem, the Editor does not repair the alignment.

If Escriba disagrees with the Reader analysis, Escriba does not silently rewrite the analytical foundation.

If Architect detects a translation problem, Architect does not reinterpret the Spanish text to compensate for it.

The issue must return to the stage that owns the evidence.

------

# 6. System Responsibilities

## 6.1 cgv-translator

**Purpose:** Produce the authoritative LBF Spanish translation and original-language alignment used by the CGV system.

cgv-translator owns:

- LBF translation work;
- source-language comparison;
- translation revision;
- original-language alignment;
- alignment revision;
- translation consistency review;
- alignment validation;
- book-level translation review;
- book-level alignment review;
- approved translation/alignment export.

All translation and alignment changes must occur here.

No downstream CGV system may independently modify the approved LBF translation or alignment.

------

## 6.2 cgv-MANAGER

**Purpose:** Govern and orchestrate the CGV production workflow.

cgv-MANAGER is the workflow authority.

It does not translate the Bible.

It does not perform Reader analysis.

It does not write the manual.

Its responsibilities are to:

- maintain project state;
- register authoritative artifacts;
- record artifact versions;
- preserve provenance;
- enforce workflow order;
- enforce approval gates;
- prevent blocked transitions;
- determine what work is eligible next;
- dispatch authorized work;
- collect validation results;
- collect structured findings;
- preserve approval history;
- track dependencies between artifacts;
- identify downstream artifacts affected by upstream changes;
- require regeneration or review when necessary;
- prepare release status.

Agents must not infer project state from conversation history.

cgv-MANAGER must maintain explicit state.

------

## 6.3 cgv-reader — Reader, Observer, Compiler

**Purpose:** Perform disciplined reading, observation and textual analysis from the approved LBF
text and alignment, and compile the result.

`cgv-reader` holds three stages, not one:

### Reader

Reading and observation. Its work may include finite verbs, clauses, actors, actions,
relationships, textual movement, tension, repetition, contrast, progression, structural
observations, and the other defined CGV observation categories.

Beyond the clause, the Constitution's Layer 2 and Layer 3 apply: the functional move of each
sentence, and the movement of the literary unit. See `cgv_hermeneutical_constitution_draft.md` §3.1
and `CGV INTERNAL – STRUCTURE FOUNDATION.md`.

### Observer

Clause marking against the approved alignment, producing the progress JSON. **Jason** is an
assistant that helps a human fill that JSON faster. Jason is not a workflow stage, has no
clearance, and produces no artifact the workflow depends on except through Observer.

### Compiler

A controlled transformation of approved Observer data into the **Compiled Skeleton**. It is not an
opportunity for the compiler to invent analysis.

cgv-reader is a read-only consumer of published data and owns no book-specific artifact — see its
`DATA_CONTRACT.md`. Every stage output lands in `{NN.Curso}/`.

The Reader is not a manual-writing environment. Its purpose is to expose and record what is
happening in the text.

------

## 6.4 Arquitecto

**Purpose:** Establish the manual's structural architecture from the approved Compiled Skeleton.

Architect determines:

- H1 headings;
- H2 headings;
- H3 headings;
- section hierarchy;
- major section boundaries;
- sequence;
- structural progression;
- approved architectural/telos decisions where required.

Architect must work from the approved skeleton.

Architect may not silently rewrite translation, alignment, or Reader analysis.

------

## 6.5 Escriba

**Purpose:** Write the CGV manual from approved upstream artifacts.

Escriba receives:

1. the approved LBF text;
2. the approved alignment where required;
3. the approved Compiled Skeleton;
4. the approved Manual Architecture;
5. applicable manual specifications.

Escriba may:

- explain;
- develop;
- connect;
- organize authorized content;
- improve pedagogical clarity;
- write transitions;
- turn the approved structure into a coherent manual.

Escriba may not silently invent new textual evidence or overwrite upstream analysis.

Questions must be flagged and routed to the responsible stage.

------

## 6.6 Editor and Corrector

Editorial work is two roles with different clearances and different tiers. Both operate inside
`G7_EDITORIAL`; each records its own provenance entry.

### Editor — mechanical

**Purpose:** Repair mechanical damage without touching wording.

Editor may address whitespace, markdown corruption, structural damage, marker violations,
heading-shape errors and footnote integrity.

Editor may not change wording. Tier `local_small` — *Editor is allowed to be stupid.*

### Corrector — prose

**Purpose:** Improve the written manual while preserving its approved textual and structural
foundation.

Corrector may address clarity, grammar, readability, unnecessary repetition, terminology,
consistency, transitions, `### En síntesis` wording, `Actores principales` rendered as prose, and
the removal of stock closers.

Tier `strong_writer`.

### Neither may

- introduce a translation, alignment, lexical, historical or theological claim;
- introduce new textual analysis or new architecture;
- resolve a tension the text leaves open;
- touch protected content.

When such a problem is discovered it must be escalated to the stage that owns it, never repaired
in the manuscript.

------

## 6.7 Verification Functions

Verification may be performed by deterministic scripts, specialized agents, qualified reviewers, specialists, or humans according to the evidence being examined.

Verification identifies and classifies problems.

Verification does not automatically authorize rewriting.

------

## 6.8 Human Authority

Human approval remains the final release authority.

The purpose of automation is to make the process disciplined, repeatable, visible, and auditable.

It does not remove human responsibility.

------

# 7. Authoritative Artifact Chain

Each book progresses through a defined chain of artifacts.

## Artifact 1 — Translator Project

Working translation and alignment inside cgv-translator.

↓

## Artifact 2 — Approved LBF Book

Versioned and approved translation/alignment package.

↓

## Artifact 3 — Reader Project

Reader analysis performed against the approved LBF Book.

↓

## Artifact 4 — Compiled Skeleton

Versioned compiled representation of the approved Reader analysis.

↓

## Artifact 5 — Manual Architecture

Approved H1/H2/H3 structure and associated architectural decisions.

↓

## Artifact 6 — Manual Draft

Manual written by Escriba from approved upstream artifacts.

↓

## Artifact 7 — Edited Manual

Manual after authorized editorial processing.

↓

## Artifact 8 — Verified Manual

Manual after required final verification.

↓

## Artifact 9 — Approved CGV Manual

Human-approved release artifact.

Every artifact must know which upstream revisions produced it.

------

# 8. Workflow Overview

Gate IDs, statuses and transitions are defined in `STATE_MODEL.md` §5–§9. This overview names the
work; STATE_MODEL names the machine.

```text
cgv-translator          LBF translation + alignment            G0_ALIGNMENT
        ↓
Reader                  reading and observation
Observer                clause marking → progress JSON
  (Jason assists the human; it is not a workflow stage)
Compiler                Compiled Skeleton                      G1_COMPILE
        ↓
verification            mechanical                             G2_MECHANICAL
                        textual                                G3_TEXTUAL
                        specialists                            G4_SPECIALISTS
        ↓
Arquitecto              architecture, telos                    G5_ARCHITECTURE
        ↓
Escriba                 manual prose                           G6_WRITING
        ↓
Editor + Corrector      mechanical + prose                     G7_EDITORIAL
        ↓
Verificador             final verification                     G8_FINAL_VERIFY
        ↓
Human                   review                                 G9_HUMAN_REVIEW
                        release                                G10_RELEASE
```

A project may not skip a required gate merely because a later agent believes the result is
acceptable. A gate is skipped only as `SKIPPED` under STATE_MODEL §6, with a recorded human reason.

------

# 9. Phase 0 — Project Initialization

**System:** cgv-MANAGER

A biblical book must first exist as an explicit project.

The Manager registers:

- book;
- project ID;
- applicable workflow version;
- source configuration;
- expected translator project;
- responsible agents or participants;
- artifact history;
- current workflow state.

Initial state:

`G0_ALIGNMENT = READY`, every other gate `BLOCKED` (`STATE_MODEL.md` §7).

No downstream work should begin from unofficial or unregistered source data.

------

# 10. Phase 1 — LBF Translation and Alignment

**System:** cgv-translator

This phase produces the textual foundation for all later work.

The detailed procedure belongs in the translator's own documentation. The evidence it must hand
over is fixed by `contracts/GATE0_CONTRACT.md`.

At the master-workflow level, the required progression is:

## 10.1 Source preparation

Confirm the required source data and project identity.

## 10.2 Translation

Produce or revise the LBF Spanish translation according to the approved LBF translation methodology.

## 10.3 Alignment

Align the Spanish translation with the original-language source.

## 10.4 Mechanical validation

Where deterministically possible, validate matters such as:

- completeness;
- chapter and verse order;
- identifiers;
- missing source units;
- unexplained duplicate alignment;
- unexplained gaps;
- span boundaries;
- token/word accounting;
- malformed data;
- reproducibility;
- version identity.

## 10.5 Linguistic validation

Qualified review must address matters that mechanical tooling cannot determine, including whether:

- an alignment is linguistically defensible;
- relationships between Hebrew, Aramaic, Greek, and Spanish have been represented appropriately;
- a source unit has been buried or distorted;
- an alignment creates a false relationship;
- translation choices accurately represent the intended source.

## 10.6 Book-level consistency review

The complete book must be reviewed for internal consistency.

Decisions made in one passage may affect comparable constructions elsewhere.

Local approval alone is not sufficient for book release.

## 10.7 Translator approval

Translation and alignment must be explicitly approved.

The resulting export becomes the:

**Approved LBF Book**

------

# 11. G0_ALIGNMENT — Source, Translation, and Alignment Approval

`G0_ALIGNMENT` is mandatory.

No Reader project may begin from an unapproved source package.

It must establish, as applicable:

- source identity;
- source completeness;
- translation revision;
- alignment revision;
- verse/order integrity;
- alignment completeness;
- source-word accounting;
- boundary integrity;
- reproducibility;
- absence of unexplained duplication or loss;
- appropriate treatment of ambiguous cases;
- linguistic defensibility;
- approval identity.

**Gate rule: if required translation or alignment validation fails, downstream production is blocked.**

No downstream agent may compensate for unresolved source defects by rewriting, rearranging, or inventing content.

------

# 12. Phase 2 — Manager Intake

**System:** cgv-MANAGER

cgv-MANAGER receives the approved translator export.

The Manager verifies that the artifact being registered matches its declared state.

Checks should include:

- correct project;
- correct biblical book;
- expected chapter/verse structure;
- translation revision;
- alignment revision;
- validation status;
- approval status;
- artifact identity;
- export integrity;
- provenance information.

If successful:

`G1_COMPILE = READY`

If not:

`G0_ALIGNMENT = FAIL`, with the finding recorded

Manager does not repair the translator artifact.

------

# 13. Phase 3 — Reader Analysis

**System:** cgv-reader

cgv-reader must import the exact approved LBF artifact registered by cgv-MANAGER.

Reader analysis then proceeds according to the Reader methodology.

The detailed procedure belongs in the Reader and Observer application documentation. What the
workflow requires of it is stated here and in `cgv_hermeneutical_constitution_draft.md` §3.1.

Reader analysis may include:

- finite verbs;
- clause identification;
- actors;
- actions;
- relationships;
- movement;
- tension;
- repetition;
- contrast;
- progression;
- structural relationships;
- other approved observational categories.

Reader observations should remain attached to their textual locations and source evidence wherever possible.

The Reader's purpose is not to create an attractive manual outline.

The purpose is to expose the structure and movement present in the text.

------

# 14. Skeleton Compilation

After required Reader work is complete, the Reader project is compiled into the:

**Compiled Skeleton**

Compilation is a controlled transformation of approved Reader data.

It is not an opportunity for the compiler to invent analysis.

The generated skeleton must record:

- LBF source revision;
- alignment revision;
- Reader project revision;
- compiler/tool version where applicable;
- generation identity;
- generation date/time;
- skeleton revision.

------

# 15. G1_COMPILE / G2_MECHANICAL — Skeleton Approval

The Compiled Skeleton must be validated before Architect begins.

Validation may include:

### Mechanical

- required fields;
- valid identifiers;
- valid hierarchy;
- missing units;
- duplicate units;
- malformed output;
- generation reproducibility.

### Textual / analytical

- correct representation of Reader observations;
- preservation of relevant clause relationships;
- actors/actions represented correctly;
- no unexplained loss during compilation;
- no invented observations;
- appropriate linkage to source locations.

After approval:

`G1_COMPILE = PASS` · `G2_MECHANICAL = PASS`

------

# 16. Phase 4 — Manual Architecture

**Agent:** Architect

Architect receives the approved Compiled Skeleton.

Architect establishes:

- H1;
- H2;
- H3;
- hierarchy;
- section boundaries;
- progression;
- approved architectural relationships.

The architecture must be defensible from the skeleton.

Architect should not impose an attractive outline that overrides the textual structure.

Architectural decisions must remain distinguishable from direct textual observations.

Output:

**Manual Architecture**

------

# 17. G5_ARCHITECTURE — Architecture Approval

Architecture must be reviewed before writing begins.

The review asks whether:

- all major divisions are supported;
- hierarchy is coherent;
- sections remain accountable to the skeleton;
- unsupported architectural claims have been avoided;
- important skeleton content has not been silently discarded;
- interpretive or telos-level decisions requiring explicit approval have been identified.

After approval:

`G5_ARCHITECTURE = PASS`

------

# 18. Phase 5 — Manual Writing

**Agent:** Escriba

Escriba writes the manual using only approved inputs.

Required inputs include:

- approved LBF text;
- approved Compiled Skeleton;
- approved Manual Architecture;
- applicable manual specification.

Escriba may develop the material into readable, teachable prose.

However, the distinction must remain clear between:

- what the text directly establishes;
- what Reader analysis observes;
- what Architect structurally concludes;
- what the manual explains or interprets.

When uncertainty occurs, Escriba must record it instead of silently solving an upstream problem.

Suggested issue classes include:

```text
TEXT_QUESTION
ALIGNMENT_QUESTION
READER_QUESTION
SKELETON_QUESTION
ARCHITECTURE_QUESTION
LEXICAL_REVIEW
HISTORICAL_REVIEW
THEOLOGICAL_REVIEW
EDITORIAL_QUESTION
```

Output:

**Manual Draft**

------

# 19. G6_WRITING — Draft Approval

The draft must be reviewed for correspondence with its approved inputs.

A draft is not approved merely because the prose is strong.

Review must determine, as applicable:

- architecture was followed;
- skeleton observations were preserved;
- unsupported material was not introduced;
- direct observation and interpretation remain distinguishable;
- unresolved source questions are recorded;
- required manual specifications were satisfied.

After approval:

`G6_WRITING = PASS`

------

# 20. Phase 6 — Editorial Processing

**Agent:** Editor

Editor performs authorized editorial work.

Editorial review should occur at several levels.

## Language

- grammar;
- clarity;
- readability;
- unnecessary repetition;
- consistency;
- terminology.

## Structure

- heading consistency;
- progression;
- transitions;
- section balance;
- internal coherence.

## Skeleton fidelity

Does the manual accurately represent the approved skeleton?

## Text fidelity

Does the manual remain faithful to the approved LBF text and its textual basis?

Editor may correct editorial defects directly.

Editor must escalate upstream defects to their owning stage.

------

# 21. G8_FINAL_VERIFY — Final Verification

Final verification is broader than editing.

Required verification may include:

- structural/mechanical audit;
- textual verification;
- lexical verification;
- historical verification;
- specialist review;
- architecture comparison;
- skeleton comparison;
- source comparison;
- unresolved-finding review;
- artifact/provenance validation.

A final verifier identifies and classifies defects.

Verification does not automatically authorize silent rewriting.

------

# 22. Evidence Classes

Findings must be classified before repair.

## Deterministic

A machine can directly establish the condition.

Examples:

- malformed Markdown;
- duplicate identifiers;
- missing fields;
- impossible state;
- invalid references;
- unexplained generated-data gaps.

## Textual / linguistic

Requires examination of the biblical text and alignment.

## Lexical / language

Requires competent Hebrew, Aramaic, Greek, Spanish, or other relevant language judgment.

## Historical

Requires appropriate historical evidence and specialist judgment.

## Interpretive

Requires distinction between:

- what the text states;
- what follows from the text;
- what the CGV framework proposes.

## Architectural / telos

Requires Architect-level judgment and must not be silently invented by a writing or editing agent.

------

# 23. Evidence Is Not Verdict

Automated reports are diagnostic evidence.

An automated finding must not automatically become a repair instruction.

Every significant finding is classified before repair. The finding statuses and dispositions are
defined in `STATE_MODEL.md` §16 and §17 and are not restated here.

Uncertainty must be recorded rather than hidden. `ACCEPTED_RISK` requires explicit human
authorization; a CRITICAL finding may never be released as `ACCEPTED_RISK` unless the manual
specification explicitly permits it.

------

# 24. Finding Severity

Severity is defined in `STATE_MODEL.md` §15 — `CRITICAL` · `HIGH` · `MEDIUM` · `LOW` · `INFO`. It is
not restated here, and no other scale is valid.

What blocks progression is not a severity but a **blocker** (`STATE_MODEL.md` §18) or an unresolved
CRITICAL finding. Gate pass conditions are STATE_MODEL §19.

------

# 25. Structured Agent Results

Agents and automated validation processes return structured findings rather than only prose.

The finding object — its fields, types, severities, statuses and dispositions — is defined in
`STATE_MODEL.md` §13–§17. Agents emit that shape and no other.

An agent must not declare an unresolved finding closed merely by rewriting the affected text.

Where a finding also needs a human-readable home, it goes in a report under `{NN.Curso}/reports/`
following the report protocol in `MANUAL_STANDARD.md` §7. Every finding quotes text and gives a
reference; a finding with no quote is not a finding.

------

# 26. Change Control

Every substantive modification must be attributable to:

- person or agent;
- task;
- input revision;
- output revision;
- reason;
- findings addressed;
- evidence used;
- date/time where appropriate.

Protected upstream content must not change without explicit authorization.

Protected content includes, where applicable:

- approved LBF Scripture;
- approved alignment;
- Reader observations;
- clause identifiers;
- approved skeleton;
- approved architectural decisions;
- specialist-approved claims.

A downstream stage may not silently overwrite upstream evidence.

------

# 27. Dependency and Invalidation Rule

Every downstream artifact depends upon specific upstream revisions.

```text
LBF Daniel v1.0 → Reader → Skeleton → Architecture → Manual Daniel v1.0
```

If `LBF Daniel v1.0` is corrected and becomes `v1.1`, the system must know that the existing
Reader, Skeleton, Architecture and Manual were produced from the earlier source. They may not
silently remain marked current.

**How invalidation is computed and recorded is defined in `STATE_MODEL.md` §12** — gates go
`STALE`, `artifact.current` goes false, `regeneration_required` goes true. The manager computes
this from declared dependencies; it does not guess, and no agent sets it by hand.

The responsible stage then determines whether the artifact is unaffected, needs partial review,
needs regeneration, or needs complete reprocessing. **That decision is itself recorded** as a
provenance entry (`STATE_MODEL.md` §22).

------

# 28. Regeneration Rule

Whenever an upstream change affects a generated artifact:

```text
upstream change → required validation → affected stage re-run
→ new artifact revision → required validation → approval
```

The old artifact must not be treated as evidence of the new state.

No artifact may be called current simply because an older version passed verification. A `STALE`
gate cannot pass without an actual rerun or the required review — see the transition rules in
`STATE_MODEL.md` §9, which disallow `STALE → PASS` and `FAIL → PASS` directly.

------

# 29. Project State

Every project maintains explicit state in one canonical file:

```text
{NN.Curso}/state.yaml
```

**The schema is defined in `STATE_MODEL.md` §3** and is not restated here. Per-book state lives
with the book, alongside `spec.md` and `blocks.md` — not in the method repository.

Agents must not infer project state from previous conversations. The Manager is authoritative.

------

# 30. Workflow Status

Status is not a single sequence. It is three independent facts, all defined in `STATE_MODEL.md`:

- **project status** — §4 · `ACTIVE` `PAUSED` `BLOCKED` `RELEASED` `ARCHIVED`
- **gate status** — §6 · one per gate, `BLOCKED` through `PASS`, plus `STALE` and `SKIPPED`
- **release status** — §24 · `NOT_RELEASED` `CANDIDATE` `APPROVED` `RELEASED` `REVOKED`

`workflow.current_gate` is the earliest mandatory gate that is not `PASS` or validly `SKIPPED`.
**The manager computes it.** A human may not set it to bypass prerequisites.

The earlier flat state sequence (`TRANSLATION_PENDING` → … → `MANUAL_APPROVED`) is retired: it
could not express a stale gate, a blocked downstream stage, or two gates in flight at once.

------

# 31. Gate Enforcement

cgv-MANAGER enforces gates rather than merely displaying progress.

A downstream gate cannot become `READY` until all mandatory prerequisites are `PASS`
(`STATE_MODEL.md` §8). So:

- Compiler Generate may not run unless `G0_ALIGNMENT = PASS`
- Arquitecto may not begin unless `G1_COMPILE = PASS` and the required verification gates pass
- Escriba may not begin unless `G5_ARCHITECTURE = PASS`
- Release requires every gate `G0`–`G9` at `PASS`, no blocker, no unresolved CRITICAL finding, and
  human approval bound to the exact artifact revision and checksum (`STATE_MODEL.md` §25)

A later agent's confidence cannot override a failed gate.

------

# 32. Traceability Requirement

The finished manual must remain traceable backward through the production chain.

Ideally:

```text
Manual paragraph / section
        ↓
Architecture section
        ↓
Skeleton unit
        ↓
Reader observation
        ↓
LBF text
        ↓
Original-language alignment
```

Not every relationship must necessarily be exposed to the end user, but the production system should preserve enough information to reconstruct the chain.

The goal is to be able to answer:

**Why does the manual say this?**

with evidence.

------

# 33. Definition of Done

A CGV manual is **DONE** only when:

-  source identity is declared;
-  source revision is recorded;
-  LBF translation revision is recorded;
-  alignment revision is recorded;
-  required translation validation passed;
-  required alignment validation passed;
-  approved translator artifact was registered;
-  Reader work was performed against the approved source;
-  Compiled Skeleton was generated;
-  Skeleton validation passed;
-  Skeleton was approved;
-  Manual Architecture was approved;
-  authorized writing is complete;
-  draft review is complete;
-  editorial processing is complete;
-  required final verification passed;
-  critical/high findings are resolved or explicitly dispositioned;
-  artifact provenance is recorded;
-  no unreviewed upstream changes invalidate the final artifact;
-  human review is complete;
-  human release approval is recorded.

**If any mandatory item is incomplete, the manual is not FINAL.**

------

# 34. Non-Negotiable Rules

1. **Do not invent.**
2. **Do not silently substitute sources.**
3. **Do not silently repair upstream defects downstream.**
4. **Do not treat automated findings as verdicts.**
5. **Do not treat fluent prose as evidence.**
6. **Do not let an agent exceed its authority.**
7. **Do not allow model confidence to substitute for verification.**
8. **Do not call an artifact current when its inputs have changed without required review or regeneration.**
9. **Do not release with unresolved blockers.**
10. **Preserve an auditable trail from source to released artifact.**
11. **Every stage must know which approved artifact it received.**
12. **Every approved artifact must know what produced it.**

------

# 35. Where Each Rule Lives

The master workflow establishes the governing process. It does not hold every rule.

**`DOCUMENT_MAP.md` is the authority on which document owns which rule.** Read it before adding a
rule anywhere.

```text
CGV-curriculo/
    DOCUMENT_MAP.md      who owns what — read first
    cgv_hermeneutical_constitution_draft.md
                         non-negotiables, observation layers, drift tests
    WORKFLOW.md          this file — order, ownership, artifact chain, done
    STATE_MODEL.md       every enumerated value: gates, findings, release
    MANUAL_STANDARD.md   markers, hierarchy, commentary, clearance, reports
    contracts/           per-boundary evidence contracts
    config/models.yaml   model tiers

curriculo/NN.Curso/
    spec.md              book specification
    blocks.md            literary-unit inventory
    state.yaml           workflow state
```

A rule stated in two documents is a defect. If you need another document's rule, point at it.

------

# 36. Current Process-Development Priority

*This section is expected to change. Update it when the priority changes; a stale priority is worse
than none.*

Two pieces of the method are specified and not implemented.

**First — Constitution Layers 2 and 3.** `CGV INTERNAL – STRUCTURE FOUNDATION.md` defines three
layers: clause control, functional move, paragraph movement. Only Layer 1 is built. The
consequence is manuals that carry grammar and flow without carrying what the text says or the
shape of the book. The work is a literary-unit inventory (`blocks.md`) and a content statement per
unit, both governed by the drift tests, with form names restricted to the text's own marker
vocabulary.

**Second — the translator workflow.** The translation and alignment of Daniel produced substantial
practical experience that has not been converted into a repeatable procedure: project
initialization, source preparation, translation and alignment sequence, difficult alignment
relationships, automated and human validation, completion criteria at verse, chapter and book
level, issue classification, escalation, approval, versioning, freeze, and the export contract with
cgv-MANAGER — the last of which now exists as `contracts/GATE0_CONTRACT.md`.

The objective in both cases is the same: the process itself must become part of the system, so the
next book does not depend on remembering how the last one was done.

------

# 37. Final Principle

The CGV workflow is designed to preserve fidelity through controlled responsibility.

Each stage must do its own work.

Each stage must preserve the evidence produced before it.

Each stage must be explicit about uncertainty.

Each stage must produce an artifact that can be traced to its inputs.

And no manual is final until the complete chain from source to release has been verified and approved.