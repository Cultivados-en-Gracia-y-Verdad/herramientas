# CGV Translator Design Audit

**Reviewed:** `WORKFLOW(3).md` v0.3 and `CONSTITUTION(1).md`  
**Verdict:** The intent is sound, but the design is not operationally complete. It describes a desirable process without specifying enough controls to run, audit, or implement it consistently.

## Executive finding

The documents confuse three layers:

1. governing principles;
2. production policy;
3. implementation behavior.

As a result, the workflow repeats the same sequence many times while leaving the hard questions unanswered: who may approve, what evidence a gate consumes, what record proves a pass, how stale approvals are detected, how exceptions are resolved, and exactly what constitutes a releasable artifact.

The redesign keeps the useful intent and replaces the narrative process with a small state machine, explicit records, role separation, deterministic invalidation, and release criteria.

## What failed

### 1. Gates exist in name only

G0A and G0B have review questions and labels, but no required input, output record, reviewer identity, timestamp, revision binding, evidence reference, or acceptance threshold. An `APPROVED` string can therefore exist without proving what was reviewed.

### 2. Status vocabulary is inconsistent

The document alternates among `APPROVED`, `PASS`, `VERIFIED`, `TRANSLATION_APPROVED`, “complete,” and “ready.” Negative states also differ between gates without a common model. This creates needless branching in code, reports, and user interfaces.

### 3. Approvals are not bound to revisions

The text says affected work must be reverified, but it never defines the immutable revision identifiers to which a decision applies. Without that binding, stale approvals cannot be detected reliably.

### 4. “Affected work” is undefined

The invalidation principle is correct, but scope is left to judgment. There is no deterministic rule for a translation edit, source change, tokenization change, alignment edit, investigation decision, or book-wide policy change.

### 5. Roles and authority are missing

“Translator,” “producer,” “reviewer,” human approval, AI assistance, Manager, and repositories are mentioned, but their permissions and separation requirements are not defined. The system cannot enforce independence or determine who may release.

### 6. Evidence is encouraged but not specified

Investigations are described as a research journey, not as a record with required fields. There is no minimum evidence package, decision status, affected scope, or linkage from a translation revision to the decision supporting it.

### 7. Completion criteria are circular

The checklists say verification must be complete and no blocker may remain, but “complete” and “blocker” are not objectively defined. They cannot serve as machine-checkable release rules.

### 8. Publication has no integrity contract

The workflow says “build,” “publish,” and “verify,” but does not require an artifact identifier, manifest, checksum, source revision, schema version, or reproducible build. Manager cannot prove it received the approved bytes.

### 9. The operating unit is oversimplified

“Verse by verse” is useful for navigation but insufficient for dependencies. Translation, source tokens, alignments, investigations, and book-level decisions may have different scopes. Treating the verse as the only unit hides cross-verse impact.

### 10. Exception handling is absent

`ESCALATE` is named but has no owner, resolution path, allowed terminal outcomes, or release effect. Rejection, waiver, unresolved research, reviewer disagreement, and source defects are not handled.

### 11. The workflow is excessively repetitive

The same happy path appears in the core sequence, working unit, chapter progress, publication, Manager handoff, definitions of done, non-negotiable rules, and canonical summary. Repetition makes contradictions more likely without adding control.

### 12. The constitution is partly redundant and partly unsafe

Several principles restate one another: textual authority, observation, evidence, transparency, explainability, and institutional memory. “Every significant decision” is undefined. “Mechanical work belongs to software” is too absolute; software may assist judgment, while humans must retain accountability. “The biblical text initiates every investigation” may also exclude legitimate triggers such as reviewer findings, consistency checks, or data defects.

## What is worth keeping

- accountability to the declared source text;
- human responsibility for final decisions;
- separate translation and alignment review;
- documented non-routine decisions;
- narrow invalidation instead of restarting unaffected work;
- book-level consistency review;
- immutable released revisions;
- one canonical downstream artifact.

Everything else should be replaced by the redesigned documents.

## Redesign decisions

| Problem | Replacement |
| --- | --- |
| Narrative sequence | Explicit state machine |
| Ambiguous gate labels | Common `PENDING`, `PASS`, `CHANGES_REQUIRED`, `BLOCKED` statuses |
| Stale approvals | Decisions bound to exact input revision IDs |
| Vague evidence | Required gate and investigation record fields |
| Undefined change impact | Deterministic invalidation matrix |
| Missing ownership | Named roles and permissions |
| Circular definition of done | Machine-checkable verse and book predicates |
| Unverifiable release | Manifest, checksum, schema version, and approved revision set |
| Repetitive policy | One canonical workflow plus concise constitution |

## Discard list

Discard the following from the old design:

- all duplicate diagrams and repeated happy-path summaries;
- gate-specific status vocabularies;
- prose-only approval claims;
- unbound or mutable approval records;
- undefined `ESCALATE` states;
- blanket claims about what software or investigations may do;
- completion checklists that cannot be evaluated from stored data;
- release steps that do not identify the exact approved artifact.

The original files should remain only in version history, not as active policy.
