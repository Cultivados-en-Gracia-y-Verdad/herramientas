# Agent Rules

Read `DATA_CONTRACT.md` before changing any data, import, export,
alignment, translation, approval, or dataset-loading code.

If a request conflicts with `DATA_CONTRACT.md`, stop and explain the conflict.
Do not work around it.

Never move, copy, regenerate, synchronize, or delete canonical data unless
the task explicitly names the source repository, destination repository,
migration phase, and validation procedure.

When uncertain which copy is authoritative, stop. Do not choose by timestamp,
file size, apparent completeness, or Git history alone.

- This application edits Biblia-LBF; it does not own translation data.
- Never create an independent canonical translation database.
- Never write directly to cgv-data.
- Never silently resolve revision conflicts.
- Machine suggestions cannot become approved without human action.