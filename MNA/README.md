# MNA — Mechanical New Testament Analysis

MNA is a strictly mechanical linguistic extraction system.

Its purpose is NOT:
- commentary,
- interpretation,
- theology,
- summaries,
- themes,
- outlines,
- discourse reconstruction,
- or inferred structure.

Its purpose IS:
- reproducible extraction,
- visible outputs,
- verifiable datasets,
- auditable structure,
- and mechanically regeneratable analysis.

---

# CORE PRINCIPLE

If a dataset cannot be reproduced from source files by a single documented script,
the dataset does not exist.

No exceptions.

---

# ARCHITECTURAL FREEZE

The project is currently under:

```text
architectural correction and stabilization
```

This freeze exists to prevent interpretive drift.

The system must not:
- overclaim structure,
- collapse provisional layers into final conclusions,
- treat finite verbs as independent clauses,
- treat all predicate anchors as trunk,
- mark [S] or [M] from non-trunk clauses,
- allow connectors to generate structure,
- silently reinterpret lower layers.

---

# VERIFIED PRINCIPLES

## 1. Finite Verb ≠ Independent Clause

A finite verb is:

```text
finite-clause center candidate
```

not:

```text
independent clause
```

Dependent clauses may still contain finite verbs.

---

## 2. Predicate Anchor ≠ Trunk

A predicate anchor is:

```text
one verified finite verb
```

It is NOT:
- trunk,
- section,
- unit,
- final clause span.

---

## 3. Real Trunk = Independent-Clause Structure

The real trunk is:

```text
independent-clause structure
```

not:
- all finite verbs,
- all predicate anchors,
- all finite clauses.

---

## 4. [S] and [M] Belong Only To Trunk Clauses

`[S]` and `[M]` must be calculated only after real trunk clauses have been established.

They must not be calculated over all predicate anchors because predicate anchors include dependent finite clauses.

Therefore:

```text
No [S] or [M] before trunk extraction.
```

---

## 5. Connectors Do Not Create Structure

Connectors may:
- signal relationships,
- signal dependency,
- signal continuation,
- signal qualification.

But connectors do NOT:
- create trunk,
- create units,
- create sections,
- create titles.

---

## 6. Independency Must Not Depend Primarily On Connectors

Connector-first parsing leads rapidly to:
- interpretive drift,
- unstable restructuring,
- discourse assumptions,
- subjective dependency assignment.

Therefore:

```text
predicate completeness and independency testing must precede connector-dominant analysis
```

---

# NON-NEGOTIABLE RULES

## 1. OUTPUT-FIRST DEVELOPMENT

Nothing is considered complete unless:

```text
command
→ visible output
```

works end-to-end.

---

## 2. EVERY DATASET MUST HAVE

### source

Where the data came from.

### producer script

Exactly which script generated it.

### reproducible command

The exact command used.

### deterministic output

Running the command again must reproduce the dataset.

---

## 3. IF IT CANNOT BE REGENERATED, DELETE IT

No mystery files.
No orphan datasets.
No manually drifting artifacts.

---

## 4. NEVER CLAIM COMPLETION EARLY

The following are NOT equivalent:

- finite verbs,
- predicate anchors,
- finite clauses,
- independent clauses,
- trunk,
- subject-change markers,
- movement markers,
- units,
- titles.

Each layer must be independently validated.

---

## 5. EVERY LAYER MUST REMAIN AUDITABLE

Every downstream layer must:
- inherit from verified lower layers,
- preserve provenance,
- avoid silent reinterpretation,
- remain mechanically reproducible.

---

# CURRENT VERIFIED PIPELINE

## Stage 1 — Finite Verbs

Goal:
Extract ONLY finite verbs mechanically from MorphGNT.

Canonical commands:

```bash
python3 scripts/stage1/build_finite_verbs.py 1corintios
python3 scripts/stage1/update_verification_ledger.py 1corintios --date 2026-05-15
```

Current status:

```text
VERIFIED
```

---

## Stage 2 — Predicate Anchors

Goal:
Stabilize finite-verb anchor coordinates.

A predicate anchor is:

```text
one verified finite verb inherited from Stage 1
```

Canonical commands:

```bash
python3 scripts/stage2/build_predicate_anchors.py 1corintios
python3 scripts/stage2/validate_predicate_anchors.py 1corintios
```

Current status:

```text
VERIFIED
```

---

## Stage 3 — Anchor Skeleton Only

Goal:
Produce ordered predicate-anchor sequencing.

Current Stage 3 does NOT:
- build real trunk,
- establish independent clauses,
- establish dependent clauses,
- calculate `[S]`,
- calculate `[M]`,
- establish units.

Canonical commands:

```bash
python3 scripts/stage3/build_anchor_skeleton.py 1corintios
python3 scripts/stage3/validate_anchor_skeleton.py 1corintios
```

Current status:

```text
ANCHOR SKELETON ONLY
```

Reason:

Real trunk extraction requires:
- finite-clause analysis,
- independency testing,
- dependency theory stabilization.

`[S]` and `[M]` must wait until trunk clauses exist.

---

# FUTURE PIPELINE DIRECTION

The corrected architectural direction currently appears to be:

```text
Stage 1  finite verbs
Stage 2  predicate anchors
Stage 3  anchor skeleton only
Stage 4  finite-clause candidates
Stage 5  independency testing / predicate completeness
Stage 6  trunk extraction (independent clauses only)
Stage 7  [S] + [M] on trunk clauses only
Stage 8  connector relationships
Stage 9  labels / patterns / units
Stage 10 titles
```

This sequence remains provisional until frozen formally.

---

# REQUIRED DIRECTORY STRUCTURE

```text
MNA/
├── README.md
├── SOURCES/
├── datasets/
├── audits/
├── scripts/
└── docs/
```

---

# REQUIRED DATASET METADATA

Every dataset must include:

```json
{
  "source": "...",
  "producer_script": "...",
  "producer_command": "...",
  "generated_at": "...",
  "version": "..."
}
```

---

# ANTI-DRIFT RULE

The system must never:
- imply certainty beyond verification,
- silently reinterpret lower layers,
- present heuristic structure as verified structure,
- collapse provisional signals into final claims,
- calculate trunk-only markers over non-trunk clauses.

Every layer must remain:
- explicit,
- auditable,
- reproducible,
- mechanically constrained.

---

# PHILOSOPHY

Mechanical truth is more important than progress claims.

Visible outputs are more important than architecture.

Reproducibility is more important than complexity.

If the system cannot visibly regenerate the output,
the system has failed.



# REBUILD CHAIN:

## Stage 1

```
python3 scripts/stage1/build_finite_verbs.py 1corintios
python3 scripts/stage1/update_verification_ledger.py 1corintios --date YYYY-MM-DD
```

## Stage 2

```
python3 scripts/stage2/build_predicate_anchors.py 1corintios
python3 scripts/stage2/validate_predicate_anchors.py 1corintios
```

## Stage 3

```
python3 scripts/stage3/build_anchor_skeleton.py 1corintios
python3 scripts/stage3/validate_anchor_skeleton.py 1corintios
```

## Stage 4 (current reviewed layer)

```
python3 scripts/stage4/rebuild_stage4_book.py 1corintios
```

That is the real current rebuild path.

FULL REBUILD COMMAND:

```
python3 scripts/rebuild/rebuild_stages_1_4_book.py \
1corintios \
--date 2026-05-15

```
