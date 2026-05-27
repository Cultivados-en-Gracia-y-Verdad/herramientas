# MNA — Aligned Corpus Workflow

## Purpose

MNA exists to create a validated alignment layer between:


- Greek New Testament text (SBLGNT)
- Spanish NBLA translation
- Morphological Greek data (MorphGNT)

The goal is not theological interpretation.
The goal is structured alignment data.

This alignment layer becomes the foundation for:

- aligned readers
- ROOTS processing
- clause analysis
- connector analysis
- finite verb extraction
- future dataset tooling
- future presentation and reading tools

---

# Phase Workflow

## 1. Align Greek ↔ Spanish

### Goal

Produce a complete TSV alignment between:

- Greek tokens
- Spanish tokens

Each Greek token must:

- map to Spanish text
- or intentionally remain missing

Each Spanish token must:

- be fully accounted for
- never silently omitted

Validation is mandatory.

### Core Files

```text
Greek tokens:
data/g-tokens/<book>/

Spanish tokens:
data/s-tokens/<book>/

Alignments:
data/alignments/<book>/
```

### TSV Structure

```text
BOOK
CH
VS
G_IDX
GREEK
NBLA_IDX
NBLA_TEXT
ALIGNMENT
```

### Alignment Types

```text
 direct
 expanded
 shared
 merged-forward
 merged-backward
 positional
 missing
```

### Validation Standard

A book is only considered complete when:

```text
SUMMARY: ALL PASS
```

---

## 2. Generate Aligned Reader

### Goal

Transform validated TSV data into a readable alignment resource.

The aligned reader shows:

- Greek verse
- NBLA verse
- token alignment table
- alignment behavior

### Script

```bash
python3 scripts/export_aligned_reader.py <book>
```

### Output

```text
data/exports/<book>-aligned-reader.md
```

### Purpose

This becomes:

- a readable alignment reference
- a debugging tool
- a dataset inspection tool
- a future reader foundation

---

## 3. Generate ROOTS Dataset

### Goal

Use validated alignment data to produce:

- finite verb extraction
- connector extraction
- clause structures
- reduction structures
- trunk analysis
- ROOTS processing

The alignment layer allows:

- Greek-driven structure
- Spanish display support
- accurate token correspondence

### Future Output

```text
ROOTS-ready dataset files
```

---

## 4. Build Reusable Alignment Knowledge

### Goal

Learn stable alignment behaviors from validated books.

Examples:

```text
θεοῦ → de Dios
ἵνα → para que
ἐν → en
```

Rules are derived from:

- validated TSVs
- repeated stable patterns
- manually verified alignments

### Important Principle

Rules must emerge from validated data.

Not from speculation.

---

## 5. Expand Book-by-Book

### Goal

Scale carefully using:

- validated books
- trusted alignment patterns
- stable tooling

Books should be completed individually.

Each completed book becomes:

- a trusted dataset
- a regression test
- a future training source

---

# Current Status

## Completed

### Filemón

```text
SUMMARY: ALL PASS
```

Completed outputs:

- validated alignment TSVs
- aligned reader export
- stable test corpus
- ROOTS-ready data layer

---

# Principles

## 1. Validator First

The validator is authoritative.

No silent failures.

---

## 2. Greek-Driven Alignment

Greek tokens are authoritative.

Spanish reflects Greek structure.

---

## 3. Stable Before Scalable

Correctness before automation.

---

## 4. Book-by-Book Completion

Small validated corpora are more valuable than unstable large-scale automation.

---

## 5. Structured Data First

The alignment layer exists to support future tools.

Not merely TSV production.

