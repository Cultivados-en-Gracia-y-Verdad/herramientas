# CGV — producing a book, end to end

The order of work for one book, with the command at each transition.

`WORKFLOW.md` says what must happen and why. `STATE_MODEL.md` defines the gates. **This file is
the operator's sequence.** If they disagree, they are the authority and this is the defect.

Run everything from the GitHub root. A shortcut worth setting once:

```bash
alias cgv='python3 ~/Nextcloud/Documents/GitHub/herramientas/CGV-curriculo/manager/manager.py'
alias cgvs='python3 ~/Nextcloud/Documents/GitHub/herramientas/CGV-curriculo/scripts'
```

`cgv status <libro>` at any moment tells you the current gate and the next action. **The Manager is
authoritative — never infer state from a conversation.**

---

## Preflight

- [ ] `@arquitecto` appears in Cursor. The agents live in `herramientas/CGV-curriculo/.cursor/` and
      reach every workspace through symlinks in `~/.cursor/`. Cursor's docs do not say whether it
      follows symlinks. **Until someone types `@arquitecto` this is unverified.** If nothing appears:
      `cp -R herramientas/CGV-curriculo/.cursor/agents/*.md ~/.cursor/agents/` and accept a sync step.
- [ ] All repos committed. Cross-repo work reads badly when it lands piecemeal.
- [ ] The course exists with `spec.md`, `blocks.md`, `state.yaml` and the pipeline folders.
- [ ] `cgv validate <libro>` → VALID.

---

## G0_ALIGNMENT — source and alignment

The producer does not certify itself. `contracts/GATE0_CONTRACT.md` requires producer checks,
**independent** verification, human linguistic review, and revisions with SHA-256 checksums.
A `translation: done · alignment: done` header is the producer's self-check — evidence, not
certification.

```bash
cgv gate0 accept <libro> --attestation path/to/alignment-attestation.yaml
```

If you choose to proceed without an attestation, say so on the record rather than faking a pass:

```bash
cgv gate <libro> G0_ALIGNMENT SKIPPED --notes "reason, and who decided"
```

Never hand-set `PASS`. That is the producer self-certifying.

---

## G1_COMPILE — Observer to skeleton

1. Jason assists the human until the Observer JSON is complete. Jason is not a workflow stage.
2. Export the Observer progress into `{NN.Curso}/observation/`.
3. **Check the spans before Generate.** A bad span costs a whole Generate cycle:

```bash
cgvs/verify-clause-spans.py --progress {NN.Curso}/observation/<libro>-progress-filled.json \
                            --lbf cgv-data/bibles/LBF/<libro>.lbf.md
```

   It catches what the skeleton gate cannot — non-contiguous spans, which produce H4s with words
   silently missing. Repair in Observer; never in the skeleton, which regenerates.

4. Compiler Generate → `{NN.Curso}/skeleton/`.
   **⚠️ The Compiler still exports where it always did.** Until the app changes, move the file
   yourself. Every agent downstream refuses `~/Downloads`.
5. Record the compile. This is the gate:

```bash
cgv compile record <libro> \
  --skeleton {NN.Curso}/skeleton/<libro>-manual-skeleton.md \
  --progress {NN.Curso}/observation/<libro>-progress-filled.json \
  --compiler-version "cgv-reader YYYY-MM-DD"
```

It records which inputs produced which artifact, with checksums, and **refuses if the source or
alignment has changed since G0** — a compile against changed source is not a compile of the
approved book.

---

## G2_MECHANICAL — the skeleton is fit to build on

```bash
cgvs/verify-skeleton-h4-packaging.py --manual {NN.Curso}/skeleton/<libro>-manual-skeleton.md \
                                     --lbf cgv-data/bibles/LBF/<libro>.lbf.md
cgvs/run-manual-checks.py --manual {NN.Curso}/skeleton/<libro>-manual-skeleton.md \
                          --lbf cgv-data/bibles/LBF/<libro>.lbf.md --book <libro>
```

The first is blocking. The second **never prints PASS by design** — it emits evidence and its own
blind spots, because it once returned clean on a Daniel skeleton whose hinge verse was in no line
at all. **Then read the surface yourself.** A script and a reading are two witnesses; if they
disagree the verdict is blocked.

```bash
cgv gate <libro> G2_MECHANICAL RUNNING
cgv gate <libro> G2_MECHANICAL PASS --notes "script + reading agree"
```

---

## G3_TEXTUAL · G4_SPECIALISTS

Verificador and the Specialists appear in the authority table and **have no agent file yet**. Until
they exist, do this work by reading and record what you actually did:

```bash
cgv gate <libro> G3_TEXTUAL PASS --notes "what was checked, by whom, how"
cgv gate <libro> G4_SPECIALISTS SKIPPED --notes "no specialist question arose"
```

---

## G5_ARCHITECTURE — blocks first, then structure

Book-level architecture still runs first when the book is new:

`/estructura` in Cursor. Arquitecto runs in order:

**Step 0 — independent clauses.** A verdict before anything is named. `Bloqueado` stops the pass;
that is the gate working, not a failure.

**Step 1 — the block inventory.** Which markers open units; how they group; the count, **and
whether it came from the markers or from a decision**; the form of each unit named in the book's
own marker vocabulary; what each unit says; the clause IDs. Arquitecto proposes — you approve it
into `{NN.Curso}/blocks.md`. No agent writes that file.

```bash
cgvs/verify-blocks.py --blocks {NN.Curso}/blocks.md --lbf cgv-data/bibles/LBF/<libro>.lbf.md
```

**Then the structure** — H1/H2/H3, telos, title. Every boundary must be defensible from
`blocks.md`. A heading that cuts a block means one of the two is wrong; Arquitecto says which.

```bash
cgv gate <libro> G5_ARCHITECTURE PASS --notes "blocks approved; architecture rests on them"
```

### Hearing production — H2 loop (locked)

Once H2 spans exist, **student analysis is remapped one H2 at a time**. Model unit:
Apocalipsis 1:1–8. See `MANUAL_STANDARD.md` § *Production template*.

```text
clause map → Arquitecto hierarchy → your approval → Escriba remap → Apéndice D → audits
```

1. Complete / refresh `reports/clause-map-{span}.md` (`templates/clause-map.template.md`).
2. `/estructura` on that span — Arquitecto writes `architecture/{libro}-hierarchy-{span}.md`.
3. You approve (one sentence).
4. `/manual` — Escriba remaps **only that H2** onto the approved tree (leave `=` frozen).
5. Footnote definitions go under **Apéndice D** at end of file.
6. Audits for that span, then the next H2.

Do **not** Arquitecto-all-first. Do **not** mass-rewrite the book in one pass. Every finished H2
must look like `## Apocalipsis 1:1–8` in the working manual.

---

## G6_WRITING — context quotes, then Escriba

Once the H2 spans exist, generate the context quotes. **Scripture is never typed by an agent.**
The script packs whole LBF verses into `=` slides under ~280 characters (never splits a verse
across slides):

```bash
cgvs/build-context-quotes.py --manual {NN.Curso}/manual/manual.md \
                             --lbf cgv-data/bibles/LBF/<libro>.lbf.md --write
```

`manual/manual.md` is the **gate surface** when present (G6–G10, verify-g7/g8, PDF). Legacy
`{libro}-manual.md` / `{libro}-manual-editor.md` files are workshop inventory only — not the gate.

For hearing remaps, Escriba works on **`manual/manual.md`** only.
the **H2 loop** above — one approved hierarchy span per pass — not “one Compiler H3 with flechas.”
The book introduction must still name series with their counts. A student who finishes the
introduction and cannot say what the book is made of has been failed by it.

### Post-hearing commentary enrichment (when the gate surface is thin)

After the H2 hearing remap, compare `manual/manual.md` to the legacy editor draft
(`{libro}-manual-editor.md`). If commentary density collapsed (one `>` per H4 instead of
nested observations on `-` / `+` hangers — see `MANUAL_STANDARD.md` § *Commentary density*),
recover missing `>` lines **without** re-importing workshop `*` lines or stock connector glosses:

```bash
python3 scripts/merge-editor-comments.py \
  --manual {NN.Curso}/manual/manual.md \
  --editor {NN.Curso}/manual/{libro}-manual-editor.md

python3 scripts/cleanup-stock-comments.py \
  --manual {NN.Curso}/manual/manual.md
```

Or via Manager: `cgv enrich-comments <libro>` (merge + cleanup). Then
`python3 scripts/check-authority.py --before … --after … --agent escriba` must PASS.
Any change to the gate surface marks **G7/G8 STALE** — rerun `cgv verify-g7` and `cgv verify-g8`.

---

## G7_EDITORIAL — two roles, then mechanical PASS

`@editor` first — mechanical only. Then `@corrector` on the **gate surface**
(`manual/manual.md` when present). Agents do **not** mark the gate.

```bash
cgvs/check-authority.py --before <a>.md --after <b>.md --agent editor
cgv verify-g7 <libro>          # auto PASS/FAIL — no hand gate
```

### When verify-g7 FAILs → Corrector (required)

```bash
cgv correct-g7 <libro>         # mechanical Corrector on gate surface, then re-verify
# if still FAIL: @corrector for remaining CRITICAL (speakers), then:
cgv verify-g7 <libro>
```

Mechanical Corrector (`scripts/correct-g7-surface.py`) deletes Actores, stock
*El recuento* / *Esto es lo que hay que oír*, and known speaker-poison triples.
It does not invent prose. Agent Corrector owns the rest.

Witness: `contracts/SPEAKER_HEARING_CONTRACT.md` · `reports/SPEAKER_HEARING_REPORT.md`.
Do **not** `cgv gate … G7_EDITORIAL PASS`.

---

## G8_FINAL_VERIFY — mechanical stream (auto PASS/FAIL)

```bash
cgv verify-g8 <libro>
cgv provenance <libro>
```

`verify-g8` runs `verify-g8-final.py` (speaker `--gate g8`, manual checks, quotes, blocks) and
records **PASS or FAIL**. No hand PASS. Human sufficiency reading is **G9 only**.

`provenance` recomputes every declared input. Drift means something moved under you; `--apply`
marks the affected gates `STALE` and blocks what depends on them.

---

## G9_HUMAN_REVIEW · G10_RELEASE

Only after G7 and G8 mechanical PASS:

**Sufficiency reading:** can a student who reads only this manual say what happens in each block,
and what shape the book has? Scripts do not answer that — humans do, here.

```bash
cgvs/release-gate.py --manifest {NN.Curso}/release-manifest.json
cgv gate <libro> G9_HUMAN_REVIEW PASS --notes "reviewed by …"
```

Release requires every gate PASS, no blocker, no unresolved CRITICAL finding, and human approval
bound to the exact artifact revision and checksum. **The default is NOT RELEASED.** A requirement
that cannot be demonstrated counts as not met, never as absent.

---

## When something moves under you

Any time the LBF source, the alignment or the artifact might have changed:

```bash
cgv provenance <libro>            # evidence
cgv provenance <libro> --apply    # execute the invalidation
```

The old artifact is never evidence of the new state.

---

## Known gaps

| Gap | Effect |
|---|---|
| Compiler exports outside the course | One manual move per book, until the app changes |
| Verificador and Specialists have no agent | G3 and G4 are done by reading, recorded by hand |
| Symlink discovery unverified | If `@arquitecto` fails, fall back to copies |
| `revision` strings are labels, not git SHAs | Checksums are ground truth; revisions are human-readable only |
| Step 1, `blocks.md` and `=` quotes are untested | Apocalipsis is the first real exercise |
