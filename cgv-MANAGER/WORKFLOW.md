# CGV Workflow Standard

**Status:** Draft — foundational specification
**Scope:** All CGV biblical translation, analysis, and manual-production projects
**Version:** 0.2

------

# 1. Authority

This document defines the canonical CGV production workflow.

It governs the movement of a biblical book from source-language text through:

**LBF Translation → Alignment → Reader Analysis → Compiled Skeleton → Manual Architecture → Writing → Editing → Verification → Human Approval**

Application-specific workflows may define detailed procedures for their own stage, but they may not silently weaken, bypass, or contradict this workflow.

Examples:

- `cgv-translator/WORKFLOW.md`
- `cgv-reader/WORKFLOW.md`
- agent-specific instructions for Architect, Escriba, Editor, or verification agents

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

**Textual observation and analysis**

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

## 6.3 cgv-reader

**Purpose:** Perform disciplined reading, observation, and textual analysis from the approved LBF text and alignment.

Reader work may include:

- reading;
- observing;
- finite verbs;
- clauses;
- actors;
- actions;
- relationships;
- textual movement;
- tension;
- repetition;
- contrast;
- progression;
- structural observations;
- other defined CGV Reader analysis.

The Reader is not primarily a manual-writing environment.

Its purpose is to expose and record what is happening in the text.

Its final derived artifact is the:

**Compiled Skeleton**

------

## 6.4 Architect

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

## 6.6 Editor

**Purpose:** Improve and verify the written manual while preserving its approved textual and structural foundation.

Editor may address:

- clarity;
- grammar;
- readability;
- repetition;
- terminology;
- consistency;
- transitions;
- formatting;
- heading consistency;
- editorial coherence.

Editor must not silently introduce:

- new translation decisions;
- new alignment decisions;
- new lexical claims;
- unsupported historical claims;
- new theological claims;
- new textual analysis;
- new architecture.

When such a problem is discovered, it must be escalated.

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

```text
PHASE 0
PROJECT INITIALIZATION
        ↓
PHASE 1
TRANSLATION + ALIGNMENT
cgv-translator
        ↓
GATE 0
SOURCE / TRANSLATION / ALIGNMENT APPROVAL
        ↓
PHASE 2
MANAGER INTAKE
cgv-MANAGER
        ↓
PHASE 3
READER ANALYSIS
cgv-reader
        ↓
SKELETON COMPILATION
        ↓
GATE 1
SKELETON APPROVAL
        ↓
PHASE 4
MANUAL ARCHITECTURE
Architect
        ↓
GATE 2
ARCHITECTURE APPROVAL
        ↓
PHASE 5
MANUAL WRITING
Escriba
        ↓
GATE 3
DRAFT APPROVAL
        ↓
PHASE 6
EDITORIAL PROCESSING
Editor
        ↓
GATE 4
FINAL VERIFICATION
        ↓
PHASE 7
HUMAN REVIEW
        ↓
RELEASE GATE
        ↓
APPROVED CGV MANUAL
```

A project may not skip a required gate merely because a later agent believes the result is acceptable.

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

```text
TRANSLATION_PENDING
```

No downstream work should begin from unofficial or unregistered source data.

------

# 10. Phase 1 — LBF Translation and Alignment

**System:** cgv-translator

This phase produces the textual foundation for all later work.

The detailed procedure belongs in:

```
cgv-translator/WORKFLOW.md
```

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

# 11. Gate 0 — Source, Translation, and Alignment Approval

Gate 0 is mandatory.

No Reader project may begin from an unapproved source package.

Gate 0 must establish, as applicable:

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

```text
READER_READY
```

If not:

```text
TRANSLATION_REQUIRES_ATTENTION
```

Manager does not repair the translator artifact.

------

# 13. Phase 3 — Reader Analysis

**System:** cgv-reader

cgv-reader must import the exact approved LBF artifact registered by cgv-MANAGER.

Reader analysis then proceeds according to the Reader methodology.

The detailed procedure belongs in:

```
cgv-reader/WORKFLOW.md
```

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

# 15. Gate 1 — Skeleton Approval

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

```text
SKELETON_APPROVED
```

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

# 17. Gate 2 — Architecture Approval

Architecture must be reviewed before writing begins.

The review asks whether:

- all major divisions are supported;
- hierarchy is coherent;
- sections remain accountable to the skeleton;
- unsupported architectural claims have been avoided;
- important skeleton content has not been silently discarded;
- interpretive or telos-level decisions requiring explicit approval have been identified.

After approval:

```text
ARCHITECTURE_APPROVED
```

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

# 19. Gate 3 — Draft Approval

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

```text
DRAFT_APPROVED
```

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

# 21. Gate 4 — Final Verification

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

Every significant finding should be classified as:

```text
CONFIRMED_DEFECT
EXPECTED_STRUCTURE
FALSE_POSITIVE
UNRESOLVED
SPECIALIST_REVIEW_REQUIRED
```

Uncertainty must be recorded rather than hidden.

------

# 24. Finding Severity

A common severity model should be used across the workflow.

## BLOCKER

Prevents progression.

Examples:

- failed required LBF validation;
- source corruption;
- missing critical textual data;
- unresolved translation/alignment defect;
- unauthorized source modification;
- missing required skeleton data;
- unresolved critical factual error.

## REVIEW_REQUIRED

Work may proceed only to the designated review process.

## WARNING

Does not necessarily block progression but remains recorded.

## PASS

No unresolved issue exists within the checking stage's authority.

------

# 25. Structured Agent Results

Agents and automated validation processes should return structured findings rather than only prose.

Example:

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
    owner:
```

An agent must not declare an unresolved finding closed merely by rewriting the affected text.

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

Example:

```text
LBF Daniel v1.0
        ↓
Reader Daniel v1.0
        ↓
Skeleton Daniel v1.0
        ↓
Architecture Daniel v1.0
        ↓
Manual Daniel v1.0
```

If:

```text
LBF Daniel v1.0
```

is corrected and becomes:

```text
LBF Daniel v1.1
```

the system must know that the existing Reader, Skeleton, Architecture, and Manual were produced from the earlier source.

They may not silently remain marked current.

cgv-MANAGER must mark affected artifacts for review.

Possible state:

```text
UPSTREAM_CHANGED
```

The responsible stage determines whether:

- the artifact remains unaffected;
- partial review is required;
- regeneration is required;
- complete reprocessing is required.

That decision must itself be recorded.

------

# 28. Regeneration Rule

Whenever an upstream change affects a generated artifact:

```text
upstream change
        ↓
required validation
        ↓
affected stage re-run
        ↓
new artifact revision
        ↓
required validation
        ↓
approval
```

The old artifact must not be treated as evidence of the new state.

No artifact may be called current simply because an older version passed verification.

------

# 29. cgv-MANAGER State Model

Every project must maintain explicit state.

A conceptual example:

```yaml
project:
  id:
  book:
  workflow_version:

source:
  source_identity:
  source_revision:

translation:
  revision:
  status:
  approved_by:
  approved_at:

alignment:
  revision:
  status:
  approved_by:
  approved_at:

reader:
  revision:
  status:

skeleton:
  revision:
  status:
  generated_from:
  approved_by:

architecture:
  revision:
  status:
  generated_from:
  approved_by:

manual:
  revision:
  status:
  generated_from:

editorial:
  revision:
  status:

verification:
  status:
  findings:
  blockers:

release:
  status:
  approved_by:
  approved_at:
```

Agents must not infer this state from previous conversations.

The Manager is authoritative.

------

# 30. Primary Workflow States

A first canonical state sequence is:

```text
TRANSLATION_PENDING
        ↓
TRANSLATION_IN_PROGRESS
        ↓
TRANSLATION_REVIEW
        ↓
TRANSLATION_APPROVED
        ↓
READER_READY
        ↓
READER_IN_PROGRESS
        ↓
SKELETON_GENERATION
        ↓
SKELETON_REVIEW
        ↓
SKELETON_APPROVED
        ↓
ARCHITECTURE_IN_PROGRESS
        ↓
ARCHITECTURE_REVIEW
        ↓
ARCHITECTURE_APPROVED
        ↓
DRAFT_IN_PROGRESS
        ↓
DRAFT_REVIEW
        ↓
DRAFT_APPROVED
        ↓
EDITING_IN_PROGRESS
        ↓
FINAL_VERIFICATION
        ↓
HUMAN_REVIEW
        ↓
MANUAL_APPROVED
```

Exception states may include:

```text
BLOCKED
REVISION_REQUIRED
REVIEW_REQUIRED
UPSTREAM_CHANGED
TRANSLATION_REQUIRES_ATTENTION
READER_REQUIRES_ATTENTION
SKELETON_REQUIRES_ATTENTION
ARCHITECTURE_REQUIRES_ATTENTION
DRAFT_REQUIRES_ATTENTION
```

------

# 31. Gate Enforcement

cgv-MANAGER must enforce gates rather than merely display progress.

Examples:

Reader may not begin unless:

```text
TRANSLATION_APPROVED
```

Architect may not begin unless:

```text
SKELETON_APPROVED
```

Escriba may not begin unless:

```text
ARCHITECTURE_APPROVED
```

Final release may not occur unless:

```text
FINAL_VERIFICATION = PASS
HUMAN_REVIEW = APPROVED
BLOCKERS = 0
```

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

# 35. Application-Specific Workflow Requirement

The master workflow establishes the governing process.

Each major production system should maintain its own workflow describing the detailed procedure within its authority.

At minimum:

```text
cgv-MANAGER/
    WORKFLOW.md
        Canonical CGV production workflow.

cgv-translator/
    WORKFLOW.md
        LBF translation, alignment, verification,
        approval, freeze, and export procedure.

cgv-reader/
    WORKFLOW.md
        Reading, observation, analysis,
        compilation, skeleton verification,
        and export procedure.
```

Agent instructions should separately define the precise authority and constraints of:

```text
Architect
Escriba
Editor
Verifier / Specialist roles as required
```

------

# 36. Current Process-Development Priority

The highest current workflow-development priority is:

**cgv-translator**

The translation and alignment of Daniel provided substantial practical experience that must now be converted into a repeatable procedure.

Before the next major translation project, the Translator workflow should define:

1. project initialization;
2. source preparation;
3. translation unit;
4. translation sequence;
5. alignment sequence;
6. handling of difficult alignment relationships;
7. automated validation;
8. human/linguistic validation;
9. verse-level completion criteria;
10. chapter-level review;
11. book-level consistency review;
12. issue classification;
13. escalation procedure;
14. approval requirements;
15. versioning;
16. freeze procedure;
17. export contract with cgv-MANAGER.

The objective is to capture what was learned through Daniel so that the next book does not depend on remembering how Daniel was done.

The process itself must become part of the system.

------

# 37. Final Principle

The CGV workflow is designed to preserve fidelity through controlled responsibility.

Each stage must do its own work.

Each stage must preserve the evidence produced before it.

Each stage must be explicit about uncertainty.

Each stage must produce an artifact that can be traced to its inputs.

And no manual is final until the complete chain from source to release has been verified and approved.