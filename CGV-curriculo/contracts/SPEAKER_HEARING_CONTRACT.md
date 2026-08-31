# Speaker / Hearing Mechanical Verification

**Status:** Binding  
**Gates:** `G7_EDITORIAL` · `G8_FINAL_VERIFY`  
**Script:** `scripts/verify-speaker-hearing.py`

## Core rule

**Speaker attribution and hearing-apparatus defects that a machine can detect must
block G7/G8. They are not deferred to human review.**

Human review (`G9_HUMAN_REVIEW`) comes **only after** the mechanical stream passes.

## Why

Actores tallies and flecha triples are not neutral. They have invented speakers
(Apocalipsis 22:17 *Ven* attributed to Jesús; 22:18 identified without reserve;
22:20 vocative inverted as subject). Agent self-certification at G7 failed to catch this.

## Gate witness — script sets PASS/FAIL (humans do not)

Humans and agents **run** verification. They do **not** approve G7/G8.

```bash
cgv verify-g7 {libro}    # exit 0 → Manager records G7_EDITORIAL PASS
                         # exit 1 → Manager records G7_EDITORIAL FAIL

cgv verify-g8 {libro}    # exit 0 → Manager records G8_FINAL_VERIFY PASS
                         # exit 1 → Manager records G8_FINAL_VERIFY FAIL
```

Same from the Manager UI (`run-g7-check` / `run-final-checks`).

Hand `cgv gate … PASS` for G7/G8 is **rejected**. Evidence is bound to the manual
checksum; edit the manual under a PASS → gate becomes `STALE` until re-verify.

Report: `{NN.Curso}/reports/SPEAKER_HEARING_REPORT.md`.

Low-level scripts (Manager wraps these):

```bash
python3 scripts/verify-g7-editorial.py --manual {NN.Curso}/manual/manual.md
python3 scripts/verify-g8-final.py --manual … --lbf … --blocks … --book …
```

## When G7 FAILs → Corrector (not a human PASS)

```bash
cgv correct-g7 {libro}     # mechanical Corrector on gate surface → re-verify
# still FAIL? @corrector for remaining CRITICAL, then cgv verify-g7 again
```

`scripts/correct-g7-surface.py` deletes Actores, stock *El recuento* /
*Esto es lo que hay que oír*, and known speaker-poison patterns. Agent Corrector
owns hearing rewrites the script must not invent.

Gate surface is `manual/manual.md` when present (what verify scores) — not a
sibling editor draft left unpromoted.

## What blocks (deterministic)

| Severity | Examples |
|---|---|
| CRITICAL | `* Yo, Jesús → Ven`; *Quien Ven es…*; denying Espíritu/novia; vocative as `* Señor Jesús → ven`; false “22:18: Yo, Jesús, doy testimonio” |
| HIGH (G7) | Any `* Actores principales:` on student surface; *El recuento*; *Esto es lo que hay que oír* |
| HIGH (G8) | Flecha / slot / *todavía no* density over caps |

## Independence

- Escriba / Corrector produce the manuscript.
- This script verifies; it does not rewrite.
- Corrector may repair after FAIL; the repaired revision must be re-run (`cgv verify-g7` again).
- G9 human reading addresses blind spots — not a substitute for mechanical PASS.

## Not a verdict on release

Mechanical G8 PASS ≠ released. `G9_HUMAN_REVIEW` and `G10_RELEASE` remain.
