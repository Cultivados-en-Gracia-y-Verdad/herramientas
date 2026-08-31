# CGV — Production Workflow

The objective production, verification, and release process for **every** CGV manual.

This document is universal. It never becomes book-specific. Anything true only of Daniel, or
only of 1 Juan, belongs in that book's spec — see [Scope boundary](#scope-boundary).

```
WORKFLOW.md              universal production standard  (this file)
    ↓
specs/{libro}.md         book-specific specification
manifests/{libro}.json   book-specific machine-readable contract
```

---

## 1. Purpose

To produce manuals whose correctness can be **demonstrated**, not asserted.

> **A CGV manual is not complete because an AI says it is complete. It is complete only when
> it satisfies the applicable specification and passes all required verification gates.**

This replaces the question "what do we think this agent should do?" with "what does the CGV
production standard authorize this agent to do?"

---

## 2. Universal principles

The non-negotiables live in `cgv_hermeneutical_constitution_draft.md` §1.2 and `WORKFLOW.md` §34.
They are not restated here.

### The two-witness rule

*Owned by this document.*

A script and a reading are two different witnesses. **Neither is the gate alone.** Run the
script for evidence, then read the surface. Report both. If they disagree, the verdict is
blocked. Never report a script PASS as a verdict.

This rule exists because a packaging gate once returned PASS on a skeleton whose hinge verse
was absent from every line of the manual. The script was not lying; its rules did not cover
the case. Every gate has an uncovered case.

---

## 3. Universal CGV structure

### Hierarchy

| Level | Role | Rule |
|---|---|---|
| `#` H1 | major development | an unbroken run of consecutive H2s |
| `##` H2 | continuous development | an unbroken run of consecutive H3s; top and small |
| `###` H3 | section context title | orientation only; never teaches |
| `####` H4 | **textual anchor** | the exact independent clause; Scripture only |

H1–H3 orient. They never teach, argue, or conclude. H1 and H2 spans must **tile the book** —
each ends the verse before the next begins; a gap or overlap means a verse is lost.

`#####` and `######` never appear in a CGV manual.

### Markers

| Marker | Content | Editable by |
|---|---|---|
| `####` | independent clause / principal declaration — **Spanish Scripture only** | nobody alters Scripture words |
| `-` | dependent clause — **Spanish Scripture only** | nobody alters Scripture words |
| `+` | phrase — **Spanish Scripture only** | Escriba may split; no word may be lost |
| `*` | mechanical / evidence (actors, grammar, Def/XRef, clause type) | nobody |
| `>` | writer commentary (meaning + visible Greek + `[^…]`) | Escriba · Corrector |
| `=` | **context quote** — the H2's whole passage, **Scripture only**, generated | nobody |

`-`, `+` and `=` carry **Spanish Scripture**. Never put actors, tono, grammar labels, clause-type
notes, Greek forms, or Writer prose on `-` or `+`. A line such as `Actores principales: …` or
`Cláusula nominal…` must start with `*`.

### Three technical layers (HARD)

| Layer | Content | Never |
|---|---|---|
| **Heading / outline** (`####` / `-` / `+`) | Spanish clause only | Greek forms; `[^…]`; bare ids |
| **Observation** (`>`) | Meaning + visible Greek beside the Spanish expression | Morphology dump; bare id strings |
| **Footnote** (`[^id]:`) | Form → lemma → morphology → syntax → relevance | — |

```markdown
#### *Revelación de Jesús Cristo*

> El libro comienza nombrándose: *Revelación de Jesús Cristo* (Ἀποκάλυψις Ἰησοῦ Χριστοῦ)[^ap-1-1-apokalypsis].
```

Footnote *definitions* live under `# Apéndices` → **Apéndice D** (end of file), not after the H2.

**Identifiers** appear only as `[^ap-1-1-apokalypsis]` — never as visible noise `ap-1-1-apokalypsis`.
Every scriptural Spanish word appears exactly once across `####` / `-` / `+`.

### Scope of the marker contract

**The marker rules above govern the student body.** They stop at the first generated workshop
section:

```
## Actores · ## Movimiento · ## Convergencia · ## Tensión · ## Apéndice · # Apéndices
```

Those sections are Compiler-generated workshop material. They legitimately carry `####` headings
that are actor names rather than clauses, and `-` lines that are evidence rather than dependent
clauses. Auditing them against the student-surface contract produces noise, not findings — on
Apocalipsis it produced 461 reports of "Scripture without italics", every one an actor name in the
`## Actores` index.

Every checker must cut at the same boundary. `verify-skeleton-h4-packaging.py` and
`run-manual-checks.py` share the list; a third checker that does not will disagree with both for a
reason that has nothing to do with the manuscript. **Report what was skipped** — a count of
appendix `####` lines — so nothing is hidden rather than merely unaudited.

### The context quote (`=`)

Every `##` H2 opens with its **whole passage**, verbatim from LBF, before any analysis. The reader
meets the unit entire before it is taken apart — the plainest possible answer to the final test in
§4.

- **Whole verses, packed under ~280 characters.** Consecutive verses share a slide while the
  line stays under the budget; the next verse starts a new slide. A verse is never cut in half.
  (A single verse longer than ~280 stands alone on its slide.)
- **Scripture italics.** Same as `####` / `-` / `+`: verse body in `*…*`; verse labels stay bold
  (`= **7** *En el día…*`). Presenter renders `=` as scripture font/style.
- **Generated, never typed.** `scripts/build-context-quotes.py` emits it from the H2 span, and the
  same script in `--check` mode proves the reconstructed quote matches LBF. Scripture never enters
  the manual through an agent's hands.
- No commentary, no `<u>`, no edits, no omissions. Nothing attaches to a `=` line.
- **Excluded from the once-only count above.** The context quote is a second presentation of the
  same text, not a second copy of it. The packaging checker must skip `=` lines when accounting for
  scriptural words, or it will read every manual as duplicated.
- Blank line between `=` slides. A long passage is many slides; that is expected, not a defect.
- The quote is the H2's whole span, however long. It is never shortened for pacing. It sits
  **directly under the H2**, never mid-analysis.

Indentation left→right is structural depth. A dependent nests under the clause it actually
depends on; a hanging participle or relative sits under its noun host with no blank line
between host and hanger.

### Clause structure

Structure is **observed, not imposed**. An anchor clause is an independent clause not
introduced by a subordinator — it is the structural controller, not the theological centre.
Coordinators (*y, pero, o, mas, sino*) join equals and do not subordinate; do not assume one
anchor per sentence.

A clause that opens with a subordinator is dependent however it was coded. A nominal clause —
where the source predicates without a verb — is a real independent clause and stands in the trunk
exactly as a verbal one does.

**Marking a nominal clause.** Body: one short mechanical line — `* Cláusula nominal[^nom].` —
never a mini-lesson, never on `-` / `+`. Definition once in **Apéndice C** (`[^nom]`). Do not
restate «no presenta verbo expreso» on every occurrence: students tune out, and the slide is
stolen from the clause itself.

**Length.** An H4 is one presentable independent clause, not a paragraph of coordinated claims.
`verify-skeleton-h4-packaging.py` fails any H4 over **180 characters** (warns from 160): those
almost always need re-cutting in Observer / Compiler before Arquitecto names.

**Brick 1B / epistolary greetings.** One verbless independent may still carry long ἀπό / source
phrases in its span. Compiler peels H4 to the **actor core** (subject ± object) and emits the
remainder as `+` lines. Actors must mark that core in Observer — empty actors leave the mega-H4.
The packaging length gate still catches what peel cannot fix.

### Commentary and `<u>`

- Each `>` paragraph carries **exactly one** short `<u>word</u>`.
- Never underline a heading, a `+`, a `-`, a `####`, or any Scripture. Never a long word.
- A `>` may be a developed paragraph; slides count `>` blocks, not sentences.
- Never leave an actor triple (`*X* → *Y* → *Z*`) unexplained.

### Slides

Blank line = new slide. About four lines per slide. Never blank after every line. **Never put
a line on the same slide that outdents from the line above** — an outdent starts a slide.

### Footnotes and identifiers

- Every `[^tag]` reference has a definition; every definition is referenced. Bare ids
  (`ap-1-1-hen` or `(ἣν)ap-1-1-hen`) are a defect — always `(ἣν)[^ap-1-1-hen]`.
  Never put `[^…]` on a heading or outline Scripture line.
- **Presenter:** may not paint the raw id string into the slide. Markdown keeps
  `[^ap-1-1-hen]`; the visible surface is Greek + a marker (e.g. †), with the note in the popup.
- **Emphasis:** `***dio***:` is valid; `***dio*****: ` (five asterisks) is FAIL. Never wrap
  `*word*` in an outer `**…**`.
- Technical footnote order (stable): **form → lemma → morphology → syntactic function →
  relevance → variant only if needed.** Include only what demonstrates the observation.
- Passage-stable ids (`[^ap-1-1-deixai]`). Name the Greek edition in the note (for Apocalipsis:
  **Scrivener 1894**). Never reconstruct Greek from Spanish alone.
- Generic appendix tags (`[^P]`, `[^I]`, `[^kai]`, `[^nom]`) remain for book-wide form
  definitions; passage technical evidence uses passage-stable ids.
- **Placement (HARD):** all footnote *definitions* live under `# Apéndices` at the end of the
  student manual (A–C generic; **Apéndice D — Notas técnicas por pasaje** for
  `[^ap-…]` / passage-stable ids). Body keeps only the `[^…]` citations. Never dump definition
  blocks after an H2 / En síntesis mid-file.
- Clause identifiers (`{chapter}:{verse}:{token}`) are protected data. An identifier that
  disappears between two versions is a defect regardless of how the text reads.

## Participant continuity (internal audit — HARD)

Preserve **who speaks or acts** through syntax and narrative progression — not by mechanical
actor tallies. Never count relative pronouns, connectors, greetings, or states as “actors.”

### Three categories (keep distinct)

| Category | What it is | Example |
|---|---|---|
| **Participant + action** | Someone does something | Dios dio; Juan dio testimonio; todo ojo verá |
| **Speaker + declaration** | Someone speaks a claim | El Señor dice: Yo soy |
| **Subject + state / assignment** | State or nominal assignment, not an action narrative | El tiempo está cerca; a él la gloria y el poder |

Not every grammatical subject is an actor. Not every clause narrates an action.

### Forbidden restorations

Do not revive counting that confuses: grammatical subject · narrative actor · speaker ·
recipient · relative pronoun · nominal predicate. Words such as *que*, *estos*, *gracia* or
*el tiempo* must not be tallied as actors.

### Internal audit (per independent / principal clause)

Record privately (clause map or architecture notes — not usually student content):

| Field | Question |
|---|---|
| Participant | Who or what occupies the clause? |
| Role | Actor, speaker, experiencer, recipient, or subject of a state? |
| Actor basis | `actor_explicit` \| `actor_implied_by_grammar` \| `referent_continued_by_context` \| `actor_unresolved` |
| Main verb | What action, speech, or state is expressed? |
| Object/reach | What does the action reach? |
| Continuity | Same participant as before, or a transition? |
| Certainty | Explicit, implied, or unresolved? |
| `temporal_relation` | Explicit time link to prior clause, or `unspecified`? |
| `relation_to_previous` | Syntactic / discourse link (coordinate, same_referent_new_declaration, …) |

Only transitions that materially affect the flow appear in the student `>`. When the text does
not identify the participant, the manual preserves that openness. Do not promote a plausible
antecedent into an explicit subject on the page.

**Guiding rule:** Every principal clause must let us hear who speaks or acts, what is said or
done, and whether the participant continues or changes.

## Discourse order ≠ event chronology (HARD)

Four layers — keep them separate:

| Layer | Question | Normally available from clause order? |
|---|---|---|
| **Textual order** | What does the text say first, next, and last? | Yes |
| **Syntactic relation** | Which clause depends on or coordinates with which? | Yes |
| **Actor continuity** | Does the same participant remain in view? | Often |
| **Event chronology** | When do the described events occur? | **Only** with explicit temporal wording or warranted grammar |

Clause order establishes **discourse order**, not necessarily event chronology.

**Forbidden in `>` unless the text (or warranted morphology) establishes the time link:**
*después*, *luego*, *ahora*, *a continuación*, *antes*, *todavía*, *aún* used as **event**
timeline glue (*ahora hace…*, *a continuación ocurre…*, *todavía no ha sucedido…*,
*primero hizo X; después hará Y*).

**Allowed when naming textual sequence** (and only when the comment adds something):
*la declaración siguiente*, *el texto pasa de… a…*, *en la lectura*, *a continuación en el
texto*, *primero se oye…; después, en el texto…*.

| Risky | Safe |
|---|---|
| Después viene con las nubes | La declaración siguiente anuncia: viene con las nubes |
| Ahora hace otra cosa | El texto pasa a otra acción |
| A continuación las tribus se lamentan | La cláusula siguiente dice que las tribus se lamentarán |
| Todavía no ha ocurrido | El acontecimiento todavía no ha sido narrado |
| Primero amó; luego viene | Primero se recuerda que amó; después, en el texto, se anuncia que viene |

If the clause map marks `temporal_relation: unspecified`, the prose generator **must not** invent
*then*, *next in time*, or *afterward*. Preserve the order of the words without converting that
order into a timeline.

**Pre-scale audit (each H2):** search the span for *a continuación*, *después*, *luego*, *ahora*,
*primero*, *antes*, *todavía*, *aún*, *lo que sigue*, *pasa a* — classify each hit as
explicit textual time · textual/discourse sequence · unsupported event chronology.

## Production template (HARD)

**Model unit:** Apocalipsis 1:1–8 in `curriculo/23.Apocalipsis/manual/manual.md`.
Every later H2 in that book — and every CGV hearing manual built this way — must come out in
**the same student shape**. This is no longer provisional.

### What the student H2 looks like

1. `##` title (movement name).
2. Continuous LBF `=` for the whole span (frozen; never rearranged).
3. Analysis outline: Spanish-only `####` / `-` / `+` nested by governor edges (no Greek, no `[^…]`
   on outline lines).
4. `>` observations: meaning + visible Greek + `[^…]` citation; no flechas; no actor tallies;
   discourse order ≠ event chronology; unresolved subjects stay open.
5. `### En síntesis` when the H2’s movements are done.
6. Passage footnote *definitions* only in **Apéndice D** at end of file.

### H2 production loop (do not skip stages)

| Stage | Owner | Artifact |
|---|---|---|
| 1. Complete clause inventory | human / Escriba prep | `reports/clause-map-{span}.md` (`templates/clause-map.template.md`) |
| 2. Literary hierarchy from edges | **Arquitecto** | `architecture/{libro}-hierarchy-{span}.md` |
| 3. Human approval of hierarchy | human | — |
| 4. Remap observations onto that tree | Escriba | working `manual/manual.md` analysis for the span |
| 5. Technical footnotes | Escriba | `[^…]` defs under Apéndice D |
| 6. Four audits | Escriba + Editor | text · syntax · hearing · restraint |

**Work one H2 at a time** through this loop. Do not Arquitecto-all-first. Do not mass-rewrite the
book in one pass. Do not hand-author student hierarchy for a span Arquitecto has not cut from
the clause map.

**Verse numbers locate; they do not structure.** Arquitecto cuts movements from `governor` /
`relation` continuity, then attaches locating references.

**Two numbering systems — never mix them:**

| System | Form | Where |
|---|---|---|
| Movements (`###`) | `2:10a`, `2:10b` | Student headings when one verse holds two (or more) literary movements. Letters **a, b, c** are editorial locators, not biblical numbering. |
| Clauses / technical refs | `2:10:1`, `2:10:6` | Clause maps, Compiler token locators, evidence lines, footnote *definitions* that need a word index. |

Do **not** title a movement `Apocalipsis 2:10 (primera parte)` or `Apocalipsis 2:10:2`. Do **not** label a clause `2:10a`. Do **not** add a student gloss explaining what `a`/`b`/`c` mean — the headings are enough.

**Hearing layer** (continuous LBF `=`) stays frozen through all stages: never rearrange words,
silently complete a subject, combine variants, or replace the continuous reading.

**Certainty** on the map binds commentary: explicit / grammatical / inference (mark or omit) /
uncertain (neutral + footnote; never resolve in the body).

**Reference artifacts for the model unit:** `reports/clause-map-1-1-8.md` ·
`architecture/apocalipsis-hierarchy-1-1-8.md` · student unit under
`## Apocalipsis 1:1–8` in `manual/manual.md`.

### Commentary density (HARD)

The hearing remap is **not** “one summary `>` per H4.” The locked model (1:1–8) averages
**~3–4 `>` blocks per H4** in analysis spans, with nested observations on `-` / `+` hangers
when the outline nests them.

| Signal | Thin (fail) | Target (pass) |
|---|---|---|
| Comments per H4 (body spans) | ~1.0, summary only | ~3–4, like 1:1–8 |
| Nested hangers | `-` lines with no `>` | Movement, grammar, cross-refs on hangers |
| H4 with zero comments | any | none |

**Gate surface:** `manual/manual.md` when present. Legacy `{libro}-manual-editor.md` is an
**inventory** for recovering missing `>` (see `RUNBOOK.md` § *Post-hearing commentary enrichment*);
never PDF-export the legacy file by mistake.

**Banned in `>` (stock connector glosses — teach once, then name what is new):**

- `Ese <u>…</u> no abre otro/otra …`
- `No suma otro/otra …`
- `Este <u>que</u> no abre otro …`
- `No cuelga suelto` / `No queda suelto` / `Eso decían`
- `…, todavía no` / `Qué, abajo` / `Lo alcanzado:` as filler

Use `scripts/cleanup-stock-comments.py` after a bulk merge from the editor draft.

### Protected content

Never altered by any agent, in any mode:

- Scripture text and references
- source-language text, morphology, glosses
- clause identifiers and spans
- `*` mechanical/evidence lines
- footnote definitions

Problems in protected content are **flagged upstream to Observer/Compiler**, never repaired in
the manuscript. Repairing a symptom in place hides the defect and it regenerates.

---

## 4. Content standard

A CGV manual **guides the reader through the text**, phrase by phrase. Explanation always
follows the text; it never precedes it.

Forbidden in commentary: interpretation, application, theological teaching, imported
conclusions from later in the book, invented questions, fabricated telos, workshop hypotheses
presented as headings.

Ask of every line: **would the original reader know this yet, here?**

**The final test:** does the reader meet the words of the text first, or your words about the
text? If the answer is unclear, the passage needs correction.

### Evaluative observation — the attribution test

Irony, hypocrisy, sarcasm, self-interest, false confidence, misplaced grief. These are the most
valuable observations a manual can carry and the most dangerous, because they are judgments about
people's hearts and they are the usual door through which moralizing enters.

**An evaluative observation may be written only when the text itself makes the evaluation.** One of
two things must be true, and the note must show which:

1. **Someone in the text says it.** Quote them, with the reference. In Zacarías 7:5 Jehová asks
   *¿de ayunar me ayunaron a mí, yo?* and in 7:6 *¿no son ustedes los que comen y ustedes los que
   beben?* The gap between fasting-for-him and eating-for-themselves is not the reader's inference.
   It is the question the text poses.
2. **The author builds the collision structurally** — two statements set side by side, a stated
   motive answered by a contrary one, one term repeated in incompatible senses. Name **both halves
   and where each one is**. If you cannot point at both, you are supplying one of them.

If neither holds, the observation is the reader's judgment about other people's motives. It does
not go in the manual. It goes in the report as a finding, for the stage that owns it.

**Further constraints, all of them hard:**

- **Name the collision, never the motive.** *El texto pregunta si el ayuno fue para él* — not
  *ayunaban por egoísmo*. The first is what the page says; the second is what you concluded.
- **Do not name the tone.** *Irónico*, *sarcástico*, *hipócrita* are classifications, and a
  classification the text does not use is category compression (Constitution §5.4). Show the move
  instead: *el texto pregunta*, *la respuesta no responde a la pregunta*, *el mismo verbo vuelve
  con otro sujeto*.
- **Assign no interior state** the text does not assign.
- **Never let the note flatter the reader.** A line whose effect is *we see through these people*
  has stopped observing and started preaching. The reader is not the exception in the passage.
- **If the book resolves it, point forward to where; if not, leave it open** (Constitution §5.2).
  In Zacarías the self-directed lament of 7:5 returns in 12:10–12 as lament directed *a mí, a quien
  traspasaron* — the book closes its own thread, and the note follows the book rather than
  anticipating it.

This is what the `Tensión` thread convention is for. An evaluative observation is a tension the
text itself names, and it is carried the same way: name the two terms that collide, say where they
are, do not reconcile them, do not propose what the author meant, do not advance the application.

Language: Latin American Spanish, around 8th grade — never dumbed down, never cut for brevity.

---

## 5. Roles and authority

Each agent has a job description **and a clearance**. Authority is enforced mechanically by
`scripts/check-authority.py`, which diffs before/after and fails any change outside clearance.
**The agent does not get to explain itself.** The diff is the verdict.

| Agent | Can | Cannot |
|---|---|---|
| **Arquitecto** | telos, H1/H2/H3 naming, architecture | verify its own claims; alter technical source data |
| **Escriba** | write prose, split `+`, refine `###` | verify its own historical/theological claims; touch `####` or `-` |
| **Editor** | whitespace, markdown corruption, structural damage, marker violations, footnote integrity | change wording; add facts; change Scripture |
| **Corrector** | `>` prose, pacing, transitions, `### En síntesis` wording, `Actores principales` → prose, stock-closer removal | add facts or analysis; lexical, historical or theological claims; resolve a tension the text leaves open; touch protected content |
| **Verificador** | identify problems | rewrite anything; approve anything |
| **Specialists** | adjudicate within one domain | rewrite; adjudicate outside their domain |
| **Human** | everything | — |

This prevents the helpful-AI failure: an agent deciding to improve something it was not
authorized to touch.

---

## 6. Model tiering

Assign tier by the **risk and type of judgment** an agent may make — never by how hard its job
sounds.

> **Editor is allowed to be stupid. Verificador is not allowed to be trusting.**

The tiers themselves are defined in [`config/models.yaml`](config/models.yaml) and are not listed
here — a table in prose and a config file diverge, and then two documents disagree about which
model ran.

A small model must **detect and route**, never adjudicate. "I cannot confirm this" is the correct
output when the data does not settle it. Guessing to appear decisive is the failure.

---

## 7. Report protocol

Agents communicate through **short reports**, never by rewriting each other's work.

```
reports/{libro}/
  PYTHON_REPORT.md   EDITOR_REPORT.md   TEXTO_REPORT.md   ESTRUCTURA_REPORT.md
  VERIFIER_REPORT.md HEBREW_REPORT.md   HISTORY_REPORT.md OBSERVATION_REPORT.md
  ARQUITECTO_REPORT.md   RELEASE_CHECK.md
```

Rules:

- A downstream agent reads the **reports**, not the manuscript.
- Only the cheapest agent reads the whole file. Specialists receive a **ref list** and load
  only those passages. If handed a whole book when the input should be a ref list, ask for it.
- Every finding **quotes text and gives a reference**. A finding with no quote is not a
  finding.
- Zero findings is a claim and needs its own evidence: say what was checked and how.

---

## 8. Verification gates

Gate IDs, statuses and progression are defined in [`STATE_MODEL.md`](STATE_MODEL.md) §5–§9 and are
not restated here. This section defines only what happens *inside* a gate when the object is a
manuscript.

```text
G2_MECHANICAL     Python deterministic checks → Editor (mechanical anomalies)
        ↓
G3_TEXTUAL        Verificador — triage, challenge claims
        ↓
G4_SPECIALISTS    textual · languages · historical · observation
        ↓
G5_ARCHITECTURE   Arquitecto — architecture, telos
        ↓
G6_WRITING        Escriba — prose repair
        ↓
G7_EDITORIAL      Editor · Corrector · **mechanical speaker/hearing verify**
        ↓
G8_FINAL_VERIFY   mechanical stream (speaker g8 + quotes + blocks + checks)
        ↓
G9_HUMAN_REVIEW → G10_RELEASE
```

Authoring a new book runs `G5_ARCHITECTURE` → `G6_WRITING` first, then the verification gates.
Repairing an existing manuscript runs the order above. The gates are the same either way.

After **every** agent modification, run the authority check against the previous version.

### Hearing the book (HARD) — G6 craft · G7/G8 mechanical

A manuscript may be wooden during Escriba drafting. **G7 and G8 do not PASS on agent prose.**

**G6 (Escriba) craft fail when** (agent judgment while writing):

- student `>` is mostly flecha lessons (*primer slot*, *lo alcanzado*, *la flecha se detiene*);
- reception is certified by the editor (*Esto es lo que hay que oír*);
- most units end with stock *todavía no* / *El recuento…* as filler;
- inferred speakers are presented as grammar facts against speakers named on the page.

**G7_EDITORIAL PASS** is recorded only by:

```bash
cgv verify-g7 {libro}
```

**On G7 FAIL** (required, not optional):

```bash
cgv correct-g7 {libro}    # mechanical Corrector → re-verify
# still FAIL → @corrector for remaining CRITICAL, then cgv verify-g7 again
```

**G8_FINAL_VERIFY PASS** is recorded only by:

```bash
cgv verify-g8 {libro}
```

Do not hand-set those gates. Contract: [`contracts/SPEAKER_HEARING_CONTRACT.md`](contracts/SPEAKER_HEARING_CONTRACT.md).
Human sufficiency reading is **G9 only** — after that stream, not instead of it.

Full craft rules live in the Escriba and Corrector skills (`Hear the book first`).

---

## 9. Release

Release eligibility is computed from state — [`STATE_MODEL.md`](STATE_MODEL.md) §25 — and the
definition of done is [`WORKFLOW.md`](WORKFLOW.md) §33. Neither is restated here.

`scripts/release-gate.py` evaluates the manuscript against its manifest and reports what it can
prove.

**The default is NOT RELEASED.** The manuscript earns it; it is never presumed to have it. A
requirement that cannot be demonstrated counts as **not met** — never as absent. A gate that cannot
prove something reports it unproven.

---

## Scope boundary

**This file never becomes book-specific.**

| Belongs here | Belongs in `specs/{libro}.md` |
|---|---|
| marker meanings, hierarchy, authority | which source texts and spines the book uses |
| the two-witness rule, release definition | language switches, chapter ranges |
| report protocol, model tiering | structural and architectural decisions taken |
| content standard | terminology, known debt, per-book gotchas |

If a rule mentions a book name, it is in the wrong file.
