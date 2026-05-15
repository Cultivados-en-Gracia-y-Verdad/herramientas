## VALIDATOR LOGIC

The validator checks one Alignment Verse at a time.

---

## 1. Required Inputs

The validator requires:

- Greek token list
- NBLA token list
- Alignment Records

---

## 2. Greek Coverage Check

For each Greek token:

- its `G_IDX` must appear exactly once in the Alignment Records

Failure if:

- a Greek index is missing
- a Greek index appears more than once
- a Greek index is outside the Greek token list

---

## 3. Greek Token Match Check

For each Alignment Record:

- `GREEK` must match the Greek token at `G_IDX`

Failure if:

- the Greek word in the record differs from the Greek token list

---

## 4. NBLA Coverage Check

For each NBLA token:

- it must appear in `NBLA_IDX`, or
- it must be explicitly accounted for by an approved status

Failure if:

- an NBLA token is unused
- an NBLA index is outside the NBLA token list

---

## 5. NBLA Text Match Check

For each Alignment Record:

- `NBLA_TEXT` must match the NBLA token(s) referenced by `NBLA_IDX`

Failure if:

- the NBLA text differs from the token list
- token order is wrong
- a range does not match the stated text

---

## 6. Duplication Check

An NBLA token may appear only once unless the record is marked as shared.

Failure if:

- the same NBLA token appears in multiple records
- and the later use is not marked shared

---

## 7. Missing Check

If `ALIGNMENT = missing`:

- `NBLA_IDX` must be empty
- `NBLA_TEXT` must be empty

Failure if:

- a missing record consumes NBLA tokens

---

## 8. Alignment Type Check

`ALIGNMENT` must be one of:

- direct
- expanded
- merged-forward
- merged-backward
- missing
- shared

Failure if:

- any other value appears

---

## 9. Final Pass Condition

An Alignment Verse passes only if:

- every Greek token is accounted for
- every NBLA token is accounted for
- all record text matches the source token lists
- no illegal duplication exists
- no invalid alignment type appears

If any check fails:

→ the Alignment Verse fails