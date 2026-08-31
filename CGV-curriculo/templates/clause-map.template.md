# Clause-map template (Arquitecto input)

Private control document. **Not** student content. Lives in `{NN.Curso}/reports/clause-map-{span}.md`
(or `.yaml` when tooling prefers).

## Purpose

Give Arquitecto a **complete clause inventory with relations** so literary hierarchy is built from
**governors and continuity of thought**, not from verse numbers. Required for every H2 remapped
under the **production template** (`MANUAL_STANDARD` § *Production template* — model: Apocalipsis
1:1–8).

Verse references locate clauses. They do **not** create movements, H3s, or indentation.

## Inventory row (required fields)

| Field | Purpose |
|---|---|
| `id` | Stable local id (`M1.01`, or book-local `c-1-1-01`) |
| `ref` | Location only (e.g. `1:1`) — not a structural boundary |
| `es` | Exact Spanish clause (LBF wording for that piece) |
| `el` | Exact Greek clause (named edition, e.g. Scrivener 1894) |
| `level` | `independent` \| `dependent` \| `embedded` |
| `governor` | `id` of governing clause, or `—` if independent root |
| `relation` | How it attaches: `relative` \| `purpose-inf` \| `object` \| `participle` \| `coordinate` \| `apposition` \| `source` \| `reason` \| `predicate` \| `dative-resume` \| … |
| `connector` | Surface connector if any (`ἣν`, `καί`, `γάρ`, `ἀπό`, …) or `—` |
| `declares` | One-line: what this clause says / does |
| `unexpressed` | Anything Spanish supplies that Greek lacks (copula, object pronoun, subject) — or `—` |
| `certainty` | `explicit` \| `grammatical` \| `inference` \| `uncertain` |
| `variant` | TR/LBF decision if any — or `—` |
| `participant` | Who/what occupies the clause (or `—` / `unresolved`) |
| `role` | `actor` \| `speaker` \| `experiencer` \| `recipient` \| `state-subject` \| `—` |
| `actor_basis` | `actor_explicit` \| `actor_implied_by_grammar` \| `referent_continued_by_context` \| `actor_unresolved` |
| `continuity` | `same` \| `transition` \| `new` \| `open` — vs prior principal clause |
| `discourse_order` | Integer reading order among mapped clauses (1, 2, 3…) |
| `action` | Main action / speech / state label (short) |
| `verb_tense` | Surface tense/aspect label if finite (`present`, `aorist`, `future`, `nominal`, …) or `—` |
| `temporal_relation` | Explicit time link to prior clause, or **`unspecified`** |
| `relation_to_previous` | Discourse/syntax vs prior principal: `same_referent_new_declaration`, `coordinate`, `new`, … |

## Participant continuity (HARD)

Three categories only — never confuse them with mechanical actor counts:

1. **Participant + action** — Dios dio; Juan testificó; todo ojo verá.
2. **Speaker + declaration** — El Señor dice: Yo soy.
3. **Subject + state / assignment** — El tiempo está cerca; a él la gloria.

Do not tally *que*, *gracia*, *el tiempo*, relatives, or connectors as actors. Student `>`
names a continuity transition only when it materially affects the hearing (e.g. 1:5–6 → 1:7
*viene*). Unresolved subjects stay open. Do not promote a plausible antecedent into an
explicit subject (`actor_basis` must stay honest).

## Discourse order ≠ event chronology (HARD)

Clause order = textual / syntactic / (often) actor continuity. It does **not** equal event
chronology. If `temporal_relation` is `unspecified`, Escriba must not invent timeline glue
(*después*, *luego*, *ahora hace…*, *a continuación ocurre…*, *todavía no ha sucedido…*).
Name textual sequence as textual sequence when needed (*la declaración siguiente*, *en la
lectura*, *a continuación en el texto*). See **MANUAL_STANDARD** § Discourse order.

1. Every non-root row names a **governor** by `id`.
2. Coordinate clauses share a discourse unit but do **not** subordinate; `relation: coordinate`
   and `governor` points to the prior peer or the shared head — state which in a note.
3. Participles and infinitives are `embedded` under their finite (or other) host.
4. **Never** invent a governor from a verse break.
5. Uncertain subjects stay `certainty: uncertain`; Arquitecto must not resolve them when naming.

## What Arquitecto receives / emits

**Input:** this inventory (+ continuous LBF for the span; + Scrivener/named Greek edition).

**Arquitecto emits** (architecture only — no `>`):

1. **Literary movements** — consecutive runs of independent roots + their dependents; named by
   movement, not by verse bucket. References locate the span after the cut is made.
2. **Principal declaration clusters** — which independents get `####` prominence; which stay
   nested only.
3. **Indent tree** — `####` / `-` / `+` nesting that mirrors `governor` edges.
4. **Dudas** — open attachments, uncertain subjects, verse numbers that a sentence crosses.

**Arquitecto does not:** write observations, invent subjects, merge variants, or treat chapter:verse
as a movement boundary.

## Downstream (after hierarchy approval)

1. Escriba remaps observations onto Arquitecto’s tree.
2. **Three layers:** outline = Spanish only; `>` = meaning + visible Greek + `[^…]`; footnote = morphology. Never bare ids; never Greek on headings.
3. Four audits: text · syntax · hearing · restraint.
