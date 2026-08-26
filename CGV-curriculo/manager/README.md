# CGV Manager v0.2

This version adds Gate 0 acceptance for verified `cgv-translator` attestations.

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
