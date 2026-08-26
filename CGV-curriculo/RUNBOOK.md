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

---

## G6_WRITING — context quotes, then Escriba

Once the H2 spans exist, generate the context quotes. **Scripture is never typed by an agent:**

```bash
cgvs/build-context-quotes.py --manual {NN.Curso}/manual/<libro>-manual.md \
                             --lbf cgv-data/bibles/LBF/<libro>.lbf.md --write
```

`/manual` in Cursor — Escriba, **one H3 per pass**. It reads `blocks.md`, and the book introduction
must name the series with their counts. A student who finishes the introduction and cannot say what
the book is made of has been failed by it.

---

## G7_EDITORIAL — two roles, in order

`@editor` first — mechanical only: markers, indentation, heading shape, slides, footnotes. **It
never changes wording.** Then `@corrector` — prose, pacing, transitions, síntesis, Actores as
prose. `@corrector` is what `@editor` used to be.

```bash
cgvs/check-authority.py --before <a>.md --after <b>.md --agent editor
```

The diff is the verdict; the agent does not get to explain itself.

---

## G8_FINAL_VERIFY

```bash
cgvs/run-manual-checks.py     --manual … --lbf … --book <libro>
cgvs/build-context-quotes.py  --manual … --lbf … --check
cgvs/verify-blocks.py         --blocks … --lbf …
cgv provenance <libro>
```

`provenance` recomputes every declared input. Drift means something moved under you; `--apply`
marks the affected gates `STALE` and blocks what depends on them.

Then the sufficiency reading: **can a student who reads only this manual say what happens in each
block, and what shape the book has?** No script answers that.

---

## G9_HUMAN_REVIEW · G10_RELEASE

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
