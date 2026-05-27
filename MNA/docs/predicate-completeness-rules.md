# Predicate Completeness Rules

## Status

This document defines the Stage 4 rule framework.

Stage 4 is currently active, but all real classification rules must be introduced slowly and explicitly.

Current default status remains:

```text
UNCERTAIN
```

No rule may classify a predicate-anchor environment as `INDEPENDENT` or `DEPENDENT` unless the rule is:

- named,
- bounded,
- auditable,
- reproducible,
- and validated against false positives.

---

# Governing Constraint

Independent clauses are determined by predicate completeness, not by connectors.

Connectors may be recorded later as evidence, but connectors must not govern independency.

This rule framework must therefore avoid connector-first parsing.

---

# Stage 4 Scope

Stage 4 classifies each predicate-anchor environment as one of:

```text
INDEPENDENT
DEPENDENT
UNCERTAIN
```

Stage 4 does not determine:

- trunk,
- `[S]`,
- `[M]`,
- labels,
- units,
- titles,
- full predicate spans,
- full clause boundaries.

---

# Rule Output Requirements

Each classification rule must produce:

- `predicate_completeness_status`,
- `independency_status`,
- `rule_id`,
- `reason`,
- `evidence_status`,
- `connector_dependency_used`.

If a rule cannot classify safely, it must return:

```text
UNCERTAIN
```

---

# Rule Safety Levels

## SAFE

A safe rule may assign `INDEPENDENT` or `DEPENDENT` only when the grammatical condition is explicit and mechanically detectable.

## CAUTION

A caution rule may identify a possible dependency environment but must normally leave the status `UNCERTAIN` until additional grammatical confirmation exists.

## UNSAFE

An unsafe rule must not classify. It may only record a warning or remain unresolved.

Unsafe patterns include:

- connector-only classification,
- punctuation-only classification,
- translation-based classification,
- semantic paraphrase classification,
- discourse-flow classification.

---

# Initial Rule Families

## PC-UNRESOLVED

Default unresolved state.

### PC-UNRESOLVED-001

Classification:

```text
UNCERTAIN
```

Reason:

```text
No formal predicate-completeness rule applied yet.
```

This is the current default for all Stage 4 rows.

---

# Future Rule Families

The following families are not yet implemented.

They must be defined and tested before use.

## PC-RELATIVE

Predicate-anchor environments that appear inside explicit relative constructions.

This rule family must not classify from relative words alone unless the finite verb environment is mechanically tied to a relative structure.

## PC-COMPLEMENT

Predicate-anchor environments that function as required complements of another predicate environment.

This rule family must be handled with extreme care because complement status can easily become semantic.

## PC-CONDITIONAL

Predicate-anchor environments that belong to conditional dependency environments.

Connectors may be present, but connector presence alone must not govern classification.

## PC-PURPOSE-RESULT

Predicate-anchor environments that belong to purpose/result dependency environments.

This rule family is high-risk if based only on connector presence.

## PC-QUOTATION

Predicate-anchor environments inside reported speech or quotation structures.

This family must distinguish quoted independent predication from syntactic dependence on a speech verb.

## PC-COORDINATE

Predicate-anchor environments that are coordinated with another predicate environment.

Coordination must not be treated as dependency automatically.

---

# Prohibited Rules

The following rule types are forbidden:

## Connector-Only Dependency Rule

Forbidden:

```text
connector present → DEPENDENT
```

Reason:

Connectors do not govern independency.

## Translation Punctuation Rule

Forbidden:

```text
Spanish/English punctuation → INDEPENDENT or DEPENDENT
```

Reason:

Translation punctuation is not source grammar.

## Semantic Guess Rule

Forbidden:

```text
meaning seems incomplete → DEPENDENT
```

Reason:

Stage 4 is grammatical, not semantic.

## Discourse Flow Rule

Forbidden:

```text
new topic / continuing thought → classification
```

Reason:

Discourse flow belongs later, if at all.

---

# Implementation Discipline

Every new rule must be added in this order:

```text
1. Define the rule in this document.
2. Add the rule to the Stage 4 builder.
3. Regenerate one book dataset.
4. Validate inheritance and anti-drift constraints.
5. Manually audit sample hits.
6. Only then expand or generalize.
```

---

# Current Implementation State

At the current stage, only this rule is active:

```text
PC-UNRESOLVED-001
```

Therefore all rows remain:

```text
UNCERTAIN
```

This is intentional and correct until real predicate-completeness rules are mature.
