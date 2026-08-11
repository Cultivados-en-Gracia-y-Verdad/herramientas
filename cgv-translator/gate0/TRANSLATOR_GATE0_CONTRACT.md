# Translator-Specific Gate 0 Contract

**Version:** 0.3  
**Producer:** `cgv-translator`  
**Consumer:** `cgv-MANAGER`

## Required artifacts

For a book `<book>`:

- `translations/oshb-spine/<book>/<book>-oshb-spine.json`
- `translations/oshb-spine/<book>/<book>-phrases.json`
- `translations/oshb-spine/<book>/<book>-reverse-links.json`
- `translations/<book>.md`

## Required evidence classes

### A. OSHB spine

Must report:

- verse count;
- source token count;
- token-language distribution;
- duplicate source-token IDs;
- missing source-token IDs where sequence rules apply;
- malformed token records;
- verse-order anomalies.

### B. Phrase map

Must report:

- phrase-record count;
- verses with no phrase;
- duplicate phrase records for a verse;
- invalid `sourceTokenIds`;
- empty Spanish phrase text;
- approval-status distribution;
- records with unknown status values.

### C. Reverse links

Must report:

- reverse-link record count;
- verses without reverse-link records;
- invalid source-token references;
- duplicate source-token assignments where disallowed;
- empty Spanish units;
- method distribution;
- status distribution;
- links whose declared verification level is below Gate 0 policy.

### D. Export

Must report:

- exported verse count;
- verses missing from export;
- duplicate exported verses;
- phrase/export divergence;
- obvious malformed export lines;
- checksum.

### E. Approval

Gate 0 policy must explicitly declare whether the book requires:

- 100% `lbf-approved`, or
- an approved subset plus documented exceptions.

Default policy for release-quality compilation is:

```text
all phrase records must be lbf-approved
```

Any `lbf-preliminary` record is a blocker unless the project specification explicitly allows it.

## Translator edit compatibility

`cgv-translator` remains editable during production.

Research, investigation, phrase correction, and alignment correction are normal Translator operations and must not require abandoning or restarting the workflow.

The governing rule is **targeted invalidation**:

```text
RESEARCH / INVESTIGATION ONLY
    → no Gate 0 approval is invalidated

SPANISH PHRASE CHANGED
    → affected G0A approval becomes stale and must be reviewed again
    → affected G0B verification becomes stale when the alignment depends on the changed Spanish

ALIGNMENT ONLY CHANGED
    → unchanged G0A approval remains valid
    → affected G0B verification becomes stale and must be reviewed again
```

A change to one unit must not silently certify the changed unit from an earlier review.

A change to one unit should not require re-review of unrelated units when the review infrastructure can identify the affected unit and its prior artifact identity.

Until review artifacts support fully granular per-unit identity, whole-artifact checksum changes remain a conservative blocker. This is safe but broader than the intended final behavior.

The implementation target is therefore:

- preserve review results for unchanged units;
- reopen only changed translation units for G0A;
- reopen only changed or translation-dependent alignment units for G0B;
- preserve all review history;
- never silently reuse approval for changed content.

## Producer output

Translator produces:

```text
translator-gate0-report.yaml
```

This report is diagnostic evidence only.

## Independent verification

A separate verifier must review:

- suspicious phrase/source mismatches;
- suspicious reverse links;
- span-boundary concerns;
- omission/duplication flags;
- approval-state anomalies.

The independent verifier must not modify Translator artifacts.

## Human linguistic review

Human review must explicitly approve:

- unresolved span-boundary judgments;
- ambiguous source/Spanish relationships;
- any exception to the approval policy.

## Manager acceptance

`cgv-MANAGER` may accept Gate 0 only when:

1. Translator report is internally valid;
2. no producer blocker remains;
3. required phrase-approval policy is satisfied;
4. independent verification = PASS;
5. human linguistic review = PASS;
6. attestation is bound to exact checksums/revisions.
