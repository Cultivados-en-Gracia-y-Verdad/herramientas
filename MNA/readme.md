# MNA — NBLA ↔ SBLGNT Alignment

MNA is a strict alignment project between:

- SBLGNT Greek text
- NBLA Spanish text
- MorphGNT morphology

## Purpose

The purpose of MNA is to align NBLA to SBLGNT at the token/span level.

MNA does not interpret the text.

MNA does not create a reader.

MNA does not create a lexicon.

MNA does not perform ROOTS analysis.

It only produces verified alignment data.

## Core Rule

Greek is the control text.

NBLA is the aligned Spanish text.

MorphGNT supplies morphology for the Greek tokens.

## Output Goal

Each SBLGNT token must have:

- Greek token
- lemma
- morphology
- NBLA aligned word/span
- alignment type
- source

## Alignment Types

- direct
- expanded
- merged-forward
- merged-backward
- missing

## Non-Negotiables

- Do not interpret.
- Do not smooth NBLA.
- Do not infer theology.
- Do not build downstream tools yet.
- If alignment cannot be verified, mark it clearly.

## Project Boundary

MNA ends when the alignment is verified.

## COVERAGE GUARANTEE (NON-NEGOTIABLE)

MNA enforces full bidirectional coverage between SBLGNT and NBLA.

### 1. Greek Coverage

Every Greek token must be:

- aligned to NBLA, or
- marked as supplied

No Greek token may remain unclassified.

---

### 2. NBLA Coverage

Every NBLA word must be:

- mapped to one or more Greek tokens, or
- explicitly marked as:
  - function-added
  - restructuring
  - helper

  No NBLA word may remain unused.

---

### 3. No Duplication

A Spanish word cannot be mapped multiple times unless explicitly marked as shared.

---

### 4. Hard Validation

At the end of each verse:

- All Greek tokens must be accounted for
- All NBLA words must be accounted for

If either fails → the alignment fails