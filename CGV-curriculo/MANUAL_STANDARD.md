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
| `####` | independent clause — **Scripture only** | nobody |
| `-` | dependent clause — **Scripture only** | nobody |
| `+` | phrase — **Scripture only** | Escriba may split; no word may be lost |
| `*` | mechanical / evidence (actors, grammar, Def/XRef) | nobody |
| `>` | writer commentary | Escriba · Corrector |
| `=` | **context quote** — the H2's whole passage, **Scripture only**, generated | nobody |

`-`, `+` and `=` are reserved for Scripture. A line such as `Actores principales: …` must start
with `*`. Every scriptural word appears exactly once across `####` / `-` / `+`.

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

- One `=` line per verse: `= **7** En el día veinticuatro del mes undécimo…`
- **Generated, never typed.** `scripts/build-context-quotes.py` emits it from the H2 span, and the
  same script in `--check` mode proves every line is byte-identical to LBF. Scripture never enters
  the manual through an agent's hands.
- No commentary, no `<u>`, no italics, no edits, no omissions. Nothing attaches to a `=` line.
- **Excluded from the once-only count above.** The context quote is a second presentation of the
  same text, not a second copy of it. The packaging checker must skip `=` lines when accounting for
  scriptural words, or it will read every manual as duplicated.
- Consecutive `=` lines are grouped into slides under the ~280-character budget. A long passage is
  many slides; that is expected, not a defect.
- The quote is the H2's whole span, however long. It is never shortened for pacing.

Indentation left→right is structural depth. A dependent nests under the clause it actually
depends on; a hanging participle or relative sits under its noun host with no blank line
between host and hanger.

### Clause structure

Structure is **observed, not imposed**. An anchor clause is an independent clause not
introduced by a subordinator — it is the structural controller, not the theological centre.
Coordinators (*y, pero, o, mas, sino*) join equals and do not subordinate; do not assume one
anchor per sentence.

A clause that opens with a subordinator is dependent however it was coded. A nominal clause —
where the source predicates without a verb and the target supplies one — is a real independent
clause and stands in the trunk exactly as a verbal one does.

### Commentary and `<u>`

- Each `>` paragraph carries **exactly one** short `<u>word</u>`.
- Never underline a heading, a `+`, a `-`, a `####`, or any Scripture. Never a long word.
- A `>` may be a developed paragraph; slides count `>` blocks, not sentences.
- Never leave an actor triple (`*X* → *Y* → *Z*`) unexplained.

### Slides

Blank line = new slide. About four lines per slide. Never blank after every line. **Never put
a line on the same slide that outdents from the line above** — an outdent starts a slide.

### Footnotes and identifiers

- Every `[^tag]` reference has a definition; every definition is referenced.
- One canonical tag set per book, applied in a single place. A tag renamed by hand is undone
  by the next regeneration — fix it at the emitter.
- Clause identifiers (`{chapter}:{verse}:{token}`) are protected data. An identifier that
  disappears between two versions is a defect regardless of how the text reads.

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
G7_EDITORIAL      Editor (mechanical) · Corrector (prose)
        ↓
G8_FINAL_VERIFY → G9_HUMAN_REVIEW → G10_RELEASE
```

Authoring a new book runs `G5_ARCHITECTURE` → `G6_WRITING` first, then the verification gates.
Repairing an existing manuscript runs the order above. The gates are the same either way.

After **every** agent modification, run the authority check against the previous version.

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
