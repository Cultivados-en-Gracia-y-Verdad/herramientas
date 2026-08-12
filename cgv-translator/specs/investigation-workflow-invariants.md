# Investigation Workflow Invariants

This document defines the permanent rules for CGV Translator investigations. Historical investigation folders are fixtures and migration inputs; they do not define the workflow contract.

## 1. Canonical ownership

Every investigation belongs to exactly one biblical book at creation time.

- Canonical path: `investigations/<book-id>/INV-<book-number>-<sequence>/`
- Canonical id example: `INV-27-0001` for Daniel.
- A new investigation must never be created first in a repository-level `INV-0001` folder and migrated later.
- The same lemma may have separate investigations in separate books.

## 2. Investigation is not decision

Creating an investigation records that study is required. It does not establish translation policy.

Every new investigation starts with:

- `Status: Draft`
- no approval authority
- no approver
- no approval timestamp
- no implied preferred rendering

Evidence gathering, AI assistance, saving, migration, or translation editing must never create human approval.

## 3. Scope is part of the decision

Every decision has one explicit scope:

1. `Occurrence`
2. `Construction`
3. `Book Default`

A new investigation defaults to `Occurrence` with `Scope Reference` equal to its originating reference. This default describes where the unresolved question came from; it does not approve anything.

Required scope data:

- `Occurrence` requires `Scope Reference`.
- `Construction` requires a machine-verifiable `Scope Condition`.
- `Book Default` requires neither a reference nor a construction condition.

## 4. Specificity precedence

When more than one approved decision could apply to a token, the most specific applicable decision wins:

`Occurrence > Construction > Book Default`

An occurrence decision applies only at its exact reference. A construction decision applies only when every supported condition clause matches. A book default applies only inside its owning book.

Unknown construction-condition syntax must fail closed: it is documented for humans but is never automatically applied.

## 5. Book Default is guidance, not string replacement

A `Book Default` establishes lexical guidance for the owning book. It does not force an exact Spanish string when morphology or syntax requires inflection, number, agreement, possession, articles, or another grammatical realization.

Occurrence and machine-verifiable construction decisions may constrain a more specific rendering.

## 6. Human approval boundary

A decision is usable as approved policy only when all of the following are true:

- status is `Approved`;
- `Approval Authority` is `human`;
- `Approved By` is non-empty;
- `Approved At` is non-empty;
- decision scope is valid;
- the decision has a preferred rendering where policy requires one.

Approval is a separate explicit human action. Editing a previously approved decision creates a new revision and clears approval provenance until that revision is explicitly approved.

## 7. Evidence is independent

Evidence can be gathered, regenerated, expanded, or replaced without changing decision status. Evidence volume or age does not grant policy authority.

The biblical text remains final authority; evidence files are traceable working material.

## 8. End-to-end book context

Book identity must travel through every workflow boundary:

`UI -> API -> investigation lookup -> gate analysis -> policy selection`

A request without a valid book id must not silently fall back to another book for investigation policy.

## 9. Atomic creation

A successful creation operation produces, in one canonical book directory:

- canonical investigation id;
- origin metadata;
- Draft decision;
- originating occurrence scope;
- empty approval provenance;
- evidence/research/policy scaffolding.

Partial or ambiguous creation is an error, not a state the application should normalize later.

## 10. Fail loudly on structural violations

Regression checks should reject:

- malformed canonical ids;
- mismatched book number and owning book;
- missing book context;
- invalid decision scope;
- occurrence scope without a reference;
- construction scope without a supported condition;
- inferred/non-human approval;
- policy application outside its scope;
- precedence violations.

Legacy/unscoped records may be handled by migration code, but new application code must not create them.

## 11. Migrations are temporary; invariants are permanent

Migration scripts may repair historical repository state. They are not the source of truth for runtime semantics.

Permanent behavior belongs in reusable application modules and regression tests. A migration is complete only when normal application paths create valid records without needing the migration again.
