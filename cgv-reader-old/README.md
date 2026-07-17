# The Reader

## Purpose

The Reader exists to help people read and participate with Scripture.

It is designed to keep the biblical text at the center while providing tools that support observation, exploration, and understanding.

The Reader does not replace the text.

It exists to serve the text.

---

## Philosophy

The Reader is built around one conviction:

> The student should receive the credit for the observation.

The software should never replace participation.

Instead, it should provide an environment where readers discover the text for themselves.

---

## Architecture

The Reader is intentionally modular.

Its core responsibility is reading Scripture.

Additional capabilities are added as independent modules.

Current modules include:

- **R** — Reader
- **O** — Observation
- **O** — Organization
- **T** — Translation
- **S** — Study

Each module extends the Reader without changing its primary purpose.

---

## Design Principles

Every feature should:

- Keep the biblical text central.
- Encourage participation.
- Be grounded in observable data.
- Remain transparent.
- Never hide reasoning from the user.

If a feature replaces participation instead of encouraging it, it does not belong in The Reader.

---

## Development

The Reader grows one capability at a time.

Each new capability must demonstrate that it genuinely helps readers engage the biblical text before becoming part of the project.

The text remains the teacher.

The Reader simply provides the environment.

# O Reader Principles

## Purpose

O is not designed to interpret Scripture for the student.

It is designed to help the student observe the text through objective participation.

Every feature in O must satisfy one question:

> Does this help the student observe something that can be demonstrated from the text?

If not, it does not belong in O.

---

## Development Philosophy

O is built one observation at a time.

Each observation becomes a "brick."

A brick is accepted only when it satisfies three conditions:

1. It is objective.
2. It can be demonstrated from the text.
3. It produces a useful observation for the reader.

If a brick fails any of these, it is removed.

---

## Current Bricks

### Brick 1
Finite verbs.

Produces:
- grammatical anchors

---

### Brick 2
Commands (imperatives).

Produces:
- visible commands
- command recipients

---

### Brick 3
Dependent clause introducers.

Current candidate list:

- ἵνα
- ὅτι
- εἰ
- ἐάν
- ὅταν
- ἐπειδή
- ἐπεί
- καθώς
- ὡς
- πρίν

These are included because they introduce dependent clauses.

Each candidate is verified by examining its occurrences in the Greek New Testament.

If a word does not consistently function as a dependent-clause introducer, it is removed from this list.

The text determines the list.

The list does not determine the text.

---

### Brick 4
Spanish clause spans.

The student selects the words belonging to each finite verb.

This produces visible clause units without requiring grammatical terminology.

---

## Guiding Principle

Every brick leaves behind a visible artifact.

Nothing depends upon hidden AI reasoning.

The student should always be able to see exactly what has been observed and how it was produced.

O exists to increase participation with the biblical text, not dependence upon the software.
## Tools

The Reader does not contain features.

It provides tools.

A tool assists the reader, then quietly steps aside.

Tools should never become the focus of the reading experience.

The biblical text remains the center.
## Every Tool Answers One Question

A tool should exist to help the reader answer a single observable question.

Examples:

Finite Verbs
→ Where are the finite verbs?

Commands
→ Where are the commands?

Command Recipients
→ Who receives the commands?

Clause Introducers
→ Which words introduce dependent thoughts?

Clause Builder
→ What words belong to this finite verb?

Skeleton
→ What remains when dependent thoughts are hidden?