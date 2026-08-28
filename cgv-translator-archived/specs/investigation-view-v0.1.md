# Investigation View v0.1

## Purpose

The Investigation View exists to make one translation problem manageable.

It should hide file complexity and present a simple workflow:

Text → Observation → Question → Evidence → Research → Policy

## Primary Goal

The translator should never think about files.

The translator should think about the text.

## Screen Layout

### Header

- Investigation ID
- Primary subject
- Origin reference
- Status

Example:

INV-0001 — G1401 δοῦλος  
Origin: Titus 1:1  
Status: Observation

---

### Left Panel — Origin

Displays:

- Project
- Source text
- Book
- Reference
- Clause
- Reason translation paused

---

### Center Panel — Investigation

Tabs:

1. Observations
2. Questions
3. Evidence
4. Research
5. Policy

Each tab edits the matching investigation document.

---

### Right Panel — Output Preview

Displays the projected dictionary output:

cgv-dictionary/greek/G1401/lemma.json

This preview is not editable directly.

---

### Bottom Panel — History

Automatically logs:

- created investigation
- added observation
- added question
- generated evidence
- changed policy
- exported lemma.json

## Rule

The app manages structure.

The translator manages judgment.