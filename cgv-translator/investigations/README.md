# cgv-translator Investigations

Investigations are owned by the biblical book that triggered them.

## Canonical structure

```text
investigations/
  <book-id>/
    INV-####/
      README.md
      observations.md
      decision.md
      questions.md
      evidence.md
      research.md
      policy.md
      history.md
      evidence/
        README.md
```

Examples:

```text
investigations/titus/INV-0001/
investigations/daniel/INV-0007/
```

## Ownership rule

Each investigation belongs to exactly one book.

The investigation may examine occurrences and evidence from anywhere in Scripture, but its workflow status and release relevance belong only to its originating book.

A Daniel release check must inspect Daniel investigations only. A Titus investigation must never block Daniel merely because both investigations exist in the same Translator repository.

## Reuse across books

A verified lesson from one book may inform later translation work in another book, but that does not transfer ownership of the original investigation.

If a later book raises a genuinely unresolved translation question, open a book-owned investigation for that book and cite the prior verified evidence or decision where useful.

Do not treat an old investigation as automatically deciding a new book context without review.

## What is not an investigation

Do not open a book investigation — and never mark one release-blocking — in order to make a translator choose ketiv vs qere or otherwise re-select tokens already fixed in the source snapshot. That choice belongs to the snapshot. Translate the spine.

Occurrence dumps must stay in the language of the book. Greek lemma profiles do not belong in a Hebrew investigation.

## Release rule

Before a book can pass its final release gate:

- every required investigation owned by that book must be resolved and documented, or explicitly classified as a non-blocking deferred question;
- source-tokenization inventories (unused qere lists, bootstrap notes) are not required investigations;
- any investigation whose decision changes Spanish must have the affected translation verification repeated;
- any investigation whose decision changes alignment must have the affected alignment verification repeated;
- unresolved blocking investigations keep the book out of `cgv-data`.

## Existing legacy layout

The current repository still contains legacy top-level investigation folders. Their declared ownership is:

- `INV-0001` through `INV-0006`: Titus
- `INV-0007` through `INV-0008`: Daniel

These folders must be migrated only after the Translator investigation API/UI is book-aware, so existing investigation history is not made inaccessible by a filesystem-only move.

The legacy file `daniel-hebrew-translation-decisions.md` is Daniel-specific historical material. It is not a substitute for resolved structured investigations and should remain associated with Daniel when the migration is performed.
