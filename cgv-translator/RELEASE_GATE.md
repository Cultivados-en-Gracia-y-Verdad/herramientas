# LBF Release Boundary

`cgv-data` is release-only.

A book cannot be published unless the active verifier reports:

```text
TRANSLATION   PASS
ALIGNMENT     PASS
BOOK          PASS
```

The PASS results must match the exact source, Spanish, and alignment bytes used to build the release.

Publication also requires:

- resolved required investigations;
- a completed book-level consistency review;
- no open blocker;
- an explicit LBF edition and immutable book version;
- explicit source, translation, and alignment revisions;
- named human approval;
- the final artifact SHA-256;
- post-publication verification of the bytes in `cgv-data`;
- registration of that exact artifact with `cgv-MANAGER`.

If any requirement is missing, failed, stale, pending, blocked, or inferred from legacy paperwork, the book is **NOT RELEASE READY**.

Corrections require a new approval and release identity. A published artifact must never be silently replaced.
