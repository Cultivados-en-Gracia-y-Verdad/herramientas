# CGV Workflow Manager — State Model

**Status:** Draft specification  
**Scope:** All CGV manual projects  
**Version:** 0.1  
**Depends on:** `WORKFLOW.md`

---

## 1. Purpose

This document defines the state model used by the CGV Workflow Manager.

The manager must always be able to answer:

1. What project is this?
2. What source and alignment revision does it depend on?
3. What artifact is current?
4. Which workflow gate is active?
5. Which gates have passed?
6. What findings remain open?
7. What blockers prevent progress?
8. What action is allowed next?
9. Is regeneration required?
10. Is release permitted?

The manager must never infer these answers from chat history or model memory. They must come from project state.

---

## 2. Core State Objects

Each project contains six core objects:

```text
Project
├── Source
├── Alignment
├── Artifact
├── Gates
├── Findings
└── Provenance
```

---

## 3. Project State

Each manual project has one canonical state file:

```text
projects/<project-id>/state.yaml
```

Minimum shape:

```yaml
project:
  id: ""
  title: ""
  workflow_version: ""
  manual_spec: ""
  status: ACTIVE

source:
  name: LBF
  path: ""
  revision: ""
  checksum: ""
  validated: false

alignment:
  path: ""
  revision: ""
  checksum: ""
  status: NOT_STARTED
  validated_at: null
  validated_by: []

compiler:
  name: ""
  version: ""
  last_run_at: null

artifact:
  path: ""
  revision: ""
  checksum: ""
  generated_from_source_revision: ""
  generated_from_alignment_revision: ""
  generated_at: null
  current: false

workflow:
  current_gate: G0_ALIGNMENT
  release_status: NOT_RELEASED
  regeneration_required: false

gates: {}

findings: []

blockers: []

provenance: []
```

---

## 4. Project Status

Allowed project-level statuses:

```text
ACTIVE
PAUSED
BLOCKED
RELEASED
ARCHIVED
```

### ACTIVE
Work may proceed according to gate rules.

### PAUSED
No automatic progression. Human intentionally paused work.

### BLOCKED
At least one blocker prevents progression.

### RELEASED
Release Gate passed and human approval is recorded.

### ARCHIVED
Project is retained but no longer active.

---

## 5. Gate IDs

The universal CGV workflow uses these gate IDs:

```text
G0_ALIGNMENT
G1_COMPILE
G2_MECHANICAL
G3_TEXTUAL
G4_SPECIALISTS
G5_ARCHITECTURE
G6_WRITING
G7_EDITORIAL
G8_FINAL_VERIFY
G9_HUMAN_REVIEW
G10_RELEASE
```

---

## 6. Gate Statuses

Every gate has exactly one status:

```text
BLOCKED
NOT_STARTED
READY
RUNNING
REVIEW_REQUIRED
FAIL
PASS
STALE
SKIPPED
```

### BLOCKED
Cannot begin because a prerequisite or blocker is unresolved.

### NOT_STARTED
Valid gate, but not yet eligible.

### READY
All prerequisites satisfied. Gate may begin.

### RUNNING
Work is currently being performed.

### REVIEW_REQUIRED
Automated/agent work completed, but human or specialist disposition is still required.

### FAIL
Gate completed and did not satisfy mandatory requirements.

### PASS
Gate completed and satisfies its requirements for the recorded revision.

### STALE
Gate previously passed, but an upstream change invalidated that pass.

### SKIPPED
Allowed only when the workflow or manual specification explicitly marks the gate unnecessary. Human reason must be recorded.

---

## 7. Initial State

A new project begins:

```yaml
workflow:
  current_gate: G0_ALIGNMENT
  release_status: NOT_RELEASED
  regeneration_required: false

gates:
  G0_ALIGNMENT: READY
  G1_COMPILE: BLOCKED
  G2_MECHANICAL: BLOCKED
  G3_TEXTUAL: BLOCKED
  G4_SPECIALISTS: BLOCKED
  G5_ARCHITECTURE: BLOCKED
  G6_WRITING: BLOCKED
  G7_EDITORIAL: BLOCKED
  G8_FINAL_VERIFY: BLOCKED
  G9_HUMAN_REVIEW: BLOCKED
  G10_RELEASE: BLOCKED
```

---

## 8. Allowed Gate Progression

Normal progression:

```text
G0_ALIGNMENT
      ↓
G1_COMPILE
      ↓
G2_MECHANICAL
      ↓
G3_TEXTUAL
      ↓
G4_SPECIALISTS
      ↓
G5_ARCHITECTURE
      ↓
G6_WRITING
      ↓
G7_EDITORIAL
      ↓
G8_FINAL_VERIFY
      ↓
G9_HUMAN_REVIEW
      ↓
G10_RELEASE
```

A downstream gate cannot become `READY` until all mandatory prerequisites are `PASS`.

---

## 9. Gate Transition Rules

Allowed state transitions:

```text
NOT_STARTED → READY
READY → RUNNING
RUNNING → PASS
RUNNING → FAIL
RUNNING → REVIEW_REQUIRED
REVIEW_REQUIRED → PASS
REVIEW_REQUIRED → FAIL
FAIL → READY
PASS → STALE
STALE → READY
READY → BLOCKED
RUNNING → BLOCKED
NOT_STARTED → BLOCKED
BLOCKED → READY
```

Disallowed examples:

```text
BLOCKED → PASS
NOT_STARTED → PASS
FAIL → PASS
STALE → PASS
```

A gate must actually rerun or receive the required review before passing.

---

## 10. Gate 0 — Alignment State

`G0_ALIGNMENT` is foundational.

Required fields:

```yaml
gates:
  G0_ALIGNMENT:
    status: READY
    source_revision: ""
    alignment_revision: ""
    mechanical_validation:
      status: NOT_STARTED
      report: null
    linguistic_validation:
      status: NOT_STARTED
      reviewers: []
      report: null
    findings: []
    passed_at: null
```

Gate 0 may pass only when:

- source identity is declared;
- source revision is recorded;
- alignment revision is recorded;
- required deterministic checks pass;
- required linguistic/human validation passes;
- no blocking alignment finding remains open.

If Gate 0 fails:

```text
G1–G10 = BLOCKED
```

---

## 11. Compilation State

`G1_COMPILE` is not a content-judgment gate.

It records:

```yaml
gates:
  G1_COMPILE:
    status: BLOCKED
    compiler_version: ""
    input_source_revision: ""
    input_alignment_revision: ""
    output_artifact_revision: ""
    output_checksum: ""
    generated_at: null
```

Compilation may run only if `G0_ALIGNMENT = PASS`.

After successful compile:

```text
artifact.current = true
workflow.regeneration_required = false
G2_MECHANICAL = READY
```

---

## 12. Regeneration and Staleness

Any upstream change can invalidate downstream work.

Examples:

### Source revision changes

```text
G0_ALIGNMENT → STALE
G1_COMPILE → STALE
G2–G10 → STALE/BLOCKED
artifact.current = false
regeneration_required = true
```

### Alignment revision changes

Same invalidation rule as source revision changes.

### Architecture changes

Potentially invalidates:

```text
G6_WRITING
G7_EDITORIAL
G8_FINAL_VERIFY
G9_HUMAN_REVIEW
G10_RELEASE
```

### Writing changes

Potentially invalidates:

```text
G7_EDITORIAL
G8_FINAL_VERIFY
G9_HUMAN_REVIEW
G10_RELEASE
```

### Editorial changes

Potentially invalidates:

```text
G8_FINAL_VERIFY
G9_HUMAN_REVIEW
G10_RELEASE
```

The manager must compute invalidation from declared dependencies, not guess.

---

## 13. Finding Model

Every finding is a persistent object.

```yaml
- id: TXT-0001
  gate: G3_TEXTUAL
  type: TEXTUAL
  severity: HIGH
  status: OPEN
  location:
    file: ""
    reference: ""
    line_start: null
    line_end: null
  summary: ""
  evidence: ""
  source_revision: ""
  artifact_revision: ""
  created_by: ""
  created_at: ""
  assigned_to: ""
  disposition: null
  resolution: null
  resolved_by: null
  resolved_at: null
```

---

## 14. Finding Types

Universal types:

```text
DETERMINISTIC
ALIGNMENT
TEXTUAL
STRUCTURAL
LEXICAL
HEBREW
ARAMAIC
GREEK
HISTORICAL
OBSERVATION_INTERPRETATION
ARCHITECTURE
WRITING
EDITORIAL
PROVENANCE
RELEASE
OTHER
```

---

## 15. Finding Severity

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

### CRITICAL
Potentially invalidates source integrity, alignment, Scripture, core structure, or release.

### HIGH
Material defect that must be resolved or explicitly dispositioned before release.

### MEDIUM
Significant review item that may or may not block depending on gate rules.

### LOW
Minor issue that does not affect core meaning or integrity.

### INFO
Evidence or observation retained for audit purposes.

---

## 16. Finding Status

```text
OPEN
TRIAGED
IN_REVIEW
CONFIRMED
FALSE_POSITIVE
EXPECTED
RESOLVED
DEFERRED
SUPERSEDED
```

No finding disappears from state.

Resolved findings remain in the audit trail.

---

## 17. Finding Disposition

A finding may be dispositioned as:

```text
FIX_REQUIRED
SPECIALIST_REQUIRED
HUMAN_DECISION_REQUIRED
EXPECTED_STRUCTURE
FALSE_POSITIVE
ACCEPTED_RISK
NOT_APPLICABLE
SUPERSEDED_BY_REVISION
```

`ACCEPTED_RISK` requires explicit human authorization.

A CRITICAL finding cannot be released as `ACCEPTED_RISK` unless the workflow specification explicitly permits it.

---

## 18. Blocker Model

A blocker is separate from a finding.

A finding may create a blocker.

```yaml
- id: BLK-0001
  source_finding: TXT-0001
  gate: G3_TEXTUAL
  reason: ""
  created_at: ""
  resolved: false
  resolved_at: null
```

When an unresolved blocker exists:

```text
project.status = BLOCKED
affected downstream gates = BLOCKED
```

---

## 19. Gate Pass Conditions

A gate may pass only when:

1. required checks/reviews completed;
2. required reports recorded;
3. no unresolved blocker applies to the gate;
4. no unresolved CRITICAL finding applies to the gate;
5. HIGH findings are resolved or explicitly dispositioned according to policy;
6. inputs match the current revisions;
7. the gate result is recorded in provenance.

---

## 20. Current Gate

`workflow.current_gate` is the earliest mandatory gate that is not `PASS` or validly `SKIPPED`.

The manager computes it.

Humans may not manually set `current_gate` to bypass prerequisites.

---

## 21. Next Action

The manager should expose one recommended next action.

Examples:

```text
Validate LBF alignment
Run Compiler Generate
Run deterministic structural checks
Resolve TXT-0014
Send HIS-0007 to historical specialist
Review Arquitecto proposal
Run final verification
Perform human review
Approve release
```

If multiple tasks are possible inside the same gate, the manager may list them, but it must not recommend work from a blocked downstream gate.

---

## 22. Provenance Log

Every important action appends an immutable provenance record.

```yaml
- id: EVT-000001
  timestamp: ""
  actor: ""
  runtime: ""
  model: ""
  action: ""
  gate: ""
  input_revision: ""
  output_revision: ""
  findings_created: []
  findings_resolved: []
  notes: ""
```

Examples of actors:

```text
human
compiler
python-checker
editor
verifier
arquitecto
escriba
esp-historico
esp-hebreo
```

---

## 23. Model/Runtime Independence

State records the worker used, but state logic must not depend on a vendor.

Example:

```yaml
execution:
  agent: escriba
  runtime: claude-code
  model: sonnet
```

or:

```yaml
execution:
  agent: editor
  runtime: opencode
  model: qwen3.5-4b
```

Changing runtime/model does not change the workflow rules.

---

## 24. Release Status

Allowed values:

```text
NOT_RELEASED
CANDIDATE
APPROVED
RELEASED
REVOKED
```

### NOT_RELEASED
Default.

### CANDIDATE
All machine/agent gates passed; awaiting final human release authorization.

### APPROVED
Human approved the exact artifact revision.

### RELEASED
Artifact was published/distributed as the released revision.

### REVOKED
A previously released artifact is no longer approved because a critical issue was discovered.

---

## 25. Release Gate Conditions

`G10_RELEASE` may become `READY` only when:

```text
G0_ALIGNMENT = PASS
G1_COMPILE = PASS
G2_MECHANICAL = PASS
G3_TEXTUAL = PASS
G4_SPECIALISTS = PASS
G5_ARCHITECTURE = PASS
G6_WRITING = PASS
G7_EDITORIAL = PASS
G8_FINAL_VERIFY = PASS
G9_HUMAN_REVIEW = PASS
```

Additionally:

- artifact.current = true;
- regeneration_required = false;
- artifact checksum matches the reviewed artifact;
- no blocker remains;
- no unresolved CRITICAL finding remains;
- required HIGH findings are resolved/dispositioned;
- human approval references the exact artifact revision/checksum.

---

## 26. Human Approval

Human approval must be explicit.

```yaml
human_approval:
  approved: true
  approved_by: ""
  approved_at: ""
  artifact_revision: ""
  artifact_checksum: ""
  notes: ""
```

If the artifact changes after approval:

```text
human approval becomes stale
G9_HUMAN_REVIEW → STALE
G10_RELEASE → BLOCKED
```

---

## 27. Workflow Manager Invariants

These rules must always hold:

1. A blocked gate cannot pass.
2. A stale gate cannot pass without rerun/review.
3. A downstream pass cannot remain valid after a dependency-changing upstream revision.
4. An artifact cannot be current if its source/alignment revisions differ from current project revisions.
5. Release cannot occur without human approval.
6. Findings are never deleted from history.
7. Automated evidence cannot close a specialist-required finding without the required specialist disposition.
8. A model cannot approve its own unauthorized scope expansion.
9. A manual cannot be `FINAL` while `regeneration_required = true`.
10. Project state must be reproducible from state + provenance + referenced reports.

---

## 28. Minimal Manager Dashboard

The manager should be able to display:

```text
CGV MANAGER

Project: <name>
Workflow: <version>
Source: LBF <revision>
Alignment: PASS / FAIL / ...
Artifact: CURRENT / STALE / NONE

Current Gate: Gx — <name>
Next Action: <action>

GATES
✓ G0 Alignment
✓ G1 Compile
○ G2 Mechanical
■ G3 Textual — BLOCKED
...

OPEN FINDINGS
Critical: 0
High: 2
Medium: 5
Low: 8

BLOCKERS
- BLK-0004 ...

RELEASE
NOT_RELEASED
```

---

## 29. First Implementation Principle

The first implementation should be simple.

The manager only needs to:

1. load `WORKFLOW.md`;
2. load a project `state.yaml`;
3. validate state invariants;
4. display current status;
5. accept gate results/reports;
6. update findings/blockers;
7. compute staleness;
8. determine the next allowed action.

Agent orchestration can be added after state control works reliably.

---

## 30. Design Principle

**The manager controls progression. Agents perform work. Humans retain authority.**

No agent, model, script, or runtime is the workflow.
