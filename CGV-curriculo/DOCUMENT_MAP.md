# CGV — Document Map

**Status:** normative
**Purpose:** one home for every rule.

Five documents govern CGV production. Each owns a distinct kind of rule. A document that needs
another's rule **points at it and never restates it** — a rule stated twice is a rule that will
drift, and the two copies will disagree in a way no one notices until an agent obeys the wrong one.

If you are about to add a rule, find its owner below first.

---

## 1. Who owns what

| Document | Owns | Answers |
|---|---|---|
| `cgv_hermeneutical_constitution_draft.md` | Non-negotiables · the three observation layers · drift tests · heading discipline · genre | **Why**, and what may never happen |
| `WORKFLOW.md` | Ownership rule · system responsibilities · artifact chain · phase narrative · traceability · definition of done | **What** must happen, in what order, and who owns each stage |
| `STATE_MODEL.md` | Gate IDs · gate statuses · transitions · finding model · severity · disposition · blockers · provenance · release status | **Every enumerated value.** The machine contract |
| `MANUAL_STANDARD.md` | Markers · hierarchy · clause structure · commentary · slides · content standard · agent clearance · report protocol | **How** a manual is built and what it may contain |
| `contracts/` | Per-boundary evidence contracts (Gate 0 today) | What evidence a specific handoff requires |
| `config/models.yaml` | Model tiers | Which runtime and model each tier uses |

Book-specific rules live in `{NN.Curso}/spec.md` and never here. If a rule mentions a book name,
it is in the wrong file.

`{NN.Curso}/blocks.md` is the book's literary-unit inventory — Constitution Layer 3. **Arquitecto
proposes it; the human approves it; no agent writes it.** Every architectural decision must be
defensible from it, and `scripts/verify-blocks.py` is its deterministic witness.

---

## 2. The vocabulary registry

**`STATE_MODEL.md` is the sole authority for every enumerated value in the system.** No other
document may define, extend, or restate these lists.

| Vocabulary | Defined in |
|---|---|
| Gate IDs — `G0_ALIGNMENT` … `G10_RELEASE` | STATE_MODEL §5 |
| Gate statuses — `BLOCKED` `NOT_STARTED` `READY` `RUNNING` `REVIEW_REQUIRED` `FAIL` `PASS` `STALE` `SKIPPED` | STATE_MODEL §6 |
| Allowed transitions | STATE_MODEL §9 |
| Project statuses — `ACTIVE` `PAUSED` `BLOCKED` `RELEASED` `ARCHIVED` | STATE_MODEL §4 |
| Finding types | STATE_MODEL §14 |
| Finding severity — `CRITICAL` `HIGH` `MEDIUM` `LOW` `INFO` | STATE_MODEL §15 |
| Finding status | STATE_MODEL §16 |
| Finding disposition | STATE_MODEL §17 |
| Blocker model | STATE_MODEL §18 |
| Release status — `NOT_RELEASED` `CANDIDATE` `APPROVED` `RELEASED` `REVOKED` | STATE_MODEL §24 |
| Provenance record shape | STATE_MODEL §22 |

---

## 3. Collisions resolved

These rules existed in more than one document. The owner keeps the rule; the others now point.

| Rule | Was in | Owner now | Why |
|---|---|---|---|
| Gate numbering | WORKFLOW (Gates 0–4) · STATE_MODEL (G0–G10) | **STATE_MODEL** | Both used the number 1 for different gates: WORKFLOW's "Gate 1 — Skeleton Approval" vs `G1_COMPILE`. The G-series is implemented in `manager/` and referenced by `contracts/GATE0_CONTRACT.md`; the prose numbering is retired |
| Finding severity | WORKFLOW §24 (`BLOCKER` / `REVIEW_REQUIRED` / `WARNING` / `PASS`) · STATE_MODEL §15 | **STATE_MODEL** | Two scales cannot both be the severity of one finding |
| Finding disposition | WORKFLOW §23 · STATE_MODEL §17 | **STATE_MODEL** | STATE_MODEL's list is a superset and is what state records |
| Workflow states | WORKFLOW §30 (`TRANSLATION_PENDING` …) | **STATE_MODEL** | Replaced by project status + gate status + release status, which the manager computes |
| State file shape | WORKFLOW §29 | **STATE_MODEL §3** | One schema |
| Structured agent results | WORKFLOW §25 | **STATE_MODEL §13** | The finding object is the return shape |
| Dependency, staleness, regeneration | WORKFLOW §27–28 | **STATE_MODEL §12** | The manager computes invalidation from declared dependencies |
| Universal principles | MANUAL_STANDARD §2 | **Constitution §1.2 + WORKFLOW §34** | Three overlapping lists of principles were three chances to cite the weakest one |
| Release requirements | MANUAL_STANDARD §9 | **STATE_MODEL §25 + WORKFLOW §33** | State decides eligibility; WORKFLOW defines done |
| Model tiering | MANUAL_STANDARD §6 | **`config/models.yaml`** | A table in prose and a config file will diverge. The *principle* — tier by risk and type of judgment, never by how hard the job sounds — stays in MANUAL_STANDARD |
| Verification chain | MANUAL_STANDARD §8 | **STATE_MODEL §5** gates, **MANUAL_STANDARD** the per-gate procedure | The chain is `G2_MECHANICAL` → `G3_TEXTUAL` → `G4_SPECIALISTS` → `G8_FINAL_VERIFY` |
| Agent clearance | WORKFLOW §6 · MANUAL_STANDARD §5 | **WORKFLOW** owns what each system is *for*; **MANUAL_STANDARD** owns what each agent may *edit* | Clearance is about the manuscript, and `check-authority.py` enforces it there |

---

## 4. Editor and Corrector

Three documents described three different Editors. Resolved by splitting the role, which is what
WORKFLOW §6.6 already described and what practice already does:

| Role | Clearance | Tier |
|---|---|---|
| **Editor** | Mechanical only: whitespace, markdown corruption, structural damage, marker violations, footnote integrity. May not change wording | `local_small` — *Editor is allowed to be stupid* |
| **Corrector** | Prose: `>` commentary, pacing, transitions, `### En síntesis` wording, `Actores principales` → prose, stock-closer removal. May not add facts, change Scripture, or introduce analysis | `strong_writer` |

Neither may resolve a tension the text leaves open, add a lexical, historical or theological claim,
or touch protected content. `G7_EDITORIAL` covers both; each records its own provenance entry.

---

## 5. The pipeline, named once

```
cgv-translator          LBF translation + alignment          → G0_ALIGNMENT
Reader                  reading and observation
Observer (Jason assists) clause marking → progress JSON
Compiler                Compiled Skeleton                    → G1_COMPILE
                        mechanical / textual / specialist    → G2 · G3 · G4
Arquitecto              architecture, telos                  → G5_ARCHITECTURE
Escriba                 manual prose                         → G6_WRITING
Editor + Corrector      mechanical + prose                   → G7_EDITORIAL
Verificador             final verification                   → G8_FINAL_VERIFY
Human                   review and release                   → G9 · G10
```

Observer and Compiler are stages, not conveniences. Any document that goes from Reader analysis
straight to Compiled Skeleton is describing a pipeline that no longer exists.

---

## 6. Amending this map

Adding a rule means naming its owner here first. Moving a rule between documents means updating
section 3. A document that grows a section belonging to another document is a defect, not a draft.
