# CGV Verification Independence Addendum

**Status:** Draft  
**Scope:** All CGV producer stages  
**Applies first to:** LBF translation and alignment

## Core Rule

**A component that creates a high-risk artifact may not be the sole authority that validates that artifact.**

The universal pattern is:

```text
PRODUCER
    ↓
producer self-checks
    ↓
INDEPENDENT VERIFIER
    ↓
human/specialist approval where required
    ↓
WORKFLOW GATE
```

Producer self-checks are evidence, not certification.

## Gate 0 Ownership

For LBF workflows:

- `cgv-translator` owns creation and maintenance of LBF text and alignment.
- `cgv-translator` runs deterministic producer checks.
- an independent verifier reviews the produced artifact without modifying it.
- qualified human/linguistic review resolves questions software cannot safely decide.
- `cgv-MANAGER` validates the attestation identity, revisions, checksums, required PASS states, and blockers.
- only `cgv-MANAGER` authorizes progression to Compiler Generate.

## Failure Behavior

Any failed or incomplete required verification blocks Gate 0.

A producer may repair its output after a failed check, but the repaired revision must be reverified.

A changed source or alignment revision invalidates prior verification.

No downstream component may compensate for an unresolved Gate 0 defect.
