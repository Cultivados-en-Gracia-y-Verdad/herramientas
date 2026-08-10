# Gate 0 Contract — cgv-translator → cgv-MANAGER

**Version:** 0.1

## Purpose

This contract defines the exact evidence `cgv-MANAGER` requires before it may mark `G0_ALIGNMENT` as `PASS`.

`cgv-translator` is the producer. It does not grant itself permission to proceed.

## Required Inputs

Manager must receive:

1. LBF source artifact.
2. LBF alignment artifact.
3. Source revision and SHA-256 checksum.
4. Alignment revision and SHA-256 checksum.
5. Producer self-check report.
6. Independent verification report.
7. Human/linguistic review when required.
8. `alignment-attestation.yaml`.

## Required PASS Conditions

Manager may accept Gate 0 only when all of the following are true:

```text
attestation.status == VERIFIED
producer.status == PASS
independent_verification.status == PASS
human_linguistic_review.status == PASS
```

Additionally:

- book/project identity matches the Manager project;
- source is declared as LBF;
- source revision is non-empty;
- alignment revision is non-empty;
- source checksum matches the current source file;
- alignment checksum matches the current alignment file;
- every required producer check is `PASS`;
- every required independent check is `PASS`;
- no unresolved blocker exists;
- no unresolved CRITICAL finding exists.

## Automatic Rejection Conditions

Manager must reject the attestation for a wrong book/project, wrong source identity, missing revision, checksum mismatch, stale attestation, incomplete or failed producer verification, incomplete or failed independent verification, incomplete required human review, unresolved blocker, unsupported schema version, or artifact change after verification.

## Revision Binding

Verification is bound to exact revisions and checksums.

If source or alignment identity changes, prior verification becomes stale.

If a downstream artifact already exists, Manager must mark Gate 0 stale, block compilation, mark the artifact non-current, and require regeneration.

## Independence Requirement

The independent verifier must not be the same logical process that generated the artifact.

The verifier may use the same repository and tooling but must run as a distinct verification task with instructions prohibiting modification.

For judgment-heavy checks, use a different model/runtime from the producer when practical.

Human linguistic approval must be explicit and attributable.

## Repair Loop

```text
producer revision N
    ↓
verification FAIL
    ↓
producer repairs
    ↓
producer revision N+1
    ↓
all required verification reruns
```

No failed verification may be converted to PASS merely by editing the attestation.

## Manager Responsibility

Manager verifies the contract and controls progression.

Manager does not translate, align, silently repair, decide linguistic questions outside its authority, or accept producer confidence as proof.
