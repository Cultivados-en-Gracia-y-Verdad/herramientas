# LBF Book Approval Workflow

**Status:** Active  
**Version:** 1.0

This is the one approval process for an LBF book. There are two gates and no inferred approvals:

## Non-negotiable authority boundary

AI must not verify a translation, verify an alignment, issue a PASS decision, or give final approval.

Scripts establish only mechanically provable facts: artifact identity, source-token accounting, completeness, exact text spans, overlap, coverage, and staleness. They do not make semantic judgments.

Faithfulness review and final approval belong to an identified human who directly examined the evidence. An AI-generated review presented under a human name is invalid.

```text
SOURCE + SPANISH
       ↓
DETERMINISTIC COMPLETENESS CHECK
       ↓
TRANSLATION REVIEW ───────────────→ TRANSLATION PASS
                                          ↓
SOURCE + SPANISH + ALIGNMENT               ↓
       ↓                                   ↓
DETERMINISTIC ALIGNMENT CHECK              ↓
       ↓                                   ↓
HUMAN ALIGNMENT REVIEW ───────────→ ALIGNMENT PASS
                                          ↓
                                  BOOK MAY BE APPROVED
```

## The hard rule

A book is eligible for approval only when:

```text
TRANSLATION = PASS
AND
ALIGNMENT = PASS
```

`PENDING`, `FAIL`, `STALE`, or `BLOCKED` is not PASS. A generated label, prior report, historical checksum, producer claim, successful export, or AI opinion is not PASS.

## Canonical working artifacts

Each review is bound by SHA-256 to exactly three working artifacts:

1. the declared source spine;
2. the Spanish phrase artifact;
3. the reverse-alignment artifact.

The translation gate is bound to the source and Spanish. The alignment gate is bound to all three.

If any bound bytes change, the old review becomes `STALE`. Running `prepare` preserves decisions only for verses whose review evidence is unchanged; changed verses return to `PENDING`.

## Step 1 — Prepare

Run:

```text
npm run verify:book -- prepare BOOK
```

The verifier uses only deterministic checks. It cannot approve the work.

It checks translation completeness, including:

- every source verse has Spanish;
- Spanish is not blank;
- phrase identities are unique;
- every source token used by a phrase exists in the correct source verse;
- no source token is omitted from the translation segmentation.

It checks alignment completeness, including:

- every phrase has one alignment record;
- every alignment span matches the exact current Spanish;
- spans do not overlap;
- no lexical Spanish text is left unaligned;
- aligned source tokens exist and belong to the phrase;
- no source token assigned to a phrase is left unaligned.

The command writes one small set of active files under `verification/BOOK/`:

- `review-packet.html` — large, readable human evidence;
- `review-packet.json` — machine-readable evidence;
- `defects.json` — all deterministic blockers;
- `translation-review.json` — translation decisions;
- `alignment-review.json` — alignment decisions.

A review file is created only when that gate has no deterministic defects.

## Step 2 — Human translation review

The reviewer examines each verse in the packet against the declared source and records `PASS` or `FAIL`:

```text
npm run verify:book -- record BOOK translation "Book 1:1" PASS --reviewer "Name" --human-confirmation
```

Translation review asks:

- Is every source meaning represented?
- Was anything added without support?
- Was any grammatical relationship distorted?
- Was an ambiguity improperly removed?
- Is the Spanish faithful enough for downstream CGV analysis?

Natural Spanish alone is insufficient. The decision must be direct human review and attributable. `--human-confirmation` records that the named human examined the evidence and that AI was not used as the verifier. Preparation never fills a PASS decision.

If a verse fails, revise the Spanish, prepare again, and review the changed verse again.

## Step 3 — Human alignment review

Alignment review for a verse may begin only after that verse has a human translation PASS:

```text
npm run verify:book -- record BOOK alignment "Book 1:1" PASS --reviewer "Name" --human-confirmation
```

Alignment review asks:

- Does each Spanish unit point to the source unit it actually represents?
- Are any relevant source units missing?
- Are unrelated source units included?
- Do the links preserve meaningful grammatical relationships?
- Would the links allow CGV Reader to show the real translation relationship?

Mechanical completeness is necessary but not sufficient. The alignment method or producer status never counts as verification.

If the links fail, repair the alignment, prepare again, and review the changed verse again. If alignment review discovers a translation defect, revise the Spanish and return that verse to translation review first.

## Step 4 — Status

Run:

```text
npm run verify:book -- status BOOK
```

This is the only active status summary. It reports the two gates directly:

```text
TRANSLATION   PASS | FAIL | PENDING | STALE
ALIGNMENT     PASS | FAIL | PENDING | STALE | BLOCKED
BOOK          PASS | NOT APPROVED
```

Use this to list remaining review work:

```text
npm run verify:book -- pending BOOK translation
npm run verify:book -- pending BOOK alignment
```

## Investigations

Open an investigation only for a genuinely difficult translation decision. Record the evidence, conclusion, preferred rendering, reason, scope, and human authority.

Research alone does not invalidate a review. If an investigation changes Spanish, the affected translation and alignment evidence becomes stale. If it changes only links, only the affected alignment evidence becomes stale.

## Final approval and publication

After both gates show PASS, perform the book-level consistency check and record human approval for an explicit edition, book version, source revision, translation revision, and alignment revision.

Build the release artifact from those exact approved bytes, record its SHA-256, publish it to `cgv-data`, verify the published bytes, and register that exact release with `cgv-MANAGER`.

No approval or publication command in this repository may bypass the two PASS results.

## Failed legacy process

The previous Gate 0 queues, packets, evidence chains, repair reports, promotion reports, backups, and in-progress generated edits were removed from the active path on 2026-08-14. They remain recoverable under `CLAUDE-FAIL/2026-08-14-failed-approval-system/` and have no approval authority.
