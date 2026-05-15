```
# MNA — Mechanical New Testament Analysis

MNA is a strictly mechanical linguistic extraction system.

Its purpose is NOT:
- commentary,
- interpretation,
- theology,
- summaries,
- themes,
- outlines,
- or inferred structure.

Its purpose IS:
- reproducible extraction,
- visible outputs,
- verifiable datasets,
- and mechanically regeneratable analysis.

---

# CORE PRINCIPLE

If a dataset cannot be reproduced from source files by a single documented script,
the dataset does not exist.

No exceptions.

---

# FAILURE THAT MUST NEVER HAPPEN AGAIN

The previous project failed because:

- partial datasets were treated as completed systems,
- invisible infrastructure was mistaken for usable output,
- render layers were assumed instead of proven,
- reproducibility was lost,
- provenance became unclear,
- and outputs were claimed before they existed.

This repository exists specifically to prevent that failure.

---

# NON-NEGOTIABLE RULES

## 1. OUTPUT-FIRST DEVELOPMENT

Nothing is considered complete unless:

```bash
command
→ visible output
```

works end-to-end.

Example:

```
do 1corintios
```

must actually render the requested artifact.

Not theoretically.
 Not partially.
 Not internally.

Visibly.

------

## 2. EVERY DATASET MUST HAVE:

### a. source

Where the data came from.

### b. producer script

Exactly which script generated it.

### c. reproducible command

The exact command used.

### d. deterministic output

Running the command again must reproduce the dataset.

------

## 3. IF IT CANNOT BE REGENERATED, DELETE IT

No mystery files.
 No orphan datasets.
 No unexplained outputs.
 No manually drifting artifacts.

------

## 4. NEVER CLAIM COMPLETION EARLY

The following are NOT equivalent:

- finite verbs
- predicates
- clauses
- continuity
- trunk
- movement
- ROOTS output

Each stage must be visibly validated independently.

------

## 5. EACH STAGE MUST PASS WHOLE-BOOK TESTS

Verse-level success means nothing.

A stage only exists if it can process:

- an entire epistle,
- consistently,
- reproducibly,
- visibly.

------

# REQUIRED PIPELINE ORDER

## Stage 1 — Finite Verbs

Goal:
 Extract ONLY finite verbs mechanically from MorphGNT.

Required visible output:

```
do-finite-verbs 1corintios
```

------

## Stage 2 — Predicate Clauses

Goal:
 Resolve actual predicate clauses from finite verbs.

This stage is NOT complete until:

```
do-predicates 1corintios
```

renders a whole-book visible output.

------

## Stage 3 — Clause Relationships

Only begins AFTER predicates are validated.

------

## Stage 4 — Trunk Reduction

Only begins AFTER clause relationships are validated.

------

## Stage 5 — Subject Continuity

Only begins AFTER trunk reduction is stable.

------

## Stage 6 — Movement Detection

Only begins AFTER continuity is stable.

------

# ABSOLUTE RULE

No downstream layer may be trusted until the previous layer is visibly reproducible.

------

# REQUIRED DIRECTORY STRUCTURE

```
mna/
├── README.md
├── sources/
├── datasets/
├── outputs/
├── scripts/
└── docs/
```

------

# REQUIRED DATASET FORMAT

Every dataset must include metadata:

```
{
  "source": "...",
  "producer_script": "...",
  "producer_command": "...",
  "generated_at": "...",
  "version": "..."
}
```

------

# PHILOSOPHY

Mechanical truth is more important than progress claims.

Visible outputs are more important than architecture.

Reproducibility is more important than complexity.

If the system cannot visibly regenerate the output,
 the system has failed.

```
And here is the continuation/startover document.

```markdown
# CONTINUATION — START OVER CORRECTLY

The previous attempt failed because the project advanced beyond validated foundations.

The restart must be radically simpler.

---

# WHAT ACTUALLY EXISTS

At the moment, the only clearly validated layer is:

- finite verb extraction from MorphGNT.

Everything else must be treated as experimental until visibly reproducible.

---

# WHAT MUST HAPPEN NEXT

## Step 1

Rebuild finite verb extraction cleanly.

Requirements:
- one script,
- one command,
- one deterministic output.

Example:

```bash
python3 scripts/build_finite_verbs.py 1corintios
```

Output:

```
datasets/finite-verbs/1corintios.jsonl
```

------

## Step 2

Validate whole-book finite verbs manually.

No next stage until this passes visibly.

------

## Step 3

Build REAL predicate clauses.

NOT:

- attached spans,
- inferred phrases,
- loose predications.

REAL predicate boundaries.

------

# CRITICAL DISCIPLINE

Never say:

- “almost,”
- “foundation,”
- “support layer,”
- “partially stable.”

Either:

- the output exists,
   or:
- it does not exist.

------

# VALIDATION STANDARD

The ONLY valid proof is:

```
command
→ whole-book output
```

------

# REMEMBER

The goal is not:

- cleverness,
- architecture,
- diagnostics,
- experiments.

The goal is:

- reproducible visible linguistic data.