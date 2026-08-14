# CGV Gate 0 Subgates

**Version:** 0.1  
**Scope:** Translator verification before Compiler Generate  
**Parent gate:** `G0_ALIGNMENT`

Gate 0 is split into two mandatory subgates:

```text
G0_ALIGNMENT
├── G0A_TRANSLATION_APPROVAL
└── G0B_ALIGNMENT_VERIFICATION
```

`G0_ALIGNMENT` may pass only when **both G0A and G0B pass**.

---

## G0A — Translation Approval

### Purpose

Verify that every LBF Spanish phrase used for the manual has been reviewed and approved against the intended source.

G0A is about the **Spanish translation itself**.

It does not certify reverse links.

### Input

For every phrase record:

- book/reference;
- MT/OSHB reference where numbering differs;
- Spanish phrase;
- source token IDs;
- source token surfaces;
- current `suggestionSource`;
- exact artifact revision/checksum.

### Allowed review decisions

```text
PENDING
APPROVED
NEEDS_REVISION
REJECTED
ESCALATE
```

### PASS criteria

G0A may pass only when:

1. every phrase record required by the book is present;
2. every phrase record has valid source-token references;
3. every phrase has been independently reviewed;
4. every phrase is `APPROVED`;
5. the corresponding Translator record is marked `lbf-approved`;
6. no `lbf-preliminary` record remains unless a project-specific exception was explicitly approved;
7. no unresolved `NEEDS_REVISION`, `REJECTED`, or `ESCALATE` item remains;
8. review is bound to the exact phrase-map revision/checksum;
9. required human linguistic approval is recorded.

### Automatic FAIL/BLOCK conditions

- missing phrase;
- invalid source token reference;
- empty Spanish phrase;
- `lbf-preliminary` remaining under normal policy;
- unresolved revision request;
- reviewer uncertainty not escalated;
- phrase-map file changed after review.

### Review standard

The reviewer asks:

- Does the Spanish account for the source span?
- Is something added that the source does not support?
- Is something omitted?
- Is the relationship between words/clauses distorted?
- Does the Spanish preserve the intended grammatical relationship sufficiently for CGV analysis?
- Is an ambiguity being falsely resolved?
- Is the phrase boundary itself defensible?

The reviewer must not approve merely because the Spanish sounds natural.

---

## G0B — Alignment Verification

### Purpose

Verify the relationship between Spanish units and OSHB source tokens.

G0B is about the **alignment**, not the quality of the Spanish prose.

### Input

For every reverse-link unit:

- reference;
- Spanish unit;
- character span;
- source token IDs;
- source token surfaces;
- current method;
- current status;
- phrase-map revision/checksum;
- reverse-link revision/checksum.

### Allowed review decisions

```text
PENDING
VERIFIED
NEEDS_RELINK
REJECTED
ESCALATE
```

### PASS criteria

G0B may pass only when:

1. all required verses have reverse-link records;
2. all reverse-link source-token IDs exist;
3. Spanish character spans match the phrase text;
4. every Spanish unit requiring alignment has been reviewed;
5. every unit is `VERIFIED`;
6. no seed-only or gloss-only unit remains under normal policy;
7. no unresolved `NEEDS_RELINK`, `REJECTED`, or `ESCALATE` item remains;
8. the final reverse-link status records verified alignment, not merely generation method;
9. review is bound to exact phrase-map and reverse-link revisions/checksums;
10. required human linguistic approval is recorded.

### Automatic FAIL/BLOCK conditions

- invalid token reference;
- character-span mismatch;
- unlinked required source material;
- seed-only/gloss-match unit remaining under normal policy;
- ambiguous relationship silently accepted;
- reverse-link file changed after review.

### Review standard

The reviewer asks:

- Does this Spanish unit actually correspond to these source tokens?
- Are relevant source tokens missing from the link?
- Are unrelated source tokens included?
- Does the link cross a grammatical boundary incorrectly?
- Does a mechanically plausible gloss-match produce a false semantic relationship?
- Does the alignment preserve the relationship needed for CGV observation?

A `gloss-match` may be correct, but **method is not verification**.

---

## Independence

Producer and verifier roles are separate.

For G0A:

```text
Translator produces phrase
        ↓
independent translation review
        ↓
human linguistic approval
```

For G0B:

```text
Translator seeds/builds alignment
        ↓
independent alignment review
        ↓
human linguistic approval
```

The same human may review both when appropriate, but the producer process may not self-certify.

---

## Review Evidence

Every reviewed item records:

```yaml
id:
gate:
reference:
artifact_revision:
artifact_checksum:
reviewer:
runtime:
model:
decision:
confidence:
evidence:
notes:
reviewed_at:
```

For AI-assisted review, `confidence` is advisory only.

A high-confidence AI result does not replace required human approval.

---

## Completion Summary

G0A must report:

```yaml
total:
approved:
pending:
needs_revision:
rejected:
escalated:
status:
```

G0B must report:

```yaml
total:
verified:
pending:
needs_relink:
rejected:
escalated:
status:
```

`status: PASS` is allowed only when the unresolved counts are zero and all required approval rules are satisfied.

---

## Parent Gate Rule

`G0_ALIGNMENT = PASS` requires:

```text
Translator deterministic producer checks = PASS
G0A_TRANSLATION_APPROVAL = PASS
G0B_ALIGNMENT_VERIFICATION = PASS
Human linguistic approval = PASS
Exact artifact checksums/revisions still match
No Gate 0 blocker remains
```

Only then may:

```text
G1_COMPILE = READY
```
