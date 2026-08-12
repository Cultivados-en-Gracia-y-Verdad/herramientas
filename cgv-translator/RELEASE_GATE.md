# cgv-translator Release Gate

**Status:** Active
**Authority:** Implements the publication boundary defined by `WORKFLOW.md`.

## Hard rule

`cgv-data` is release-only.

No book may be added to `cgv-data` while it is incomplete, partially verified, provisionally approved, or still carrying unresolved workflow questions.

A passing regression, historical artifact match, successful export, or successful individual gate is evidence about part of the workflow. None of those by itself authorizes publication.

## Release identity

Every released book must belong to an explicitly declared LBF edition and an immutable book release version.

Before publication, the release record must identify:

- LBF edition;
- book release version;
- biblical source identity and source revision;
- LBF translation revision;
- alignment revision;
- workflow version used for approval;
- exact final artifact SHA-256;
- final approval state and authority.

The terms have distinct purposes:

- **Edition** identifies the canonical LBF edition to which the book belongs.
- **Book release version** identifies the immutable release of that book within the edition.
- **Translation revision** identifies the approved Spanish state.
- **Alignment revision** identifies the approved source-alignment state.
- **Artifact SHA-256** identifies the exact released bytes.

No edition or version may be inferred from a filename, branch name, date, old export, or historical checksum. It must be explicitly assigned and recorded.

If the approved Spanish, alignment, or final release bytes change after release, the prior released artifact remains immutable. The correction must receive a new release identity as required by the edition/version policy; it must never silently replace the prior artifact under the same identity.

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
- LBF edition is explicitly declared;
- book release version is explicitly declared;
- translation revision is explicitly declared;
- alignment revision is explicitly declared;
- final human approval is recorded for those exact revisions and release identity;
- the final release artifact is built from the approved Translator state;
- the final release artifact passes its release validation/regression checks;
- the final artifact SHA-256 is recorded in the release identity;
- publication to `cgv-data` preserves the exact approved edition/version/artifact identity;
- the published `cgv-data` artifact is verified after publication.

If any item is unknown, missing, failed, or only inferred from legacy evidence, the book is **NOT RELEASE READY**.

## Daniel

Daniel is a regression/reference corpus while its historical workflow evidence is being reconciled.

The existence of externally approved G0A evidence, externally VERIFIED G0B results, a frozen reverse-link artifact, or a matching historical release hash does not by itself establish that Daniel completed every current book-level release requirement.

Daniel also requires an explicitly declared LBF edition and book release version. Historical files or hashes must not be used to invent that identity.

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
DECLARE EDITION + VERSION + REVISIONS
        ↓
HUMAN APPROVAL OF THAT EXACT RELEASE IDENTITY
        ↓
BUILD FINAL ARTIFACT
        ↓
VALIDATE EXACT ARTIFACT + SHA-256
        ↓
PUBLISH TO cgv-data
        ↓
VERIFY PUBLISHED ARTIFACT
        ↓
REGISTER WITH cgv-MANAGER
```

There is no shortcut from G0A, G0B, regression success, export success, or a historical hash directly to `cgv-data`.