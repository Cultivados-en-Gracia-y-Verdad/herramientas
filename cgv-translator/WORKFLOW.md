# cgv-translator Workflow Standard

<<<<<<< Updated upstream
**Status:** Active  
**Scope:** LBF translation, alignment, verification, approval, and release  
**Version:** 0.3

---

# 1. Authority

This document defines the canonical production workflow for `cgv-translator`.

Implementation specifications may add technical detail but may not contradict this workflow.

---

# 2. Purpose

`cgv-translator` governs the production of **La Biblia Fiel (LBF)** and its alignment to the biblical source text.
=======
**Status:** Draft  
**Scope:** LBF translation, alignment, verification, approval, and release  
**Version:** 0.2

---

# 1. Purpose

cgv-translator governs the production of the **La Biblia Fiel (LBF)** translation and its alignment to the biblical source text.
>>>>>>> Stashed changes

The objective is to produce an LBF text that is:

- faithful to the source;
- reviewed;
- correctly aligned;
- documented where difficult translation decisions required investigation;
- approved;
- ready to become canonical CGV data.

The process must remain simple enough to be followed consistently.

---

<<<<<<< Updated upstream
# 3. System Responsibilities

## cgv-translator

`cgv-translator` is the working environment for:
=======
# 2. System Responsibilities

## cgv-translator

cgv-translator is the working environment for:
>>>>>>> Stashed changes

- translation;
- difficult-word investigations;
- translation decisions;
- translation verification;
- alignment;
- alignment verification;
- revision;
- approval preparation.

## cgv-data

`cgv-data` is the canonical repository for final approved CGV data.

Approved LBF Bible and alignment data ultimately reside there.

## cgv-MANAGER

<<<<<<< Updated upstream
`cgv-MANAGER` records the approved artifact and determines what downstream workflow may begin.

---

# 4. Core Translation Workflow
=======
cgv-MANAGER records the approved artifact and determines what downstream workflow may begin.

---

# 3. Core Translation Workflow
>>>>>>> Stashed changes

The canonical Translator sequence is:

```text
SOURCE
   ↓
TRANSLATE
   ↓
G0A — VERIFY TRANSLATION
   ↓
ALIGN
   ↓
G0B — VERIFY ALIGNMENT
   ↓
BOOK-LEVEL FINAL CHECK
   ↓
APPROVE
   ↓
PUBLISH TO cgv-data
   ↓
REGISTER WITH cgv-MANAGER
```

This is the governing sequence.

---

<<<<<<< Updated upstream
# 5. Translator Compatibility Principle

The LBF translation process may be carried out using AI, human work, `cgv-translator`, or a combination of these methods.

The workflow must remain compatible with `cgv-translator` throughout production.

At any time, the translator may use `cgv-translator` to:

- inspect the source;
- conduct research;
- open or continue an investigation;
- revise a Spanish phrase;
- modify an alignment;
- correct other Translator-owned data.

Using `cgv-translator` does not bypass the workflow and does not require restarting unaffected work.

A change returns only the affected artifact to the appropriate verification step.

```text
RESEARCH ONLY
    → no verification state is invalidated

SPANISH TRANSLATION CHANGED
    → affected G0A approval must be verified again
    → affected alignment must be reviewed or rebuilt if the change affects it
    → affected G0B verification must be verified again when alignment is affected

ALIGNMENT ONLY CHANGED
    → unchanged G0A approval remains valid
    → affected G0B verification must be verified again
```

The workflow tracks the state of the work; it must not prevent the translator from returning to the text when correction or further research is required.

`cgv-translator` remains an editable working environment until release. Approval controls the validity of the current artifact; it does not make the text inaccessible.

---

# 6. Working Unit

Translation normally proceeds **verse by verse**.

Within `cgv-translator`, the underlying data may divide the verse into phrases or other alignment units.
=======
# 4. Working Unit

Translation normally proceeds **verse by verse**.

Within cgv-translator, the underlying data may divide the verse into phrases or other alignment units.
>>>>>>> Stashed changes

That implementation detail does not change the human workflow:

```text
VERSE
  ↓
TRANSLATE
  ↓
VERIFY
  ↓
ALIGN
  ↓
VERIFY ALIGNMENT
  ↓
NEXT VERSE
```

---

<<<<<<< Updated upstream
# 7. Phase 1 — Translate
=======
# 5. Phase 1 — Translate
>>>>>>> Stashed changes

Begin from the declared biblical source text.

Produce the LBF Spanish translation of the verse.

AI may assist substantially in producing the translation.

AI output is proposed translation work and remains subject to review.

The translator must consider the source text and necessary context.

The translation should not begin from another Spanish Bible as its authority.

---

<<<<<<< Updated upstream
# 8. Difficult Translation Decisions
=======
# 6. Difficult Translation Decisions
>>>>>>> Stashed changes

Not every translated word requires documentation.

Investigations are reserved for difficult words, expressions, or translation questions where a responsible decision requires closer examination.

When such a question occurs:

```text
DIFFICULT WORD / QUESTION
        ↓
OPEN INVESTIGATION
        ↓
EXAMINE OCCURRENCES
        ↓
OBSERVE HOW IT IS USED
        ↓
EXAMINE HOW IT HAS BEEN TRANSLATED
        ↓
ARRIVE AT DECISION
        ↓
RECORD PREFERRED RENDERING
        ↓
EXPLAIN WHY
        ↓
RETURN TO TRANSLATION
```

The purpose is straightforward:

**Document what we decided and how we arrived at that decision.**

The investigation record exists so important decisions for this edition do not survive only in:

- human memory;
- AI conversations;
- temporary notes.

A future edition may reconsider the decision.

<<<<<<< Updated upstream
Research or investigation by itself does not invalidate approved translation or alignment work. If the resulting decision changes the Spanish or alignment, the affected verification state is then returned to G0A or G0B as appropriate.

---

# 9. G0A — Translation Verification
=======
---

# 7. G0A — Translation Verification
>>>>>>> Stashed changes

After translation, the Spanish must be verified.

G0A concerns the **translation itself**.

It does not verify alignment.

The question is:

> Does this Spanish faithfully represent the source?

The positive G0A decision is:

```text
APPROVED
```

Possible negative or unresolved states include:

```text
NEEDS_REVISION
REJECTED
ESCALATE
```

## G0A Review

Verify matters such as:

- Does the Spanish account for the source?
- Was anything omitted?
- Was anything added without support?
- Was a grammatical relationship distorted?
- Was ambiguity resolved that should remain open?
- Is the Spanish sufficiently faithful for later CGV analysis?

Natural-sounding Spanish alone is not enough.

## If G0A fails

```text
G0A
 ↓
NEEDS REVISION
 ↓
RETURN TO TRANSLATION
 ↓
REVISE
 ↓
G0A AGAIN
```

Translation does not proceed to final alignment verification until G0A passes.

---

<<<<<<< Updated upstream
# 10. Phase 2 — Alignment
=======
# 8. Phase 2 — Alignment
>>>>>>> Stashed changes

Once the translation has passed G0A, align the approved Spanish to the original-language source.

Alignment records which Spanish unit corresponds to which source unit or units.

Alignment must represent the real translation relationship.

It must not create false relationships merely to make the alignment appear complete.

Legitimate relationships may include:

```text
one source unit → one Spanish unit

one source unit → multiple Spanish units

multiple source units → one Spanish unit

multiple source units → multiple Spanish units
```

---

<<<<<<< Updated upstream
# 11. G0B — Alignment Verification
=======
# 9. G0B — Alignment Verification
>>>>>>> Stashed changes

After alignment, verify the alignment.

G0B concerns the **relationship between the Spanish and source units**.

It does not primarily judge Spanish style.

The positive G0B decision is:

```text
VERIFIED
```

Possible negative or unresolved states include:

```text
NEEDS_RELINK
REJECTED
ESCALATE
```

## G0B Review

Verify matters such as:

- Does this Spanish unit actually correspond to these source tokens?
- Are relevant source tokens missing?
- Are unrelated source tokens included?
- Does the link cross a grammatical boundary incorrectly?
- Has a mechanically plausible alignment created a false relationship?
- Does the alignment preserve what CGV Reader will later need to observe?

Generation method is not verification.

An AI-generated or mechanically generated link still requires verification.

---

<<<<<<< Updated upstream
# 12. If G0B Finds an Alignment Problem
=======
# 10. If G0B Finds an Alignment Problem
>>>>>>> Stashed changes

If the translation is correct but the alignment is wrong:

```text
G0B
 ↓
NEEDS RELINK
 ↓
FIX ALIGNMENT
 ↓
G0B AGAIN
```

---

<<<<<<< Updated upstream
# 13. If G0B Reveals a Translation Problem
=======
# 11. If G0B Reveals a Translation Problem
>>>>>>> Stashed changes

Alignment may reveal that the Spanish itself needs correction.

In that case:

```text
G0B
 ↓
TRANSLATION PROBLEM DISCOVERED
 ↓
RETURN TO TRANSLATION
 ↓
REVISE SPANISH
 ↓
G0A AGAIN
 ↓
REALIGN AS NEEDED
 ↓
G0B AGAIN
```

A downstream alignment correction must not hide a translation defect.

---

<<<<<<< Updated upstream
# 14. Gate 0 Completion
=======
# 12. Gate 0 Completion
>>>>>>> Stashed changes

Gate 0 is complete only when:

```text
G0A = PASS
AND
G0B = PASS
```

No unresolved blocker may remain.

---

<<<<<<< Updated upstream
# 15. Review Independence
=======
# 13. Review Independence
>>>>>>> Stashed changes

Translation production and verification are different actions.

The producer should not simply declare its own output correct.

AI may produce translation or alignment.

AI may also assist review.

But production is not itself verification.

---

<<<<<<< Updated upstream
# 16. Chapter Progress
=======
# 14. Chapter Progress
>>>>>>> Stashed changes

As work progresses through a chapter:

1. translate the verse;
2. resolve difficult investigations where needed;
3. pass G0A;
4. align;
5. pass G0B;
6. continue to the next verse.

Chapter completion should not depend merely on every verse having Spanish text.

The required translation and alignment verification must also be complete.

---

<<<<<<< Updated upstream
# 17. Book-Level Final Check
=======
# 15. Book-Level Final Check
>>>>>>> Stashed changes

After the entire book has passed verse-level work, review the book as a whole.

This review exists to catch issues that may not be obvious while moving verse by verse.

Review should consider:

- consistency of repeated terminology;
- names and titles;
- recurring expressions;
- repeated grammatical constructions;
- difficult-word decisions made during the book;
- translation choices made early in the book in light of later discoveries;
- alignment consistency;
- unresolved investigations;
- unresolved G0A findings;
- unresolved G0B findings.

The purpose is **intentional consistency**, not forced identical translation in every context.

---

<<<<<<< Updated upstream
# 18. Final Translation Status
=======
# 16. Final Translation Status
>>>>>>> Stashed changes

A book is ready for approval only when:

- translation is complete;
- G0A verification is complete;
- alignment is complete;
- G0B verification is complete;
- difficult translation decisions requiring investigation are documented;
- book-level final review is complete;
- no blocking issue remains.

Then the project may become:

```text
TRANSLATION_APPROVED
```

---

<<<<<<< Updated upstream
# 19. Approved Output
=======
# 17. Approved Output
>>>>>>> Stashed changes

The approved Translator output consists of the reviewed LBF data needed downstream, including:

- LBF Spanish text;
- source alignment;
- appropriate source identifiers;
- translation revision;
- alignment revision;
- approval state;
- required provenance;
- documented significant translation decisions.

The exact storage/export schema may be defined separately.

---

<<<<<<< Updated upstream
# 20. Publication to cgv-data
=======
# 18. Publication to cgv-data
>>>>>>> Stashed changes

After approval:

```text
TRANSLATION_APPROVED
        ↓
BUILD FINAL DATA
        ↓
PUBLISH TO cgv-data
        ↓
VERIFY PUBLISHED DATA
        ↓
REGISTER WITH cgv-MANAGER
```

`cgv-data` becomes the canonical home of the released LBF data.

The working Translator project remains the record of how the translation was developed.

---

<<<<<<< Updated upstream
# 21. Manager Handoff

`cgv-MANAGER` must receive or identify the exact approved `cgv-data` artifact.
=======
# 19. Manager Handoff

cgv-MANAGER must receive or identify the exact approved `cgv-data` artifact.
>>>>>>> Stashed changes

Manager then determines whether the book is eligible for the next workflow stage.

For the larger CGV process:

```text
cgv-translator
      ↓
G0A PASS
      ↓
G0B PASS
      ↓
APPROVED
      ↓
cgv-data
      ↓
cgv-MANAGER
      ↓
cgv-reader
```

Reader must not begin from an unofficial or unverified translation artifact.

---

<<<<<<< Updated upstream
# 22. Post-Approval Corrections
=======
# 20. Post-Approval Corrections
>>>>>>> Stashed changes

An approved translation may later require correction.

If so:

```text
CORRECTION REQUIRED
        ↓
RETURN TO cgv-translator
        ↓
REVISE TRANSLATION / ALIGNMENT
        ↓
G0A AS REQUIRED
        ↓
G0B AS REQUIRED
        ↓
BOOK CHECK AS REQUIRED
        ↓
NEW APPROVAL
        ↓
NEW cgv-data REVISION
        ↓
REGISTER WITH cgv-MANAGER
```

The previous approved artifact must not be silently changed while retaining the same identity.

---

<<<<<<< Updated upstream
# 23. Definition of Done — Verse
=======
# 21. Definition of Done — Verse
>>>>>>> Stashed changes

A verse is complete when:

- [ ] translation is complete;
- [ ] required difficult-word investigations are resolved or properly flagged;
- [ ] G0A translation verification passed;
- [ ] alignment is complete;
- [ ] G0B alignment verification passed;
- [ ] no blocking issue remains.

---

<<<<<<< Updated upstream
# 24. Definition of Done — Book

A book is complete in `cgv-translator` when:
=======
# 22. Definition of Done — Book

A book is complete in cgv-translator when:
>>>>>>> Stashed changes

- [ ] every required verse is complete;
- [ ] all G0A review is complete;
- [ ] all G0B review is complete;
- [ ] required investigations are documented;
- [ ] book-level final review is complete;
- [ ] no blocker remains;
- [ ] human approval is recorded;
<<<<<<< Updated upstream
- [ ] final data package is ready for `cgv-data`.

---

# 25. Non-Negotiable Rules
=======
- [ ] final data package is ready for cgv-data.

---

# 23. Non-Negotiable Rules
>>>>>>> Stashed changes

1. Translate from the declared source.
2. AI may assist, but AI output must be verified.
3. Difficult decisions should be documented; routine words do not require investigations.
<<<<<<< Updated upstream
4. Research alone does not invalidate verified work.
5. G0A verifies the translation.
6. A translation change returns the affected work to G0A.
7. Alignment follows the translation.
8. G0B verifies the alignment.
9. An alignment-only change returns the affected work to G0B without invalidating unchanged G0A work.
10. A G0B finding may send the work back to translation.
11. Do not hide translation problems through alignment changes.
12. Do not hide alignment problems through Spanish rewriting.
13. Do not restart unaffected work when one unit changes.
14. Do not declare work complete merely because text exists.
15. Approved final data belongs in `cgv-data`.
16. Downstream CGV work must use the approved canonical artifact.

---

# 26. Canonical Summary
=======
4. G0A verifies the translation.
5. Translation must pass G0A before final acceptance.
6. Alignment follows the translation.
7. G0B verifies the alignment.
8. A G0B finding may send the work back to translation.
9. Do not hide translation problems through alignment changes.
10. Do not hide alignment problems through Spanish rewriting.
11. Do not declare work complete merely because text exists.
12. Approved final data belongs in cgv-data.
13. Downstream CGV work must use the approved canonical artifact.

---

# 24. Canonical Summary
>>>>>>> Stashed changes

```text
TRANSLATE
   ↓
   ├── difficult word?
   │       ↓
   │   INVESTIGATE
   │   OCCURRENCES
   │   DECIDE
   │   EXPLAIN WHY
   │       ↓
   └──── RETURN
   ↓
G0A — VERIFY TRANSLATION
   ↓
ALIGN
   ↓
G0B — VERIFY ALIGNMENT
   ↓
BOOK FINAL CHECK
   ↓
APPROVE
   ↓
cgv-data
   ↓
cgv-MANAGER
   ↓
cgv-reader
```

<<<<<<< Updated upstream
At any point before release, the translator may return to `cgv-translator` for research or correction. Only the affected verification state is reopened.

That is the `cgv-translator` production workflow.
=======
That is the cgv-translator production workflow.

> **Translator Compatibility Principle**
>
> The LBF translation process may be carried out using AI, human work, cgv-translator, or a combination of these methods.
>
> The workflow must remain compatible with cgv-translator throughout production.
>
> At any time, the translator may use cgv-translator to inspect the source, conduct an investigation, revise a Spanish phrase, modify an alignment, or correct other Translator-owned data.
>
> Such work does not bypass or restart the workflow. It returns the affected artifact to the appropriate verification step.
>
> Research alone does not invalidate approved work.
>
> A translation change invalidates the affected G0A approval and any G0B alignment that depends on that translation.
>
> An alignment-only change invalidates the affected G0B verification but does not by itself invalidate an unchanged G0A-approved translation.
>
> The workflow tracks the state of the work; it does not prevent the translator from returning to the text when correction or further research is required

> **cgv-translator must remain an editable working environment until release. Approval controls changes; it does not make the text inaccessible.**
>>>>>>> Stashed changes
