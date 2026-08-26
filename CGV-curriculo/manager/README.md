# CGV Manager v0.3

The Manager is the authoritative workflow record for one CGV book. Version 0.3
adds a graphical, large-text dashboard that follows `RUNBOOK.md`, plus the
existing command-line interface.

The Manager lives with the method in `herramientas/CGV-curriculo/manager/`, while
authoritative course state lives with each course:

```text
curriculo/<course>/state.yaml
```

The shared state template lives at:

```text
herramientas/CGV-curriculo/templates/state.template.yaml
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The macOS system Python already supplies the only runtime dependency on the
current CGV workstation.

## Graphical Manager

Double-click:

```text
CGV Manager.app
```

The app opens a local dashboard at `http://127.0.0.1:8765/`. It reads and writes
the selected course's canonical `state.yaml`; it does not keep a second copy of
project state.

The dashboard exposes the operator sequence from preflight through release:

- Cursor agent confirmation and repository cleanliness;
- course validation;
- verified Gate 0 acceptance or an explicit recorded waiver;
- Observer and Compiler imports into the course;
- skeleton, block, quote, final, and provenance checks;
- recorded human gate decisions.

Files selected in the dashboard are copied into the course's `observation/`,
`skeleton/`, or `attestations/` folder. Downstream work never reads Downloads.

## Existing course

Pass either the project ID or the course folder name to every command:

```bash
python3 manager.py status apocalipsis
python3 manager.py status 23.Apocalipsis
```

Both read and write `curriculo/23.Apocalipsis/state.yaml` directly.

## Gate 0

Translator produces `alignment-attestation.yaml`.

Manager accepts it with:

```bash
python3 manager.py gate0 accept apocalipsis \
  --attestation /path/to/alignment-attestation.yaml
```

If and only if the attestation satisfies the Gate 0 contract, Manager records the
exact LBF/alignment revisions and checksums, sets `G0_ALIGNMENT = PASS`, and
sets `G1_COMPILE = READY`.

The producer cannot self-certify: producer checks, independent verification,
and required human linguistic review must all pass.

An operator may explicitly waive Gate 0 with a recorded reason. A waiver is
stored as `SKIPPED`, never `PASS`; the Manager snapshots the exact source and
alignment checksums so the Compiler gate can still detect drift.
