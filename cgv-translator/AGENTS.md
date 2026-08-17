# cgv-translator — agent entry point

Read [`DATA_CONTRACT.md`](DATA_CONTRACT.md) before changing any data, import,
export, alignment, translation, approval, or dataset-loading code.

If a request conflicts with `DATA_CONTRACT.md`, stop and explain the conflict.
Do not work around it.

Never move, copy, regenerate, synchronize, or delete canonical data unless the
task explicitly names the source repository, destination repository, migration
phase, and validation procedure.

When uncertain which copy is authoritative, stop. Do not choose by timestamp,
file size, apparent completeness, or Git history alone.

## What this repository is

This is the **human editing and approval application** for the LBF project. It
provides workflows over `Biblia-LBF`. It does **not** own a translation or
alignment corpus.

Canonical architecture: `Biblia-LBF/docs/architecture/CGV_DATA_ARCHITECTURE.md`.

## Hard rules

- Canonical input is a named `Biblia-LBF` branch and commit — not a copy kept
  here.
- Accepted edits are committed or proposed by pull request to `Biblia-LBF`.
- **Never publish directly to `cgv-data`.** Publication starts only after
  approvals are merged into `Biblia-LBF` and pass its export gate.
- Approval records the authenticated approver **and** the exact translation and
  alignment revisions approved. Approval on displayed text alone is not approval.
- A save that changes translation text invalidates affected approvals. A save
  that changes alignment invalidates alignment approval.
- Machine output is never automatically promoted to approved, and stays visually
  distinguishable from human decisions.
- Token ids are persisted. Never regenerate them from array position.
- Concurrent edits detect revision conflicts. Last-write-wins is prohibited.
- A cache or collaboration database is allowed only while `Biblia-LBF` stays
  authoritative and every accepted change is durably written back to Git.

## Before you open a pull request

```bash
python3 scripts/check-data-contract.py
```

The check is read-only and needs no dependencies. It fails on any violation not
already listed in `.data-contract-baseline.json` — the problems that existed when
the check was introduced. Shrink that list; never grow it.

The baseline is large, and it is honest about two things:

- `translations/` currently holds a full parallel corpus, which is exactly what
  this contract prohibits. It is baselined so the check can go live, not because
  it is acceptable.
- `CLAUDE-FAIL/` holds an archived approval system whose records carry approval
  decisions with no approver and no revision binding. It is archived, not fixed.

Do not edit data to make a check pass. If a check is wrong, fix the check and say
so in the pull request.
