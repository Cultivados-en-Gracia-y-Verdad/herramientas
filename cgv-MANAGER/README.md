# CGV Manager v0.2

This version adds Gate 0 acceptance for verified `cgv-translator` attestations.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Existing project

If you already have `projects/daniel/state.yaml`, preserve it when replacing the app files.

## Gate 0

Translator produces `alignment-attestation.yaml`.

Manager accepts it with:

```bash
python3 manager.py gate0 accept daniel   --attestation /path/to/alignment-attestation.yaml
```

If and only if the attestation satisfies the Gate 0 contract, Manager records the
exact LBF/alignment revisions and checksums, sets `G0_ALIGNMENT = PASS`, and
sets `G1_COMPILE = READY`.

The producer cannot self-certify: producer checks, independent verification,
and required human linguistic review must all pass.
