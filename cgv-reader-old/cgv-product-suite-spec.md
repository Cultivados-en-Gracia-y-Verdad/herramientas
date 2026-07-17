# CGV Product Suite — Architecture & Design Spec

Consolidated from a design conversation covering the product shape, separate from the
linguistic-method specs already written for Observer's internals (`skeleton-telos-spec.md`,
`participle-layer-spec.md`, `participle-mega-views-spec.md`, `sequence-view-spec.md`,
`titus-audit-corrections.md`, `participle-data-and-view-fixes.md`,
`interlinear-view-spec.md`). This document is the map those specs live inside.

---

## The founding discipline, spanning every app in the suite

Pure textual observation — no interpretation, no outside sources, no application. This isn't
a feature of one app; it's the reason the suite is split into four apps instead of one. Each
app exists specifically to keep one job from quietly bleeding into another:
- Reader must never push toward producing anything, or personal encounter with the text
  starts happening with one eye on output.
- Observer must never let a note, a feeling, or a "looks right" visual judgment substitute
  for an actual grammatical answer.
- Compiler must never reach outside Scripture — no lexicons, no commentaries, no historical
  background. Everything it gathers is other Scripture, nothing else.
- Writer is the *only* place a human's own explanatory prose enters — and even there, it's
  built from structure the text itself gave up, not from material the person brought in.

Four apps, four verbs — **Reader, Observer, Compiler, Writer** — each doing exactly one job
and handing off to the next.

---

## 1. Reader — public, free, everyone's front door

**Purpose:** pure encounter with the text. Listening, watching, observing — "pickling in the
text," enjoyment of it, nothing more. This was the very first thing described for this
project ("nice reader, clean, allows subtle comments, nothing more") and every later addition
has to protect that, not compromise it.

**Contains:**
- Multiple Bible version selection.
- Margin notes, attached per verse — same as writing in a physical Bible's margin.
- Highlighting (near-term).
- Scribbling / drawing / freehand annotation (later — see technical approach below; this is
  the feature most likely to need native, not just web, capability).

**Explicitly does not contain:** any structural/observational machinery (no bricks, no
skeleton, no clause tools), and no path that nudges a reader toward producing content. Reader
matures by becoming a better and better place to just sit with the text — not by being pushed
toward output.

**Preferences (new, needed now):**
- **Bible version** — which translation(s) are loaded/available to switch between.
- **Language** — interface language, independent of Bible version (e.g. a Spanish-language
  interface reading an English translation should be possible).
- **Font** — typeface and size.

**Quality bar ("pristine"):** concrete levers, not vague polish —
- Typographic measure (line length) capped for reading comfort regardless of screen width.
- Fonts embedded/bundled with the app rather than relying on whatever's installed on the
  device — this alone closes most of the cross-browser/cross-device rendering gap.
- Polytonic Greek rendering (accents, breathing marks) tested explicitly against real Greek
  text in the candidate fonts, not assumed to work because Latin/Spanish text looks fine.
- Minimal UI chrome — restraint, whitespace, the page reading like paper rather than software.

---

## 2. Observer — downloadable upgrade, attached to Reader

**Purpose:** where structural observation actually happens. This is where every linguistic
spec already written lives: Bricks 1–4 (finite verbs, mood, participles), Clause Builder,
Q1/Q2/Q3 dependency review, Skeleton/Outline/Telos, the participle mega-views (Flow/Emphasis/
Cast), and the Sequence view (reason/solution/imperative/purpose/recipient).

**Interlinear is the center of Observer** — not tucked inside one brick's flow, but the base
view everything else in Observer is built on top of (see `interlinear-view-spec.md`).

**The self-assembling canvas (the key design idea from this session):** rather than separate
screens for "flat clause list" and "finished skeleton," Observer is conceived as **one
continuous view that reorganizes itself as it's worked.** A passage starts flat — every
clause in plain document order, undifferentiated. As each clause is answered through Q1/Q2/Q3,
the moment it's marked dependent, its row visually nests under its resolved parent, in place.
Nothing is a separate destination; watching the flat sequence resolve into structure *is* the
observation. Participle underlines, connective marks between root clauses, and sequence tags
(reason/solution/imperative/purpose/recipient) attach to rows once they've settled, as
further layers on the same standing view — not additional screens.

**Hard rule protecting that canvas:** clauses never move by drag-and-drop, ever, even as a
"quick fix." A clause only changes position by being re-answered through the actual
grammatical questions and getting a different result than before — the visual re-nesting is
a rendering of a new answer, never itself a way of deciding placement. "Looks wrong, so I
moved it" is never a valid interaction Observer permits.

**Notes import from Reader:** notes a student has written in Reader, attached to a verse,
can be pulled into Observer — but each one needs to be explicitly **confirmed or rejected**
by the student, not auto-imported. A margin note in Reader could be anything — a personal
reflection, a question, an application — and Observer's structure must never absorb something
that isn't genuinely an observation about the text. Confirming is the student affirming "yes,
this is actually textual observation." Rejected notes simply stay where they were, in Reader
— never deleted, never silently dropped.

---

## 3. Compiler — scripture-only gathering tool

**Purpose:** sits between Observer's structural output and Writer's prose. A "gathering"
tool, not an analysis or interpretation tool — it fetches and assembles, it doesn't argue or
explain. Currently in conception; the name itself signals the job (assembling scattered
material into something structured enough to hand off), matching the Reader/Observer/Writer
naming pattern of naming an action, not a content category.

**Scope, explicitly confirmed: Scripture only.** No lexicons, no commentaries, no historical/
cultural background material — that would be a real, deliberate step outside the founding
discipline, and it was explicitly ruled out. Everything Compiler gathers is more Scripture:
cross references, word/lemma usage elsewhere in the Bible, a book's own internal echoes (e.g.
Titus echoing or being echoed by Paul's other letters).

**Not part of Reader.** Deliberately kept separate — Compiler is a serious working tool for
gathering and investigating, not something bundled into the public reading app.

**Feeds into Writer**, which is the existing markdown editor — Writer's job is applying the
right formatting to whatever Compiler exports, not gathering material itself.

---

## 4. Writer — existing markdown editor (mostly unchanged)

Already exists. Its scope in this architecture: take structured input from Compiler
(ultimately drawing on Observer's skeleton/outline/telos/sequence data as raw material) and
format it into finished manual content (e.g. the Titus CGV manual). Deliberately **not**
reachable directly from Reader — there is no shortcut from "just reading" to "producing
manual content." Everything passes through Observer and Compiler first.

---

## Technical architecture: shared core + native shell

**Decision:** build a shared core codebase (web technologies) for Reader (and eventually
Observer), wrapped in a **native shell** (e.g. Capacitor or Tauri) for actual app-store
distribution on phone, tablet, and desktop — rather than either (a) a bare website, or (b)
fully separate native codebases per platform.

**Why not bare web/browser-based:** browsers differ in rendering, and — more importantly —
browser-based canvas/input handling is genuinely worse than native ink APIs (e.g. Apple's
PencilKit) for the planned scribbling/stylus feature: worse latency, no real pressure
sensitivity. Given how central the "just like a real Bible" feel is to Reader, this is a
real, not cosmetic, gap.

**Why not fully native per platform:** would give the highest possible quality ceiling
everywhere, but multiplies effort substantially (three-plus codebases to build and maintain)
for a project currently built through one person working with Claude Code. Considered and
explicitly set aside as too large a commitment at this stage.

**The middle path:** one shared core handles layout, reading, notes, highlighting,
navigation, and most of Observer's interface. The native shell provides real app-store
presence on each platform, and gives a clean seam to drop in a genuinely native ink/stylus
layer specifically for scribbling when that feature is built — without rewriting everything
else. This also allows staged delivery: ship the shared core first, add native-only
capability (like stylus ink) later without a rebuild.

**Cross-browser font consistency** is mostly solvable within this approach by bundling fonts
with the app rather than depending on whatever's installed on the device — this closes most
of the rendering-inconsistency gap that motivated moving away from "just a website" in the
first place, separate from the stylus-latency reason.

**On "navigator":** clarified to mean browser-based delivery generally (not a specific UI
navigation control) — the concern was about output/rendering quality and consistency across
browsers, addressed above by the shared-core-plus-native-shell approach and font bundling.

---

## Licensing

**GPL family (copyleft).** Consistent with "not to be sold" — anyone who modifies and
redistributes the suite must also keep their version open, rather than a permissive license
(MIT/Apache) that would allow a closed, commercial fork later. This applies across the whole
suite — Reader, Observer, Compiler, and Writer.

---

## Open / not yet decided

- Compiler's actual name (currently using "Compiler," settled this session, replacing the
  earlier placeholder "??" and a considered alternative, "Gatherer").
- Compiler's specific toolset — cross references and word/lemma usage are confirmed in
  scope; the full list of tools ("gathering information," "investigation," etc.) is still
  in conception and needs its own design pass once Observer's output stabilizes enough to
  feed it.
- Exact mechanism for how Observer's skeleton/outline/telos/sequence data gets structured for
  Compiler and, ultimately, Writer's formatting step.
- Highlighting and scribbling in Reader are confirmed as intended features but explicitly
  deferred — not part of the current build pass.
