# Archived Failed Approval System

Archived on 2026-08-14 during the clean restart of the LBF book approval process.

This directory is preservation, not production. Nothing here has verification or approval authority.

## Contents

- `gate0/` — the former queues, packets, evidence chains, result files, repair reports, promotion reports, policies, templates, and runners;
- `workflow/` — in-progress workflow logs from the failed Daniel run;
- `snapshots/investigations-current/` — the full investigation tree as it existed immediately before cleanup;
- `snapshots/` — copies of the modified application and Daniel files before they were restored to the last committed versions;
- `loose-files/` — generated backups, caches, temporary scripts, and pre-promotion artifacts;
- `legacy-scripts/` — regression scripts coupled to the removed Gate 0 file layout.

The active process is defined only by the repository-root `WORKFLOW.md` and `scripts/book_workflow.py`.

## Why it was retired

The former system had multiple competing representations of truth, depended on a package not available in the normal repository environment, could not read Titus's established phrase format, and allowed large volumes of generated paperwork to obscure whether translation and alignment had actually passed.

The replacement exposes two direct, hash-bound results:

```text
TRANSLATION PASS
ALIGNMENT PASS
```

Both require explicit human decisions for the exact current evidence.
