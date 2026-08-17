# CGV Translator

CGV Translator is a future translation workspace for producing faithful Bible translations from the biblical languages.

This repository currently exists to document the workflow, specifications, and feature candidates discovered while translating Titus for La Biblia Fiel.

Translator does not replace the translator.

Translator exposes evidence, records decisions, manages history, and assists the human translator in remaining accountable to the biblical text.

## Verify a Book for Approval

There is one active approval path and two required results: `TRANSLATION PASS` and `ALIGNMENT PASS`.

```sh
npm run verify:book -- prepare daniel
npm run verify:book -- status daniel
npm run release:status -- daniel
```

`prepare` performs strict, mechanical completeness checks. It never approves anything. AI verification is prohibited.

G0A is a book reading. Read the continuous Spanish. If the book is acceptable, record one PASS on that revision:

```sh
npm run verify:book -- record-book daniel translation PASS --reviewer "Name" --human-confirmation
```

If a verse is wrong, record that finding first:

```sh
npm run verify:book -- record daniel translation "Daniel 1:1" CHANGES_REQUIRED --reviewer "Name" --notes "…" --human-confirmation
```

`record-book` stores one human book attestation on the pending verses. It cannot bypass review independence, cannot record AI review, and cannot start alignment review before the current translation revision has G0A `PASS`.
`release:status` writes the exact remaining blockers to
`verification/{book}/release-readiness.json`.

See [WORKFLOW.md](WORKFLOW.md) for the complete, canonical process. Legacy Gate 0 paperwork has no approval authority and is preserved only under `CLAUDE-FAIL/`.

## Run the Investigation View Prototype

From this folder:

```sh
npm start
```

Then open:

```text
http://127.0.0.1:1424/
```

### Optional local AI phrase suggestions (LM Studio)

The configured local provider is LM Studio. It may propose drafting suggestions, but it cannot verify, approve, or publish anything.

1. Install LM Studio and load a chat-capable model.
2. In LM Studio's **Developer** tab, start the Local Server on port `1234`.
3. CGV Translator discovers the first model returned by `/v1/models`, unless `CGV_TRANSLATOR_LMSTUDIO_MODEL` is set explicitly.

Provider overrides go in `.env` (see `.env.example`). Ollama and the existing cloud providers remain available as alternatives.

### Translation drafting pipeline

1. **Analyze phrase** — mechanical Gates 1–5 + grammar skeleton (Gate 4 loads verse ±2 + local LBF)
2. **Propose Spanish** — AI drafts modern Spanish under those constraints
3. **Use draft** — copies into working Spanish for human editing before verification

Grammar checks reject illegal readings and RV1909 orthography bleed. If AI fails checks, the mechanical skeleton is shown instead.

### Textual basis (TR)

LBF’s Greek authority is **Scrivener 1894 TR**. When a book has a TR spine under
`translations/tr-spine/{bookId}/`, the translator loads:

- `{bookId}-phrases-tr.json` for phrase Spanish / token ids
- `{bookId}-tr-spine.json` for Greek verse tokens (not MorphGNT/SBLGNT)

Titus, Jude, 1 John, and Revelation have TR spines. Other books still fall back to MorphGNT until theirs exist.

Rebuild from Robinson-parsed UTR:

```sh
python3 scripts/build_tr_spine_titus.py
python3 scripts/build_tr_spine_jude.py
python3 scripts/build_tr_spine_1john.py
python3 scripts/build_tr_spine_revelation.py
```

Sources: `Biblia-LBF/source/greek/TR1894/robinson-parsed/{TIT,JUDE}.UTR`

### Reverse interlinear (Titus pilot)

Spanish unit → TR `sourceTokenIds` live in a separate file (not on phrase saves):

`translations/tr-spine/titus/titus-reverse-links.json`

```sh
python3 scripts/seed_titus_reverse_links.py
```

Phrases 0–10 (+ selected fixes) are hand-seeded; plain auto-zip is weak.

Prefer AI seeding with lemma + morphology + Strong’s:

```sh
node scripts/ai_seed_titus_reverse_links.mjs --start 11 --limit 10
```

This preserves `seeded-hand` entries and writes `seeded-ai` (or `seeded-ai-invalid` if
validation fails). Requires the configured local provider (LM Studio or Ollama) or cloud keys.

In the UI, use the **Reverse interlinear** row — click a unit to highlight linked Greek.

### Preliminary LBF seed (per book)

Phrase files are the source of truth for the editor:

- `translations/titus-phrases.json`
- `translations/philemon-phrases.json`
- `translations/hebrews-phrases.json`
- `translations/james-phrases.json`
- `translations/1peter-phrases.json`
- `translations/2peter-phrases.json`
- `translations/1john-phrases.json`
- `translations/2john-phrases.json`
- `translations/3john-phrases.json`
- `translations/jude-phrases.json`
- `translations/revelation-phrases.json`
- `translations/matthew-phrases.json`
- `translations/mark-phrases.json`
- `translations/luke-phrases.json`
- `translations/john-phrases.json`
- `translations/acts-phrases.json`
- `translations/romans-phrases.json`
- `translations/1corinthians-phrases.json`
- `translations/2corinthians-phrases.json`
- `translations/galatians-phrases.json`
- `translations/ephesians-phrases.json`
- `translations/philippians-phrases.json`
- `translations/colossians-phrases.json`
- `translations/1thessalonians-phrases.json`
- `translations/2thessalonians-phrases.json`
- `translations/1timothy-phrases.json`
- `translations/2timothy-phrases.json`

Rebuild / refresh a preliminary Spanish seed:

```sh
python3 scripts/rebuild_matthew_phrases.py
python3 scripts/rebuild_mark_phrases.py
python3 scripts/rebuild_luke_phrases.py
python3 scripts/rebuild_john_phrases.py
python3 scripts/rebuild_acts_phrases.py
python3 scripts/rebuild_romans_phrases.py
python3 scripts/rebuild_1corinthians_phrases.py
python3 scripts/rebuild_2corinthians_phrases.py
python3 scripts/rebuild_galatians_phrases.py
python3 scripts/rebuild_ephesians_phrases.py
python3 scripts/rebuild_philippians_phrases.py
python3 scripts/rebuild_colossians_phrases.py
python3 scripts/rebuild_1thessalonians_phrases.py
python3 scripts/rebuild_2thessalonians_phrases.py
python3 scripts/rebuild_1timothy_phrases.py
python3 scripts/rebuild_2timothy_phrases.py
python3 scripts/rebuild_titus_phrases.py
python3 scripts/rebuild_philemon_phrases.py
python3 scripts/rebuild_hebrews_phrases.py
python3 scripts/rebuild_james_phrases.py
python3 scripts/rebuild_1peter_phrases.py
python3 scripts/rebuild_2peter_phrases.py
python3 scripts/rebuild_1john_phrases.py
python3 scripts/rebuild_2john_phrases.py
python3 scripts/rebuild_3john_phrases.py
python3 scripts/rebuild_jude_phrases.py
python3 scripts/rebuild_revelation_phrases.py
```

Open a book in the UI via the Book menu, or:

```text
http://127.0.0.1:1424/?book=matthew
http://127.0.0.1:1424/?book=mark
http://127.0.0.1:1424/?book=luke
http://127.0.0.1:1424/?book=john
http://127.0.0.1:1424/?book=acts
http://127.0.0.1:1424/?book=romans
http://127.0.0.1:1424/?book=1corinthians
http://127.0.0.1:1424/?book=2corinthians
http://127.0.0.1:1424/?book=galatians
http://127.0.0.1:1424/?book=ephesians
http://127.0.0.1:1424/?book=philippians
http://127.0.0.1:1424/?book=colossians
http://127.0.0.1:1424/?book=1thessalonians
http://127.0.0.1:1424/?book=2thessalonians
http://127.0.0.1:1424/?book=1timothy
http://127.0.0.1:1424/?book=2timothy
http://127.0.0.1:1424/?book=revelation
http://127.0.0.1:1424/?book=jude
http://127.0.0.1:1424/?book=3john
http://127.0.0.1:1424/?book=2john
http://127.0.0.1:1424/?book=1john
http://127.0.0.1:1424/?book=2peter
http://127.0.0.1:1424/?book=1peter
http://127.0.0.1:1424/?book=james
http://127.0.0.1:1424/?book=hebrews
http://127.0.0.1:1424/?book=philemon
http://127.0.0.1:1424/?book=titus
```

Each phrase’s `spanish` field loads into the Working Spanish textarea with
`suggestionSource: lbf-preliminary`. Edit phrase by phrase; saving keeps your
changes in that book’s phrases file.

### Batch review loop (b)

```sh
node scripts/batch_lbf_propose.mjs --limit 8 --start "Titus 2:1"
```

Then human-review `translations/review-log.jsonl`, edit/approve phrases in `titus-phrases.json`, and encode recurring misses in `src/ai/lbf-translation-rules.md` + `assistGates.js` validators.

Batch propose skips phrases that already have preliminary/approved Spanish.

Default local model: `qwen2.5:7b` (set in `.env`). `llama3.2` is too weak for this task.

AI translation discipline lives in:

```text
src/ai/lbf-translation-rules.md
```

The prototype reads and writes plain Markdown files in `investigations/`. During this stage, those Markdown files remain the source of truth.
Investigation Stop Rule

Begin an investigation only when the translation decision cannot be made responsibly from existing project policy.

If an existing policy already answers the question, apply the policy and continue translating.

Investigations exist to establish policy.

Not to repeatedly justify established policy.
