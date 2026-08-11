> **Status: SUPERSEDED**
>
> This document describes an earlier prototype translation pipeline.
> It is retained for historical reference.
>
> The canonical cgv-translator production workflow is defined in:
>
> `../WORKFLOW.md`

---

# Translation Pipeline v0.1

## Purpose

The Translation Pipeline defines how CGV Translator produces **La Biblia Fiel (LBF)** Spanish phrase by phrase.

The pipeline exists to ensure that every rendering is accountable to the biblical text — not to tradition, memory, theology, or an earlier Spanish translation.

AI may assist the pipeline, but AI does not replace the pipeline.

The human translator remains responsible for every approved phrase.

---

## Primary Goal

Faithful Spanish that is:

- simple
- precise
- contemporary
- accountable to lemma, morphology, and context

RV1909 is an excellent Spanish reference, but it is **not** the initiating authority.

---

## Foundational Principle

> **Let Scripture speak for itself.**

The Greek or Hebrew text initiates every phrase.

The translator follows the text.

The text never follows the translator.

This principle governs every gate below.

---

## Relationship to Other Specs

| Spec | Role |
|------|------|
| `CONSTITUTION.md` | Governing principles |
| `investigation-view-v0.1.md` | Lemma policy workflow when Gate 1 blocks |
| `cgv-data-contract-v0.1.md` | Occurrence and morphology data |
| `storage-v0.1.md` | File-based persistence |
| `Biblia-LBF/README.md` | Translation operating rules |

The Investigation View handles **lemma policy creation**.

The Translation Pipeline handles **phrase rendering**.

---

## Unit of Work

The unit of translation work is one **phrase**.

A phrase is a bounded span of source tokens within a verse, defined by the project phrase map.

Example:

```text
Titus 1:1 · Phrase 1
Greek:  Παῦλος δοῦλος θεοῦ
Tokens: n56001001001, n56001001002, n56001001003
```

Every phrase passes through the same five gates in the same order.

---

## The Five Gates

Gates run in strict order.

A later gate may clarify meaning.

A later gate may **not** override an earlier gate.

| Gate | Name | Question | Authority |
|------|------|----------|-----------|
| 1 | Lemma | What does each word mean? | CGV Dictionary, investigations |
| 2 | Morphology | What does the grammar require? | MorphGNT / morphology codes |
| 3 | Immediate context | What is this clause doing? | Phrase tokens, syntax, connectors |
| 4 | General context | How does the author use this here? | Paragraph, pericope, book discourse |
| 5 | RV1909 review | How did a masterful Spanish translation render this? | RV1909 alignment only |

Gate 5 is consultative.

Gates 1–4 are authoritative.

---

## Gate 1 — Lemma

### Input

- Greek or Hebrew surface forms in the phrase
- Lemma per token
- Strong's or equivalent identifier when available

### Sources

- `cgv-dictionary`
- Approved investigations (`INV-####`)
- Occurrence evidence when policy is not yet stable

### Task

Determine the **allowed renderings** for each significant lemma.

This gate does not choose final Spanish wording.

It defines the legitimate lexical options.

### Output

```json
{
  "status": "resolved",
  "tokens": [
    {
      "sourceTokenId": "n56001001002",
      "lemma": "δοῦλος",
      "strongs": "G1401",
      "allowedRenderings": ["siervo"],
      "policySource": "cgv-dictionary/greek/G1401/lemma.json",
      "investigationId": null
    }
  ]
}
```

### Blocked state

If no stable policy exists for a significant lemma:

```json
{
  "status": "blocked",
  "blockedLemma": "G1401 δοῦλος",
  "investigationId": "INV-0001"
}
```

Translation pauses.

The translator opens or creates an investigation.

Gate 1 must not be bypassed.

### AI role

AI may:

- summarize dictionary policy
- summarize occurrence patterns
- surface parallel renderings from evidence files

AI may not:

- invent lemma policy
- override an approved investigation
- choose a rendering without policy support

---

## Gate 2 — Morphology

### Input

- Morphology / parsing code per token
- Allowed renderings from Gate 1

### Task

Determine what the grammar **requires** or **permits** in Spanish.

Grammar narrows lexical options.

Grammar does not redefine lemmas.

### Output

```json
{
  "status": "resolved",
  "constraints": [
    {
      "sourceTokenId": "n56001001002",
      "morphology": "N-NSM",
      "requirements": [
        "nominative singular required",
        "predicate nominative after copular construction"
      ],
      "permittedRenderings": ["siervo"]
    }
  ]
}
```

### Rule

Morphology establishes legitimate possibilities.

It does not select literary style.

### AI role

AI may explain morphology in plain Spanish and map grammatical requirements.

AI may not introduce meaning not supported by the parsing code.

---

## Gate 3 — Immediate Context

### Input

- Phrase token span
- Clause structure
- Connectors and function words in the phrase
- Outputs from Gates 1–2

### Task

Read the **immediate clause**.

Identify:

- subject
- predicate
- modifiers
- connectors
- subordinate elements
- discourse markers within the phrase

### Output

```json
{
  "status": "resolved",
  "structure": {
    "subject": ["Παῦλος"],
    "predicate": ["δοῦλος θεοῦ"],
    "notes": "Paul identifies himself as a slave of God before apostolic office."
  },
  "remainingOptions": [
    "siervo de Dios"
  ]
}
```

### Rule

Immediate context clarifies which grammatically valid option the author intends **in this clause**.

It does not import theology from outside the text.

### AI role

AI may propose a syntactic reading and explain the clause.

AI may not add referents, soften roles, or resolve deliberate ambiguity.

---

## Gate 4 — General Context

### Input

- Current verse
- Surrounding paragraph / pericope
- Book-level usage patterns
- Outputs from Gates 1–3

### Context order

Consult context in this order:

1. Immediate phrase (already handled in Gate 3)
2. Immediate verse
3. Local paragraph
4. Book discourse
5. Corpus parallels when available in project data

### Task

Disambiguate among options still open after Gates 1–3.

### Output

```json
{
  "status": "resolved",
  "scope": ["Titus 1:1", "Titus 1:1-4", "Epistle to Titus"],
  "notes": "Paul's opening self-description pattern; δοῦλος precedes ἀπόστολος.",
  "remainingOptions": [
    "siervo de Dios"
  ]
}
```

### Rule

Context clarifies authorial intent.

Context does not redefine words.

External theology never overrides the text.

### AI role

AI may cite in-book parallels and discourse notes from project data.

AI may not use theological systems as translation drivers.

---

## Gate 5 — RV1909 Review

### Input

- RV1909 aligned text for the phrase
- Outputs from Gates 1–4

### Task

Consult Reina-Valera 1909 **last**.

Compare the constrained LBF direction against RV1909.

Note:

- added words
- softened expressions
- resolved ambiguities
- traditional renderings
- excellent Spanish phrasing worth considering

### Output

```json
{
  "status": "consulted",
  "rv1909Text": "PABLO, siervo de Dios",
  "flags": [
    {
      "type": "added-traditional-connector",
      "note": "RV1909 uses comma after PABLO; Greek has no equivalent particle."
    }
  ],
  "advisoryNotes": [
    "Natural Spanish word order; dignified tone."
  ]
}
```

### Rule

RV1909 may inform style.

RV1909 may not override lemma, morphology, or context.

RV1909 must never auto-fill the working translation field.

---

## Synthesis — Proposed Spanish

After Gates 1–5 complete, the system may propose one Spanish phrase.

### Input

- Constraint stack from all gates
- BLE mechanical text as diagnostic contrast only
- RV1909 as advisory comparison only

### Output

```json
{
  "proposedSpanish": "Pablo, siervo de Dios,",
  "rationale": [
    "G1401 resolved to siervo by dictionary policy.",
    "N-NSM supports predicate nominative rendering.",
    "Immediate clause identifies Paul as slave of God.",
    "Book opening pattern supports self-description before apostolic title.",
    "RV1909 consulted; comma after Pablo retained for natural Spanish."
  ],
  "confidence": "high"
}
```

### Human actions

- Accept proposal
- Edit proposal
- Reject and translate manually
- Open investigation if Gate 1 blocked

Only **approved** Spanish is saved as LBF text.

---

## Translation View Layout

The existing Translation View layout remains.

Add a **Gate Status** panel.

```text
┌─────────────────────────────────────────────────────────────┐
│  Titus 1:1 · Phrase 1                                       │
├──────────────────────────┬──────────────────────────────────┤
│  Interlinear             │  Gate Status                     │
│  Παῦλος  δοῦλος  θεοῦ    │  ✓ Lemma                         │
│                          │  ✓ Morphology                    │
│                          │  ✓ Immediate context             │
│                          │  ○ General context               │
│                          │  ○ RV1909 review                 │
├──────────────────────────┴──────────────────────────────────┤
│  Working Spanish (human decision)                           │
├─────────────────────────────────────────────────────────────┤
│  References (read-only)                                     │
│  RV1909 · BLE mechanical · AI proposal                     │
└─────────────────────────────────────────────────────────────┘
```

### Actions

| Action | Behavior |
|--------|----------|
| Analyze phrase | Run Gates 1–4, then Gate 5 |
| Propose Spanish | Run synthesis after gates complete |
| Accept proposal | Copy proposal into working Spanish |
| Save phrase | Persist approved phrase and gate record |
| Open investigation | Jump to INV view when Gate 1 is blocked |

---

## Phrase Record Shape

Extend phrase storage beyond `spanish` and `rv1909Text`.

```json
{
  "reference": "Titus 1:1",
  "phraseIndex": 0,
  "greek": "Παῦλος δοῦλος θεοῦ",
  "spanish": "Pablo, siervo de Dios,",
  "sourceTokenIds": ["n56001001001", "n56001001002", "n56001001003"],
  "gates": {
    "lemma": {},
    "morphology": {},
    "immediateContext": {},
    "generalContext": {},
    "rv1909Review": {}
  },
  "aiProposal": "Pablo, siervo de Dios,",
  "approval": {
    "status": "approved",
    "approvedBy": "human",
    "approvedAt": "2026-07-11T20:00:00.000Z"
  },
  "suggestionSource": "lbf-approved"
}
```

### Source labels

| `suggestionSource` | Meaning |
|--------------------|---------|
| `blank` | No suggestion applied |
| `ble` | BLE mechanical diagnostic only |
| `rv1909` | RV1909 shown in references only; not a valid saved source |
| `ai-proposed` | AI synthesis awaiting approval |
| `lbf-approved` | Human-approved LBF phrase |
| `saved` | Legacy saved phrase prior to gate metadata |

---

## AI Rules

AI is a **pipeline assistant**, not a translator.

### AI may

- summarize gate inputs
- explain morphology and syntax in Spanish
- compare RV1909 against the constrained reading
- propose Spanish after all gates complete
- cite project data: dictionary, investigations, token rows, RV1909, BLE

### AI may not

- skip a gate
- start from RV1909
- invent lemma policy
- smooth, strengthen, explain away, or theologize beyond the text
- save output without human approval

### Prompt structure

Use one structured prompt per gate.

Each prompt receives only the output of prior gates.

Do not use a single-shot "translate this phrase" prompt.

---

## Operating Rules

1. Faithfulness to the text is king.
2. Lemma precedes morphology.
3. Morphology precedes context.
4. Context precedes RV1909.
5. RV1909 informs; it does not govern.
6. If the text repeats, Spanish should repeat when good Spanish allows.
7. If the text leaves tension or ambiguity, Spanish preserves it.
8. If the text is simple, Spanish remains simple.
9. Do not work from memory.
10. Do not work from theology.
11. Mechanical gathering belongs to software.
12. Scholarly judgment belongs to the translator.

---

## Implementation Order

### Phase 1 — Correct the authority order

- Remove RV1909 as default working-text fill
- Show RV1909 and BLE only in reference lane
- Start each phrase blank for a fresh LBF translation
- Keep phrase navigation and save behavior

### Phase 2 — Gate panel without AI

- Gate 1 from dictionary + investigations
- Gate 2 from morphology codes
- Gate 3 from phrase token structure
- Gate 4 from verse / paragraph context in project data
- Gate 5 RV1909 comparison flags

### Phase 3 — AI-assisted analysis

- Structured prompts per gate
- Phrase synthesis after gates complete
- Human approval required before save

### Phase 4 — Investigation integration

- Auto-block Gate 1 when lemma policy missing
- Resume phrase after investigation approval

---

## Success Criteria

A phrase is ready to save when:

1. Gates 1–4 are `resolved` or explicitly marked not applicable
2. Gate 5 is `consulted`
3. Working Spanish is human-approved
4. Every significant lemma is traceable to policy or investigation
5. The rendering can answer:

   - Did we add meaning?
   - Did we remove meaning?
   - Did we soften the text?
   - Did we strengthen the text?
   - Did we preserve the author's argument?

If any answer violates LBF rules, revise before save.

---

## Rule

The app manages the pipeline.

The translator manages judgment.

The text remains final authority.
