# MNA Stage 4 — Full Audit Suite Plan

## Purpose

Stage 4 now requires a full-system audit suite.

The goal is no longer merely:

- detecting dependency environments,
- reducing unresolved predicates,
- or building candidate datasets.

The goal is now:

- verifying that approved eliminations are grammatically defensible,
- exposing overclassification,
- preserving anchor stability,
- protecting against drift,
- and ensuring downstream ROOTS stages remain mechanically trustworthy.

This audit suite is intentionally conservative.

No audit script is allowed to:

- modify Stage 1–3,
- alter predicate anchors,
- create trunk,
- create [S],
- create [M],
- create labels,
- create sections,
- create titles,
- or reinterpret the text.

The suite is diagnostic only.

# Audit Suite Structure

## scripts/stage4/audit/

### 1. validate_stage4_dataset_integrity.py

Purpose:

- verify dataset integrity across all Stage 4 datasets.

Checks:

- row counts,
- duplicate predicate_anchor_id values,
- ordering,
- metadata inheritance,
- approved/quarantined separation,
- source existence,
- schema consistency,
- stable anchor identity.

Outputs:

- PASS / FAIL,
- detailed mismatch report.

### 2. audit_false_eliminations.py

Purpose:

- inspect all NO rows.

Input:

- datasets/independent-clause-candidates/.jsonl

Grouped by:

- detector source,
- mood,
- morphology,
- local environment.

Classification buckets:

- SAFE_DEPENDENT
- POSSIBLE_FALSE_ELIMINATION
- UNCLEAR

Important: This script does NOT automatically reclassify. It only surfaces suspicious eliminations.

### 3. audit_unresolved_residue.py

Purpose:

- analyze remaining unresolved predicates.

Goal:

- discover repeated unresolved grammatical environments.

Metrics:

- unresolved by mood,
- unresolved by connector environment,
- unresolved by morphology,
- unresolved by local token patterns,
- unresolved by verse density.

Output:

- environment frequency report.

This is the primary detector-discovery tool.

### 4. audit_mood_distribution.py

Purpose:

- detect suspicious elimination bias.

Metrics:

- indicative counts,
- subjunctive counts,
- imperative counts,
- infinitive counts,
- participle counts.

Compared across:

- total predicates,
- eliminated predicates,
- unresolved predicates.

Danger indicators:

- excessive imperative elimination,
- excessive indicative elimination,
- overbroad subjunctive removal,
- morphology imbalance.

### 5. audit_subordinator_environments.py

Purpose:

- verify subordinator handling.

Grouped by subordinator:

- ἵνα
- ὅτι
- ὥστε
- εἰ
- ὅταν
- καθώς
- ἐπειδή
- ἕως
- etc.

Metrics:

- eliminated predicates,
- unresolved predicates,
- matrix/dependent ambiguity,
- mood distribution,
- overlap with other detectors.

Important: This audit exposed the current broad-subordinator drift.

### 6. audit_detector_precision.py

Purpose:

- evaluate detector trustworthiness.

Per detector:

- raw hits,
- unique hits,
- overlap rate,
- exclusive hits,
- false-elimination suspicion rate,
- unresolved reduction contribution.

Expected outcome:

- identify high-trust detectors,
- quarantine unstable detectors.

### 7. audit_anchor_stability.py

Purpose:

- ensure Stage 4 never mutates predicate identity.

Checks:

- predicate_anchor_id stability,
- token index stability,
- anchor order stability,
- reference stability,
- morphology inheritance stability.

This protects downstream ROOTS phases.

# Approved vs Quarantined Logic

## Approved Detectors

Allowed to influence official elimination counts.

Current candidates:

- absolute-dependency-candidates
- relative-dependency-candidates
- content-clause-dependency-candidates

## Quarantined Detectors

Allowed for audit only.

Current:

- subordinator-dependency-candidates

Reason:

- mixes subordinate environments with matrix clauses.

Must be split into narrower detectors before approval.

# Audit Philosophy

## Core Rule

Stage 4 is NOT trying to prove:

- “this clause is definitely independent.”

Stage 4 is trying to prove:

- “this predicate is mechanically non-independent.”

Anything not safely eliminated remains:

- UNRESOLVED_CANDIDATE.

This preserves mechanical conservatism.

# Expected End State

A fully mechanical Stage 4 probably ends with:

- NO
- UNRESOLVED_CANDIDATE
- possibly later: HIGH_CONFIDENCE_INDEPENDENT

It may never safely reduce all predicates to binary independent/dependent.

That is acceptable.

The system must prefer:

- precision,
- auditability,
- and stability,

over forced completeness.

# Recommended Immediate Execution Order

1. validate_stage4_dataset_integrity.py
2. audit_false_eliminations.py
3. audit_detector_precision.py
4. audit_mood_distribution.py
5. audit_subordinator_environments.py
6. audit_unresolved_residue.py
7. audit_anchor_stability.py

# Current Strategic Assessment

The system is now in a much healthier state than earlier.

Major breakthrough:

subordinator presence ≠ automatic predicate dependency

That distinction prevented broad overclassification.

The audit suite now becomes the mechanism that keeps Stage 4 from drifting again.

I’ve laid out the full Stage 4 audit suite architecture and execution order in a dedicated audit document.

The key shift is:

- Stage 4 is now treated as an auditable mechanical system,
- not just a detector pipeline.

The suite focuses on:

- false eliminations,
- detector precision,
- subordinator drift,
- unresolved residue,
- mood distribution,
- anchor stability,
- and approved vs quarantined detector separation.

Most important:
 the audit philosophy is now explicitly conservative:

- eliminate only when grammar safely forces non-independence,
- otherwise remain unresolved.