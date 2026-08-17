# cgv-translator Data Contract

Status: normative  
Canonical architecture: `Biblia-LBF/docs/architecture/CGV_DATA_ARCHITECTURE.md`

## Purpose

`cgv-translator` is the human editing and approval application for the LBF project. It provides workflows over `Biblia-LBF`; it does not own an independent translation or alignment corpus.

## Owned data

- Translator UI and application code.
- A repository adapter for reading and proposing changes to `Biblia-LBF`.
- Authentication, authorization, and collaboration workflow code.
- Local caches, drafts, and optimistic UI state.
- Tests and clearly labeled noncanonical fixtures.

## Source and write contract

- Canonical input is a named `Biblia-LBF` branch and commit.
- The application reads and writes the canonical schemas without inventing an alternate format.
- Accepted edits are committed or proposed by pull request to `Biblia-LBF`.
- Translation, tokenization, alignment, notes, and review state use stable canonical IDs.
- Concurrent edits must detect revision conflicts; last-write-wins is prohibited.
- A save that changes translation text must invalidate affected approvals.
- A save that changes alignment must invalidate alignment approval.
- Human approval records the authenticated approver and exact content revisions.
- Machine suggestions remain distinguishable from human decisions.

## Cache and database rules

A cache or collaboration database is allowed only when:

- `Biblia-LBF` remains authoritative;
- every record includes its base repository commit and canonical revision;
- accepted changes are durably written back to Git;
- conflicts block publication rather than silently selecting a winner;
- cached content can be rebuilt or discarded without losing approved work.

The application must show whether work is local draft, proposed, merged, approved, or published.

## Publication boundary

`cgv-translator` must never publish directly to `cgv-data`. Publication begins only after changes and approvals are merged into `Biblia-LBF`, then passes through its validation and export gate.

## Prohibited content and behavior

- A private canonical translation database.
- Hand-maintained copies of the full LBF corpus.
- Direct edits to `cgv-data`.
- Approval based on display text without exact revision binding.
- Silent regeneration of token IDs.
- Silent conflict resolution.
- Automatic promotion of machine output to approved.

## Pull-request gate

CI must test repository-adapter round trips, revision conflicts, approval invalidation, stable IDs, schema compatibility, and the absence of direct `cgv-data` writes.

