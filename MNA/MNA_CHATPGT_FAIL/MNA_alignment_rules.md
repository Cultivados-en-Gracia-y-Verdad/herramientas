# MNA Alignment Rules

## 1. PURPOSE

MNA Alignment maps NBLA to SBLGNT at the token level.

No interpretation is permitted.

---

## 2. COVERAGE (NON-NEGOTIABLE)

### Greek Coverage
Every Greek token must be:
- aligned to NBLA, or
- marked as missing

No Greek token may remain unclassified.

---

### NBLA Coverage
Every NBLA token must be:
- mapped to one or more Greek tokens, or
- explicitly accounted for

No NBLA token may remain unused.

---

### Duplication
An NBLA token may not be used more than once
unless explicitly shared.

---

### Validation
If any Greek or NBLA token is unaccounted for:
→ alignment fails

---

## 3. TOKEN RULES

- One Greek token = one Alignment Record
- NBLA tokens are fixed after tokenization
- NBLA tokens may not be modified during alignment

---

## 4. ALIGNMENT TYPES

- direct
- expanded
- merged-forward
- merged-backward
- missing

---

## 5. CLAUSE ANCHOR RULE

A Greek clause introducer
maps to the first NBLA token
that begins its clause.

---

## 6. MINIMAL SPAN RULE

Use the smallest NBLA span
that satisfies the Greek token.

---

## 7. NO INTERPRETATION

Do not use meaning to decide alignment.

Only observable structure is allowed.

## CONTRAST ANCHOR RULE

A Greek contrast marker (e.g., δὲ)
maps to the NBLA token that introduces
the contrasting segment.