# cgv-translator Release Gate

**Status:** Active
**Authority:** Implements the publication boundary defined by `WORKFLOW.md`.

## Hard rule

`cgv-data` is release-only.

No book may be added to `cgv-data` while it is incomplete, partially verified, provisionally approved, or still carrying unresolved workflow questions.

A passing regression, historical artifact match, successful export, or successful individual gate is evidence about part of the workflow. None of those by itself authorizes publication.

## Required before publication

A book may be published to `cgv-data` only when all of the following are true for the exact artifact being released:

- every required verse is complete;
- all required G0A translation verification has passed;
- all required alignment is complete;
- all required G0B alignment verification has passed;
- verification evidence is attributable to the exact reviewed artifact;
- required difficult-word investigations are resolved and documented;
- book-level final review has passed;
- no unresolved blocker, escalation, or known workflow defect remains;
- final human approval is recorded;
- the final release artifact is built from the approved Translator state;
- the final release artifact passes its release validation/regression checks;
- publication to `cgv-data` preserves the exact approved artifact identity;
- the published `cgv-data` artifact is verified after publication.

If any item is unknown, missing, failed, or only inferred from legacy evidence, the book is **NOT RELEASE READY**.

## Daniel

Daniel is a regression/reference corpus while its historical workflow evidence is being reconciled.

The existence of externally approved G0A evidence, externally VERIFIED G0B results, a frozen reverse-link artifact, or a matching historical release hash does not by itself establish that Daniel completed every current book-level release requirement.

Until the complete book release gate above is demonstrated, Daniel must remain out of `cgv-data` as a new canonical release.

## Publication sequence

```text
VERSE WORK COMPLETE
        ↓
G0A COMPLETE
        ↓
ALIGNMENT COMPLETE
        ↓
G0B COMPLETE
        ↓
INVESTIGATIONS RESOLVED
        ↓
BOOK-LEVEL FINAL CHECK PASS
        ↓
NO BLOCKERS
        ↓
HUMAN APPROVAL
        ↓
BUILD FINAL ARTIFACT
        ↓
VALIDATE EXACT ARTIFACT
        ↓
PUBLISH TO cgv-data
        ↓
VERIFY PUBLISHED ARTIFACT
        ↓
REGISTER WITH cgv-MANAGER
```

There is no shortcut from G0A, G0B, regression success, or export success directly to `cgv-data`.