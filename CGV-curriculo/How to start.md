**How to start**

**0. Test the symlinks first.** Open Cursor and type `@arquitecto`. This is the one unverified assumption in everything we built — Cursor's docs never say whether it follows symlinks. If nothing appears: `cp -R herramientas/CGV-curriculo/.cursor/agents/*.md ~/.cursor/agents/` and we go back to copies plus a sync step. Don't start the book until this answers.

**1. Commit.** Four repos are still dirty.

**2. Jason finishes, then export Observer into the course** — `23.Apocalipsis/observation/`.

**3. Compiler Generate → `23.Apocalipsis/skeleton/`.** ⚠️ I rewrote the *instructions* so agents read from the course, but the Compiler is an app in cgv-reader and still exports where it always did. Until that app changes, you move the file yourself. Everything downstream now refuses `~/Downloads`.

**4. `/estructura`.** Arquitecto runs Step 0 (independent-clause verification) and gives a verdict. If **Bloqueado**, it stops — that's the gate working.

**5. Step 1 — the block inventory.** New, and the reason we did all this. Arquitecto proposes: which markers open units, how they group, the count and whether it came from markers or a decision, the form of each unit named in the book's own vocabulary, what each unit says, clause IDs. You approve it into `blocks.md`.

bash

```bash
python3 CGV-curriculo/scripts/verify-blocks.py \
  --blocks 23.Apocalipsis/blocks.md \
  --lbf cgv-data/bibles/LBF/apocalipsis.lbf.md
```

**6. Structure proposal** — H1/H2/H3, telos, title. Must be defensible from `blocks.md`.

**7. Context quotes**, once H2 spans exist:

bash

```bash
python3 CGV-curriculo/scripts/build-context-quotes.py \
  --manual 23.Apocalipsis/manual/manual.md \
  --lbf cgv-data/bibles/LBF/apocalipsis.lbf.md --write
```

**8. `/manual`** — Escriba on **`manual/manual.md`** (gate surface), one H3 per pass, reading `blocks.md`; the introduction must name the series with its counts.

**8b. Post-hearing enrichment** (if commentary is thin — one `>` per H4):

```bash
cd herramientas/CGV-curriculo/manager && python3 manager.py enrich-comments apocalipsis
```

Then `cgv verify-g7 apocalipsis` and `cgv verify-g8 apocalipsis` (gate surface changed → G7/G8 STALE).

**9. `@editor`** (mechanical) **then `@corrector`** (prose). `@corrector` is what `@editor` used to be.

The rest is untested by definition — Step 1 has never run, Escriba has never read a `blocks.md`, and no manual has carried `=` quotes. Apocalipsis is the first real exercise, so expect to find gaps. Tell me what breaks.