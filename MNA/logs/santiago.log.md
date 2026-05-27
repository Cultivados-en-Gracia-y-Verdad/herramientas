# Santiago — ROOTS Work Log

> **Purpose:** Document, step-by-step, the work performed to derive an objective structure for the book of *Santiago* using ROOTS principles.
>
> **Non-negotiables**
> - Use **CGV controlled sources only**.
> - Produce **observation-only** outputs (no theology, no interpretation, no application).
> - Maintain **traceability**: every dataset element must point to explicit evidence in the Greek text or morphology.

---

## 0. Scope

This log covers:

1. Creating new datasets for **Subject** and **Movement**.
2. Building the **Trunk** (predicate-anchor chain).
3. Deriving whole-book structure: **H0 / H1 / H2**.
4. Preparing to write the **CGV Santiago manual** (Spanish; Filemón-format) after the structure is locked.

---

## 1. Controlled sources (authoritative)

- Greek morphology (MorphGNT): `MNA/SOURCES/MorphGNT/`
- Greek text (SBLGNT): `MNA/SOURCES/SBLGNT/`
- Spanish Bible (NBLA): `MNA/SOURCES/NBLA/`

For Santiago specifically (working copies in sandbox during development):
- `santiago-morphgnt.txt`
- `santiago.md` (SBLGNT)
- `santiago.nbla.md` (NBLA)

---

## 2. Existing ROOTS-adjacent datasets (already present)

These are inputs used for trunk/structure work:

- `MNA/datasets/finite-verbs/santiago.jsonl` (Stage 1)
- `MNA/datasets/predicate-anchors/santiago.jsonl` (Stage 2)

Deprecated / not trusted:
- prior Stage 3 subject file (not used).

---

## 3. New datasets to create (this project)

### 3.1 Subject dataset (predicate-anchor only)

**Path:** `MNA/datasets/subject/santiago.jsonl`

**Scope decision:** Subject records attach to **predicate anchors only** (Stage 2), not all finite verbs.

**Allowed evidence sources:**
- Greek token(s) present in the text (explicit subject)
- Finite-verb morphology (person/number) when an explicit subject token is not present (morphology-derived subject)

**Disallowed:** inferred semantic subjects, topical subjects, “implied by context,” etc.

---

### 3.2 Movement dataset (boundary markers only)

**Path:** `MNA/datasets/movement/santiago.jsonl`

**Definition:** Movement markers are **boundary markers only** (not logical role tags).

**Movement v1 marker types (enabled):**
1. Connector boundary (explicit Greek connector token)
2. Mood boundary (imperative vs non-imperative, from morphology)
3. Person/number boundary (finite-verb morphology shift)

**Disallowed:** purpose/reason/result labeling; topic-change labeling.

---

## 4. Proposed trunk (human proposal, comparison artifact)

A Spanish trunk proposal was provided and will be used as a comparison/validation target against a mechanically derived trunk from `predicate-anchors/santiago.jsonl`.

Status: received.

---

## 5. Decision log

### Decision 001 — Logging strategy
- Output a separate Markdown file: `santiago.log.md`.

### Decision 002 — Workflow order
- Build whole-book structure first (H0/H1/H2), then proceed phrase-by-phrase.

### Decision 003 — Movement definition
- Movement = boundary markers only.

### Decision 004 — Subject dataset scope
- Subject records attach to predicate anchors only.

### Decision 005 — Movement v1 marker types
- Enable connector-boundary + mood-boundary + person/number-boundary.

---

## 6. Open questions (to be resolved later)

1. Movement expansion (time/location/speech boundaries): define if/when to include.
2. Exact rules for mapping trunk segments → H2, and H2 groupings → H1/H0.
3. Manual front-matter fields for Santiago (author, cover, version, date, subtitle).
