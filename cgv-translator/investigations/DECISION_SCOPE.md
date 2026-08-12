# Investigation Decision Scope

**Status:** Active

An investigation decision is not merely a mapping from an original-language lemma to one fixed Spanish string.

Every approved investigation decision must declare the scope at which its translation guidance applies.

## Canonical scopes

### Occurrence

Use when the decision applies only to a specific biblical occurrence.

Required metadata:

- `Scope: Occurrence`
- `Scope Reference: <book chapter:verse>`

The decision does not automatically govern other occurrences of the same lemma.

### Construction

Use when the decision depends on a particular morphological or syntactic construction.

Required metadata:

- `Scope: Construction`
- `Scope Condition: <condition>`

Machine-matchable conditions may use exact clauses separated by semicolons:

```text
morph=<exact morphology code>
surface=<exact source surface form>
lemma=<exact lemma>
strongs=<exact Strong's id>
```

All supplied clauses must match. If a construction condition cannot be safely evaluated by the Translator, the approved decision remains documented guidance but must not be applied automatically.

### Book Default

Use when the preferred rendering represents the normal lexical sense for that lemma throughout the owning book unless local morphology, syntax, discourse, idiom, or sense requires a different realization.

Required metadata:

- `Scope: Book Default`

A Book Default is guidance, not a word-replacement rule.

For example, a book-default lexical decision of `rey` may be realized locally as `rey`, `el rey`, `reyes`, `rey de ...`, or another grammatically required form while retaining the approved lexical sense.

## Application precedence

When more than one approved decision could inform an occurrence, Translator uses the most specific applicable scope:

```text
Occurrence
  ↓
Construction
  ↓
Book Default
```

An occurrence-specific decision overrides broader guidance for that occurrence. A matching construction-specific decision overrides a book default for that construction.

## Human approval

Scope is part of the decision itself.

AI may gather evidence, propose a rendering, propose a scope, or explain possible consequences. AI must not provide final approval.

A decision becomes binding Translator policy only when a human explicitly approves the exact decision content, including:

- preferred rendering;
- scope;
- required scope reference or condition;
- reason;
- confidence;
- human approval provenance.

Changing the scope of an already approved decision creates a revised decision that requires new human approval.

## Book ownership

Investigation scope never silently becomes cross-book global policy.

A book-owned decision may inform later work in another book as evidence, but the later book must evaluate its own context. A decision from one book does not automatically bind another book.
