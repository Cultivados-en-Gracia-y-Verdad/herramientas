# Gender and number in BLE

The Greek/Hebrew `morph` field carries full gender and number. BLE **must** reflect that in Spanish glosses wherever Spanish grammar requires agreement—not only for articles and pronouns.

## Current state (systemic gap)

| Layer | Gender-aware? | Mechanism |
|-------|---------------|-----------|
| Articles (`ὁ`) | Yes | `grc_article_by_morph.json` |
| Pronouns (`αὐτός`, `ὅς`, …) | Yes | per-lemma morph tables |
| Nouns & adjectives | **Mostly no** | single entry in `grc_lemma_lexicon.json` per lemma |

Examples of the gap:

| Reference | Greek | Morph | BLE today | Expected |
|-----------|-------|-------|-----------|----------|
| Rom 16:1 | διάκονον | acc. sg. fem. | servidor | servidora |
| 1 Tim 3:11 | γυναῖκας … σεμνάς | fem. pl. | mujer … honesto | mujeres … honestas |
| Acts 2:17–18 | υἱοί / θυγατέρες | | hijos / hijas ✓ | nouns may still lack plural agreement elsewhere |

A scan of NT tokens finds **~200 lemmas** that appear in both masculine and feminine inflected forms but carry **one fixed Spanish gloss** for every occurrence. That is diagnostic—not every hit is a translation error (some lemmas are genuinely epicene in Spanish, e.g. *persona*), but it confirms the pipeline does not yet apply morphology systematically.

**Conclusion:** source gender is preserved in the data; BLE does not yet convert it systematically into Spanish gender and number.

## Target behavior

1. **Lemma lexicon** stores a *lemma gloss* (typically masculine singular for adjectives, citation form for nouns).
2. **Morph inflection** derives the surface gloss from `lemma` + `morph` before writing `es` (same pattern as articles).
3. **Overrides** remain for irregular forms, names, and idioms.

Spanish inflection targets at minimum:

- **Gender:** -o / -a (servidor → servidora; honesto → honesta)
- **Number:** plural -s / -es (honesto → honestos / honestas)
- **Neuter** Greek: often maps to singular Spanish without gender flip on the noun itself; case-by-case in lexicon notes

Participles and adjectives agree with their head noun’s gender/number in the Greek token’s morph tag.

Remove `ἐγώ` / `σύ` from generic lexicon lookups when morph tables exist — see `grc_ego_by_morph.json`, `grc_su_by_morph.json`, and `ble/scripts/reapply_pronoun_glosses.py`.

| Greek | Morph | BLE gloss |
|-------|-------|-----------|
| ἐγώ | RP----NS-- | yo |
| ἐγώ | RP----GS-- | de·mí |
| ἐγώ | RP----GP-- | de·nosotros |
| ἐγώ | RP----DS-- | a·mí |
| ἐγώ | RP----DP-- | a·nosotros |
| ἐγώ | RP----AS-- | me |
| ἐγώ | RP----AP-- | nos |
| ἐγώ | RP----NP-- | nosotros |
| σύ | RP----DP-- | a·ustedes |
| σύ | RP----GP-- | de·ustedes |
| … | | full tables in `grc_su_by_morph.json` |

**Never** map the lemma label `ἐγώ` → `yo` for every form. ἡμῶν is genitive plural (`de·nosotros`), not `yo`.

## Inclusive masculine plurals (policy)

Greek masculine plurals such as ἀδελφοί may refer to mixed groups. BLE is **token-aligned**, not referential:

| Approach | BLE text | Notes |
|----------|----------|-------|
| **Adopted** | hermanos | Preserve grammatical masculine plural in the literal line |
| Rejected for main text | hermanos y hermanas | Adds a Spanish noun not present as a token |

Referential scope (“brothers and sisters”) belongs in **interlinear notes** or a separate study layer—not inserted into the assembled verse.

## Implementation path

1. **`audit_gender_glosses.py`** — list lemmas with mixed gender morphology and a single gloss (prioritize fixes).
2. **`grc_inflect_es.py`** (or extend `next_step.py`) — rule-based Spanish inflection from lemma gloss + morph for `N` and `A` tags (and participles).
3. **Re-run `next_step.py`** on affected books, then regenerate interlinear readers and `.ble.md`.
4. **Human review** via interlinear export for high-impact passages (Rom 16, 1 Tim 3, Acts 2).

## What not to do

- Do not “fix” gender in `tokens_to_ble.py` assembly—that step only joins glosses; agreement must be correct in each token’s `es` field.
- Do not smooth inclusive plurals in the literal Bible without an explicit, documented policy change.
