## BLE Output Changes

This document records the BLE output changes made in the recent correction pass.

Scope:
- These changes were applied through the token-to-BLE pipeline, not by hand-editing published `.ble.md` files.
- The goal was to preserve BLE's Greek-exposure translation philosophy while correcting recurring output problems.
- This file documents the changes that affected published BLE output during this pass.

## Translation Philosophy Preserved

BLE remains a Greek-exposure study tool in Spanish, not an idiomatic reader's Bible.

The correction pass kept these priorities:
- preserve Greek word order as much as possible
- preserve one Greek lexical word to one Spanish lexical word where possible
- avoid paraphrase
- avoid smoothing Spanish for readability
- preserve repetition and clause structure

## What Changed

### 1. Published function-word marking was standardized

BLE token glosses use mid-dot forms such as `de·Dios` and `por·medio·de`.
Published BLE output now consistently marks inserted function words with a bullet in the assembled text:

- token gloss: `de·Dios`
- published BLE: `de•Dios`

Implemented in:
- `scripts/ble_gloss_text.py`
- `scripts/tokens_to_ble.py`

Current examples in output:
- `Tito 1:1` -> `siervo de•Dios`
- `Tito 1:5` -> `por• causa•`
- `Apocalipsis 1:1` -> `por• medio• de•`

### 2. Compound function words are now split correctly

Published BLE now handles compound forms more consistently when converting token glosses to display text.

Examples:
- `del` is treated as `de`
- `al` is treated as `a el`

This affects how inserted function words appear in BLE output, especially around genitives and prepositional phrases.

Implemented in:
- `scripts/ble_gloss_text.py`

### 3. Repeated text-level spelling fixes were centralized

Several recurring output typos were moved into a shared text-fix layer so they are corrected automatically during BLE assembly.

Documented fixes include:
- `apartarses` -> `apartarse`
- `apropiarses` -> `apropiarse`
- `discusiónes` -> `discusiones`
- `varónes` -> `varones`

Implemented in:
- `scripts/ble_gloss_text.py`

Current examples in output:
- `Tito 2:5` -> `varones`
- `Tito 3:9` -> `discusiones`
- `Tito 2:10` -> `apropiarse`

### 4. Surface-specific overrides were made reliable

Surface-form overrides now normalize Greek punctuation and editorial marks before matching.
This made special-case rules apply more reliably to forms that previously failed because of casing or punctuation noise.

Implemented in:
- `scripts/reapply_surface_glosses.py`
- `scripts/ble_gloss_text.py`

This includes support for:
- punctuation-stripped surface matching
- removal of marks such as `⸀`, `⸂`, `⸃`
- case-insensitive handling of special forms

### 5. `δεῖ` no longer publishes as the lexical gloss `atar`

One major correction in BLE output was the handling of the impersonal verb `δεῖ`.

Before this pass, BLE output could leave `δεῖ` with the lexical-style gloss `atar`, which is wrong in context for the impersonal construction.

Now:
- `δεῖ` is protected from generic verb re-conjugation
- the surface-gloss layer can override it correctly
- published BLE shows `debe` where appropriate

Implemented in:
- `scripts/ble_gloss_text.py`
- `scripts/reapply_verb_glosses.py`
- `scripts/reapply_surface_glosses.py`

Current examples in output:
- `Tito 1:7` -> `debe porque el obispo irreprensible ser`
- `Tito 1:11` -> `cual debe tapar la boca`
- `Apocalipsis 1:1` -> `cual debe llegar a• ser en pronto`

### 6. Verb glosses were re-conjugated from lemma plus morphology

Finite and infinitive verb glosses were re-generated from the lemma lexicon and Greek morphology instead of being left in rough lexical form.

This improved BLE output while still keeping the literal/Greek-exposure style.

Implemented in:
- `scripts/reapply_verb_glosses.py`

Notable output examples:
- `Tito 2:1` -> `conviene`
- `Tito 2:6` -> `ruega`
- `Tito 1:16` -> `confiesan`
- `Tito 3:1` -> `recuerda`

### 7. Noun and adjective glosses were re-inflected

Nominal glosses were re-applied from the lemma lexicon and Greek morphology so number and gender are reflected more consistently in BLE output.

Implemented in:
- `scripts/reapply_nominal_glosses.py`

This helped stabilize output forms across the published BLE files, especially in repeated lexical items and agreement-sensitive contexts.

### 8. Genitive marking was reapplied more consistently

Genitive relationships were re-marked so BLE output more consistently signals Spanish `de` relationships in token glosses and published assembly.

Implemented in:
- `scripts/reapply_case_glosses.py`

This is visible throughout output such as:
- `de•Dios`
- `de•Cristo`
- `de•Jesús`
- `de•la`
- `de•nosotros`

### 9. Lexical renderings were corrected in recurring problem words

Specific lexical outputs were corrected where BLE was publishing the wrong Spanish choice.

Documented lexical corrections from this pass include:
- `διάβολος` -> `calumniador`
- `ζηλωτής` -> `celoso`

These corrections were made upstream in the token-gloss pipeline and then propagated into BLE output.

Current output examples:
- `Tito 2:14` -> `celoso buenos obras`
- `Tito 2:3` -> `no calumniadoras`

Note:
- Some interlinear token files may still show older lexical placeholders if they were inspected before the rebuilt published output or if related upstream token sources were not yet fully refreshed in the same place.
- The published BLE target of this correction pass was the assembled BLE output.

## Pipeline Order Used

The correction pass depended on running the token reapplication scripts before rebuilding BLE output.

Recommended rebuild order:

```bash
cd "herramientas/Biblia - BLE"
python3 scripts/reapply_case_glosses.py --all
python3 scripts/reapply_nominal_glosses.py --all
python3 scripts/reapply_agreement_glosses.py --all
python3 scripts/reapply_verb_glosses.py --all
python3 scripts/reapply_surface_glosses.py --all
python3 scripts/tokens_to_ble.py --all
```

Notes:
- `reapply_surface_glosses.py` should run after the broader morphology-driven passes so surface-specific corrections can win where needed.
- `tokens_to_ble.py` is the final publish step that converts token glosses into `.ble.md` output.

## Files Involved

Primary BLE output/publish files:
- `scripts/tokens_to_ble.py`
- `scripts/ble_gloss_text.py`
- `output/*.ble.md`

Primary correction passes:
- `scripts/reapply_case_glosses.py`
- `scripts/reapply_nominal_glosses.py`
- `scripts/reapply_verb_glosses.py`
- `scripts/reapply_surface_glosses.py`
- `scripts/reapply_agreement_glosses.py`

## Summary

In this correction pass, BLE output was improved in four main ways:
- published function-word marking became more consistent
- Greek morphology was reapplied more reliably to verbs and nominals
- recurring lexical and spelling errors were corrected
- special-case surface overrides, especially `δεῖ`, were made reliable in the final BLE output
