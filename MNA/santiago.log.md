- # MNA — Santiago (Log)

  ## Session info
  - Date: 2026-05-27
  - Scope: observation-only (no interpretation / application)
  - Outputs tracked in this log:
  	- `MNA/datasets/finite-verbs/santiago.jsonl` (rebuilt)
  	- `MNA/datasets/movement/santiago.jsonl`

  ## Sources used
  - MorphGNT source (uploaded): `MNA/SOURCES/MorphGNT/santiago-morphgnt.txt`
  - Predicate anchors (uploaded): `MNA/datasets/predicate-anchors/santiago.jsonl`

  ## Dataset rebuild: finite verbs
  ### Problem
  The provided `finite-verbs/santiago.jsonl` was missing 3 token indexes required by predicate anchors:
  - Missing `token_index`: 997, 1010, 1420
  - Counts: anchors = 263, finite-verbs = 260

  ### Resolution
  Rebuilt `finite-verbs/santiago.jsonl` directly from `santiago-morphgnt.txt`.

  ### Parsing rules (MorphGNT)
  - Each token line format observed:
  	- `<ref> <pos> <morph> <surface> <norm> <something> <lemma>`
  	- Example verb line:
  		- `200102 V- 2AMD-P-- ἡγήσασθε, ἡγήσασθε ἡγήσασθε ἡγέομαι`
  - Token index (`token_index`) definition:
  	- 1-based running counter over *all* token lines in the MorphGNT file (excluding blank lines, headings like `ΙΑΚΩΒΟΥ`, and non-token lines).
  - Finite verb selection:
  	- `pos == "V-"` AND morphology (`morph`) begins with a person digit `1|2|3`.
  	- Non-finite verb forms where `morph` begins with `-` (e.g., `-PAN----`) are excluded.
  - Morphology encoding used in output:
  	- `morphology = "V-" + morph`
  - Chapter/verse:
  	- From `ref` formatted `CCVVVV` where:
  		- chapter = `ref[2:4]`
  		- verse = `ref[4:6]`
  - Person mapping:
  	- `1 → first`, `2 → second`, `3 → third`
  - Number mapping:
  	- `S → singular`, `P → plural`
  - Voice mapping:
  	- `A → active`, `M → middle`, `P → passive`
  - Mood mapping:
  	- Standard MorphGNT mood codes mapped:
  		- `I → indicative`
  		- `S → subjunctive`
  		- `O → optative`
  		- `M → imperative`
  		- `N → infinitive`
  		- `P → participle`
  	- Note: The original frozen dataset sometimes used `"D"` for imperative; the rebuilt dataset uses `"imperative"` from MorphGNT `M`.

  ### Rebuilt output summary
  - Output: `MNA/datasets/finite-verbs/santiago.jsonl`
  - Rows:
  	- metadata: 1
  	- finite_verb records: 263
  - Verification:
  	- All predicate-anchor token indexes were present in rebuilt finite-verbs.
  	- Specifically confirmed present: 997, 1010, 1420.

  ## Dataset build: movement
  ### Definition (as agreed)
  Movement = boundary markers only.
  - Enabled markers:
  	- mood boundary
  	- person/number boundary
  - Disabled/unsupported:
  	- connector-boundary labels
  	- purpose/reason/result labels
  	- topic-shift labels

  ### Construction rules
  For each predicate anchor (in anchor order):
  - Lookup the corresponding finite-verb row by `token_index`.
  - Store the finite verb’s:
  	- mood
  	- person
  	- number
  - Compute boundaries relative to the immediately previous anchor:
  	- `mood_boundary_before = (current.mood != previous.mood)`
  	- `person_number_boundary_before = (current.person != previous.person) OR (current.number != previous.number)`
  - First anchor:
  	- both boundary fields are `false`.

  ### Output summary
  - Output: `MNA/datasets/movement/santiago.jsonl`
  - Rows:
  	- metadata: 1
  	- movement_marker records: 263

  ## Notes / next dependencies
  - Subject dataset generation still depends on the agreed subject rules (predicate-only; derived from finite-verb morphology).
  - Manual writing (Spanish, Filemón format) depends on finalized datasets + movement boundary usage in structuring.

  ---

  ## Trunk work (manual preparation)

  ### Goal
  Produce a **trunk** (high-level structure) for Santiago and compare it against the trunk provided by the user.

  ### Constraint
  - Trunk decisions are **observation-only**.
  - Structural decisions are grounded in the **Greek text flow** (not the Spanish translation).

  ### Inputs used
  - Greek text source (uploaded): `santiago.md` (continuous Greek text by verse)
  - Predicate anchors (uploaded): `MNA/datasets/predicate-anchors/santiago.jsonl` (finite-verb anchor list)
  - User-provided trunk (pasted in chat): a predicate-oriented trunk built from Greek predicates/connectors.

  ### Method (how the AI trunk was derived)
  1) **Read the Greek text** as a continuous discourse (by chapter/verse) to identify major topical / rhetorical blocks.
  2) **Segmented into macro blocks** using visible transitions in the Greek (topic shifts, vocatives like ἀδελφοί μου, imperatives / prohibitions, and section changes such as:
  	- 1:19 shift to hearing/doing
  	- 2:1 shift to partiality
  	- 2:14 shift to faith/works argument
  	- 3:1 shift to teachers/tongue
  	- 3:13 shift to wisdom contrast
  	- 4:1 shift to conflicts/desires
  	- 5:1 shift to rich warning
  	- 5:7 shift to patience
  	- 5:13 shift to prayer)
  3) Produced a **macro-trunk** (coarse outline) consisting of the main blocks:
  	- 1:1
  	- 1:2–18
  	- 1:19–27
  	- 2:1–13
  	- 2:14–26
  	- 3:1–12
  	- 3:13–18
  	- 4:1–10
  	- 4:11–12
  	- 4:13–17
  	- 5:1–6
  	- 5:7–11
  	- 5:12
  	- 5:13–18
  	- 5:19–20
  4) Compared this macro-trunk against the user’s trunk by checking **coverage and order**:
  	- The user trunk is more granular (predicate-by-predicate) but follows the same **canonical sequence of Greek discourse blocks**.
  	- Result: the two trunks were judged **compatible and in agreement at the macro level**.

  ### Agreement summary
  - Agreement was established because:
  	1) The user trunk’s clause sequence (finite-verb predicates + connectors) covers the same macro sections in the same order.
  	2) No out-of-order blocks were detected.
  	3) No major macro block was missing from the user trunk (the only caution noted was that the pasted excerpt ended at 5:20, but this was treated as a likely truncation of the paste, not a structural disagreement).

  ### Notes
  - The AI trunk is a **macro-level trunk** for manual structuring.
  - The user trunk is a **predicate-anchor trunk**; it is consistent with the macro trunk and is suitable for fine-grained clause alignment.

  \---

  \## Trunk work (manual preparation)

- Let’s make H0 / H1 / H2 clear *as a method* (so you can reuse it), and at the same time produce a first-pass H0/H1/H2 for Santiago that we can refine. I’ll write this verbose on purpose so you can copy straight into documentation.

  ### 1) Definitions (what H0, H1, H2 are)

  #### H0 = Whole-book trunk (macro)

  H0 is the book’s top-level flow: the minimum set of large sections that explain how the discourse moves from start to finish.

  H0 answers: “What are the big movements of the document?”

  H0 is *not* phrase-by-phrase.

  H0 should be stable even if we later tweak details.

  Practical rule: H0 usually has 5–15 blocks.

  #### H1 = One level down (major sub-movements inside each H0 block)

  H1 subdivides each H0 block into the main subunits that a reader can track without getting lost.

  H1 answers: “Within this major section, what are the main steps?”

  H1 normally aligns to obvious shifts in Greek flow: vocatives, imperatives, contrasts, topic-change, new examples, etc.

  H1 is still “section-level”, not micro.

  Practical rule: each H0 block often has 2–6 H1 units.

  #### H2 = One level down from H1 (local steps / paragraph-like moves)

  H2 is the “working level” for your phrase-by-phrase observations.

  H2 answers: “What is the local step-by-step progression?”

  H2 often correlates to clusters of clauses/predicates, and sometimes matches “paragraphs” or “mini-arguments”.

  H2 is the level where your predicate-trunk (anchor-by-anchor) starts to become the primary guide.

  Practical rule: each H1 unit often has 2–10 H2 steps depending on density.

  ### 2) How we decide boundaries (Greek-based, observation-only)

  When deciding where to cut H0/H1/H2, we use observable markers, not interpretation.

  #### Boundary signals we are allowed to use

  1) Vocative / address (e.g., *ἀδελφοί μου*)
  2) Imperatives / prohibitions that reset the discourse (new command, new target)
  3) Explicit contrast markers (ἀλλά / δέ / οὖν / διό / πρὸ πάντων, etc.)
  4) New scenario/example (e.g., the poor/rich illustration; Abraham/Rahab)
  5) Genre shifts inside the letter (warning oracle, proverb-like instruction, prayer section)
  6) Your “movement markers” (mood/person-number boundaries) as *supporting evidence* for segmentation—especially useful for H2-level changes.

  #### What we avoid at this stage

  We do not label: “this is the theme”, “this is the meaning”, “this is application”.

  We do not create headings like “Justification by faith” (interpretive).

  We use neutral headings: “Warning”, “Contrast”, “Example”, “Instruction”, “Result”.

  ### 3) Documentation protocol (log every step)

  Here’s a simple “log template” you can paste under your documentation section each time we refine:

  Step X — Decision: (what we changed)  

  Evidence: (Greek boundary signals, connector cues, mood/person shifts)  

  Result: (updated H0/H1/H2 outline)  

  Notes: (what’s uncertain / what we’ll verify next)

  That’s the pattern we’ll follow.

  ### 4) First-pass H0 for Santiago (macro trunk)

  This matches what we already agreed at macro level:

  H0-A — 1:1 Opening / sender + recipients + greeting  

  H0-B — 1:2–18 Trials → wisdom → desire/temptation → gifts from above → new birth  

  H0-C — 1:19–27 Hearing/doing → speech/anger → “religion” description  

  H0-D — 2:1–13 Partiality / rich-poor scenario / “law” language  

  H0-E — 2:14–26 Faith/works argument + examples  

  H0-F — 3:1–12 Teachers + tongue (power/inconsistency)  

  H0-G — 3:13–18 Wisdom contrast (from above vs other)  

  H0-H — 4:1–10 Conflicts/desires → friendship with world → submit/humble  

  H0-I — 4:11–12 Speaking against/judging a brother → one lawgiver/judge  

  H0-J — 4:13–17 Presumption about tomorrow → accountability  

  H0-K — 5:1–6 Woe to rich oppressors  

  H0-L — 5:7–11 Patience until the Lord’s coming  

  H0-M — 5:12 Oaths (yes/no)  

  H0-N — 5:13–18 Prayer section (suffering/sick/confession/Elijah)  

  H0-O — 5:19–20 Closing: turning back / saving / covering

  Log Step 1 — Decision: Accept H0 macro trunk as baseline.  

  Evidence: Major observable discourse shifts already identified (2:1, 2:14, 3:1, 3:13, 4:1, 4:11, 4:13, 5:1, 5:7, 5:12, 5:13, 5:19).  

  Result: H0 = A–O above.  

  Notes: This is stable; we refine H1/H2 next.

  ### 5) First-pass H1 + H2 (focus on “especially” H1)

  You said “H0, H1 especially” — so I’ll lay out H1 clearly, and give a workable H2 skeleton beneath each H1. We can tighten later.

  #### H0-B (1:2–18) — H1/H2

  H1-B1 — 1:2–4 Trials → produce endurance → endurance → complete result  

  H2-B1a: command to “count it joy”  

  H2-B1b: knowledge: testing produces endurance  

  H2-B1c: endurance must have full effect → completeness / lack nothing

  H1-B2 — 1:5–8 Lack wisdom → ask → must ask in faith (contrast doubt)  

  H2-B2a: conditional: lack wisdom  

  H2-B2b: ask God who gives  

  H2-B2c: ask in faith, no doubting  

  H2-B2d: doubter described (sea wave) + “do not think he will receive” + double-minded instability

  H1-B3 — 1:9–11 Lowly/rich contrast (status reversal) + fading imagery  

  H2-B3a: lowly boast in exaltation  

  H2-B3b: rich boast in humiliation  

  H2-B3c: reason: grass/flower fading; sun rises/scorches/dries/falls/beauty perishes; rich fades in pursuits

  H1-B4 — 1:12 Beatitude: endurance under trial → approved → crown  

  H2-B4a: blessed one who endures  

  H2-B4b: after approval → receives crown

  H1-B5 — 1:13–15 Temptation source + desire conception → sin → death  

  H2-B5a: prohibition: “let no one say ‘from God I’m tempted’”  

  H2-B5b: God not tempted by evil; he tempts no one  

  H2-B5c: each tempted by own desire (dragged/enticed)  

  H2-B5d: desire conceives → gives birth to sin; sin finished → births death

  H1-B6 — 1:16–18 Do not be deceived + gifts from above + Father + new birth by word of truth  

  H2-B6a: “do not be deceived”  

  H2-B6b: every good gift/from above/from Father of lights/no variation  

  H2-B6c: by will he brought us forth by word of truth → firstfruits

  Log Step 2 — Decision: Define H1 for 1:2–18 as B1–B6.  

  Evidence: Clear shifts: (a) command/production chain (1:2–4), (b) wisdom asking + faith/doubt (1:5–8), (c) lowly/rich contrast imagery (1:9–11), (d) beatitude closure (1:12), (e) temptation/desire chain (1:13–15), (f) “do not be deceived” + gift/new birth (1:16–18).  

  Result: H1-B1..B6 + H2 skeleton above.  

  Notes: This is a good “spine” for phrase-by-phrase work.

  #### H0-C (1:19–27) — H1/H2

  H1-C1 — 1:19–20 hearing/speaking/anger + anger doesn’t work God’s righteousness  

  H2: “know this” → be quick to hear / slow to speak / slow to anger → reason: human anger doesn’t produce righteousness

  H1-C2 — 1:21 receive implanted word with meekness  

  H2: put away filth/overflow of evil → receive word → able to save souls

  H1-C3 — 1:22–25 doers not hearers only; mirror illustration; blessed doer  

  H2: command be doers  

  H2: hearer-only compared to mirror look/leave/forget  

  H2: doer who perseveres in perfect law → blessed

  H1-C4 — 1:26–27 tongue/religion + “pure religion” description  

  H2: if thinks religious but doesn’t bridle tongue → religion vain  

  H2: pure religion described (orphans/widows + keep unstained)

  #### H0-D (2:1–13) — H1/H2

  H1-D1 — 2:1 prohibition: faith with partiality  

  H1-D2 — 2:2–4 scenario: rich vs poor seating → “have you not made distinctions?”  

  H1-D3 — 2:5–7 appeal: God chose poor; you dishonored; rich oppress/blaspheme  

  H1-D4 — 2:8–13 “royal law” + transgression logic + mercy/judgment

  #### H0-E (2:14–26) — H1/H2

  H1-E1 — 2:14–17 claim of faith without works + needy example → dead  

  H1-E2 — 2:18–20 dialogue challenge + demons believe → empty person  

  H1-E3 — 2:21–24 Abraham example + scripture fulfilled  

  H1-E4 — 2:25–26 Rahab example + conclusion: faith without works dead

  #### H0-F (3:1–12) — H1/H2

  H1-F1 — 3:1–2 teachers warning + stumble in speech  

  H1-F2 — 3:3–6 small controls big (bits/rudders) + tongue/fire/world  

  H1-F3 — 3:7–8 taming animals vs tongue untamable  

  H1-F4 — 3:9–12 blessing/cursing inconsistency + fountain/tree images

  #### H0-G (3:13–18) — H1/H2

  H1-G1 — 3:13 show by good conduct  

  H1-G2 — 3:14–16 bitter jealousy/ambition → not from above  

  H1-G3 — 3:17–18 wisdom from above described + righteousness sown in peace

  #### H0-H (4:1–10) — H1/H2

  H1-H1 — 4:1–3 conflicts from pleasures + you ask wrongly  

  H1-H2 — 4:4–6 friendship with world + God gives greater grace  

  H1-H3 — 4:7–10 submit/resist/draw near/cleanse/humble

  #### H0-I (4:11–12) — H1/H2

  H1-I1 — 4:11–12 speak against/judge brother → one lawgiver/judge

  #### H0-J (4:13–17) — H1/H2

  H1-J1 — 4:13–15 planning speech vs “if the Lord wills”  

  H1-J2 — 4:16–17 boasting + sin of knowing good and not doing

  #### H0-K (5:1–6) — H1/H2

  H1-K1 — 5:1–3 rich weep; rot/corrode; hoarded  

  H1-K2 — 5:4 withheld wages cry out  

  H1-K3 — 5:5–6 luxury → fattened hearts → condemned/killed righteous

  #### H0-L (5:7–11) — H1/H2

  H1-L1 — 5:7–8 be patient; farmer image; strengthen hearts  

  H1-L2 — 5:9 do not groan; judge at doors  

  H1-L3 — 5:10–11 prophets + Job example + Lord compassionate

  #### H0-M (5:12) — H1/H2

  H1-M1 — 5:12 no oaths; yes/no

  #### H0-N (5:13–18) — H1/H2

  H1-N1 — 5:13 suffer/pray; cheerful/sing  

  H1-N2 — 5:14–15 sick → elders pray/anoint → Lord raises; sins forgiven  

  H1-N3 — 5:16 confess/pray; effective prayer  

  H1-N4 — 5:17–18 Elijah example

  #### H0-O (5:19–20) — H1/H2

  H1-O1 — 5:19–20 wander/turn back → “let them know” → save/cover

  ### 6) What we do next (to “make it clear” in your mind)

  Here’s the clean next sequence:

  #### Step 3 (Refinement): Confirm H1 boundaries using your trunk + movement markers

  For each H0 block, we will:

  list the key predicate anchors in order (your trunk),

  check where mood/person-number boundaries cluster,

  confirm whether the H1 cuts above are right or need adjustment.

  #### Step 4 (Lock): Freeze H0/H1/H2

  Once you say “yes, that’s the skeleton”, we freeze it and stop moving boundaries.

  #### Step 5: Phrase-by-phrase observations/comments

  Then we proceed with the manual content generation in the Filemón format.

  ### One question to choose the path (so we don’t wander)

  Do you want to refine H1/H2 starting with 1:2–18 (since that’s where we’re writing now), or do you want to do a full-book H1 pass first?

  Reply with:

  “Start with 1:2–18” or

  “Full-book H1 first”

  developmental-signal-system.md

  

  

  mna-renewed-direction.md

  

  i need you to see these files. Read them carefully.

  8:19 AM

  

  4 steps

  

  

  I read both files carefully.

  ### What changed (and what that means for our H0/H1/H2 work)

  #### 1) The core pivot

  Both documents say the same pivot in two ways:

  We are not trying to mechanically derive final structure from grammar.

  We are trying to expose and track observable developmental continuity.

  So: H0/H1/H2 are not “the structure generator output.”  

  They are a human-facing observation scaffold that should be built from *developmental signals*, with grammar/movement as supporting environment.

  #### 2) What stays valuable from our existing work

  Per *MNA Renewed Direction*, our existing datasets (anchors, movement, finite verbs, etc.) remain foundational, but only as:

  > “the exposed movement environment in which developmental continuity can be observed.”

  So movement/person-number/mood are *not* the structure—  

  they are *part of the evidence layer*.

  #### 3) The guardrail (non‑negotiable)

  Both files explicitly require we resist:

  abstract theorizing

  theology generation

  interpretive labels

  conceptual inflation

  And enforce this test:

  > “Can this be directly pointed to repeatedly in the text?”

  So when we write H0/H1/H2 headings, we must use non-interpretive, observable labels like:

  “unresolved contrast continues”

  “delayed closure”

  “re-entry / resumption”

  “escalation”

  “directional shift”

  rather than doctrinal/thematic headings.

  ### Updated method: how we should do H0/H1/H2 now (aligned to your two docs)

  #### Layer framing (matches your “Three Interacting Layers”)

  Layer 1 (Raw Data): anchors, connectors, movement, etc.

  Layer 2 (Exposition): we mark spans/overlays like “delayed closure” / “re-entry”

  Layer 3 (Training): questions/habits students use to observe it

  #### Practical implication

  H0/H1/H2 belong to Layer 2 (Exposition), not Layer 1.

  So from now on:

  H0 = the book’s major developmental continuities (what “pressure” continues)

  H1 = major developmental sub-movements inside each continuity (where pressure shifts / escalates / resumes / resolves)

  H2 = local continuity steps used to support phrase-by-phrase observation

  And we only accept a boundary if we can document it using:

  repeated patterns,

  delayed closure / resumption,

  recurring unresolved contrasts,

  escalation,

  directional shifts,

  resolution signals,

  sustained relational pressure,

  all *pointable* in the Greek flow.

  ### How this affects what you asked earlier (“develop H0/H1 especially”)

  We can still do H0/H1/H2, but we must re-describe them in your renewed vocabulary:

  Not “Section about X doctrine”

  But “Continuity of unresolved pressure X” + “how it escalates/resolves”

  ### Next step (so we proceed correctly)

  To proceed in the renewed direction, I need one decision from you:

  Do you want H0/H1/H2 for Santiago to be built primarily from these initial developmental signals first:

  1) unresolved contrast
  2) delayed closure
  3) re-entry / resumption

  (with escalation and directional shift later)

  —OR— do you want to include escalation + directional shift from the start?

  Reply with:

  “Start simple (3 signals)” or

  “Full system (include escalation/shift now)”

  Then we’ll rebuild the Santiago H0/H1 with that signal vocabulary and log each boundary decision step-by-step.

  

  

  

  

  

  Can you do this?  Let me correct you here: We are not trying to mechanically derive final structure from grammar. No we first arrive mechanically to see structure in conjunction with  exposing and tracking observable developmental continuity.  if we turn to full-on developmental continuity we loose the objectivity the grammar provides (finite verbs, etc etc).  However, if we ignore developmental continuity we will turn to thematic breaks or theological topics.  Developmental continuity gives us greater understanding into the text that allows us to see clearer the purpose of the author etc.

  8:33 AM

  

  

  Yes—I can do this, and your correction is important.

  Here’s the corrected, aligned framing in your terms:

  ### 1) The actual target (grammar + development together)

  We are not doing either extreme:

  Not grammar-only (which tends to become mechanical grouping that misses large-scale flow), and

  Not development-only (which can drift into subjectivity if it isn’t anchored to observable grammatical data).

  Instead, the workflow is:

  > Mechanical structure exposure (finite verbs / anchors / connectors / movement)

  > in conjunction with

  > observable developmental continuity tracking

  So grammar is not “the structure generator”, but it *is* the objectivity anchor and the exposed environment.

  ### 2) Why the mechanical layer must come first (your point)

  If we jump straight to “developmental continuity” without the mechanical scaffolding:

  boundaries can become “what feels like a new topic”

  or worse, theological/thematic segmentation

  and then we lose the discipline of “point to it repeatedly in the text”

  So the mechanical layer provides:

  stable anchor points (finite verbs / predicate anchors)

  continuity measurements (movement signals)

  traceable clause ordering (so we can’t hand-wave continuity)

  ### 3) Why developmental continuity must still be present

  If we ignore developmental continuity and rely on grammar alone:

  we may produce “units” that don’t explain *why* the discourse keeps carrying certain pressure forward

  we risk treating structure as merely local grammatical clustering

  and then we again drift into “topic headings” to compensate

  So developmental continuity provides:

  a disciplined way to describe what remains unresolved, resumes, escalates, closes

  and that’s what gives clearer sight of authorial purpose (without forcing theology)

  ### 4) The operational model (how we will do H0/H1/H2 from now on)

  #### Step A — Mechanical exposure (objective)

  We build/read:

  predicate anchors (finite-verb chain)

  connectors

  movement markers (mood/person-number boundaries)

  (subject later, where applicable)

  This gives us an objective map of “what is happening where”.

  #### Step B — Developmental signal overlay (still observable)

  On top of that map, we mark developmental behaviors:

  unresolved contrast

  delayed closure

  re-entry/resumption

  escalation

  directional shift

  resolution signals

  sustained relational pressure

  Key rule: each signal must be pointable in the anchored chain (not vibes).

  #### Step C — H0/H1/H2 are the exposition output

  H0: major developmental continuities across the whole letter (supported by the mechanical map)

  H1: major sub-movements where continuity shifts/escalates/resumes/closes

  H2: local steps aligned to the predicate chain (the working level for phrase-by-phrase observation)

  ### 5) Confirming I can execute this

  Yes: for Santiago we can proceed exactly this way:

  use the predicate-trunk + movement data as the mechanical spine,

  then overlay developmental signals to justify H0/H1/H2 boundaries,

  and log each boundary decision step-by-step so you can paste it into documentation.

  ### 6) One clarification question (to proceed cleanly)

  When we write H0/H1/H2 headings, do you want the headings to be:

  1) Neutral structural headings (e.g., “1:5–8 Pedir con fe vs dudar”), with the *developmental signals documented under the heading*, or
  2) Signal-explicit headings (e.g., “1:5–8 Contraste no resuelto: fe vs duda”), where the signal is in the heading itself?

  Pick 1 or 2 and I’ll start building the H0/H1/H2 for Santiago under this corrected method, logging every step.