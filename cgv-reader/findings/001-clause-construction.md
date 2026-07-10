# Finding 001

# Greek Clause Relationships
## Current Findings

**Status:** In Progress

---

## Research Question

After finite-verb clauses have been identified, how does Greek grammar objectively indicate the relationship between those clauses?

The purpose of this investigation is not to study discourse or semantics.

The objective is to determine whether clause relationships can be identified objectively enough to assist readers in observing the primary grammatical progression of a passage.

---

# Findings

## Finding 1

Finite verbs are the proper starting point.

OpenText begins clause analysis by first identifying the verbal predicate and then grouping the words belonging to that predicate into a clause.

This independently confirms the architecture currently used by The Reader.

**Result**

✅ Finite Verbs remain Brick 1.

---

## Finding 2

Clause construction precedes relationship analysis.

OpenText first establishes complete clauses.

Only after clauses exist are relationships considered.

This confirms the design of the Clause Builder.

**Result**

✅ Clause Builder remains the correct next step after finite verbs.

---

## Finding 3

Clause relationships are NOT determined at the clause level.

OpenText explicitly states that questions of connection and dependency cannot be resolved during clause annotation.

Those questions belong to paragraph-level annotation.

This explains why repeated attempts to determine dependency directly from completed clauses continually reached dead ends.

The problem was not implementation.

The problem was asking the clause level to answer a paragraph-level question.

**Result**

✅ Stop searching for complete clause dependency at the clause level.

---

## Finding 4

Clause openings appear significant.

While studying Titus through the new Clause Opening tool, several distinct clause openings immediately suggested different grammatical relationships.

Examples observed:

- ἵνα
- γάρ
- καί
- διὰ τοῦτο
- δι᾽ ἣν αἰτίαν

At present no conclusions are being drawn.

The observation is simply that the opening of a clause appears to communicate how the clause relates to surrounding clauses.

This remains under investigation.

**Result**

Research continues.

---

## Finding 5

The Clause Opening tool has become a research instrument.

Originally intended only to inspect the first words of a clause, the tool now allows direct observation of how Greek clauses begin.

This has shifted the research question away from:

> "Is this clause dependent?"

toward:

> "What grammatical relationship is signaled by the opening of this clause?"

This appears to be a more precise and potentially more objective question.

---

# Current Unknown

How does OpenText determine the paragraph-level "connect" relationship?

Specifically:

- What objective evidence is used?
- Which grammatical features participate?
- Which aspects remain interpretive?

This is now the primary research objective.

---

# Next Research Target

OpenText Paragraph Annotation

Goal:

Determine the methodology by which OpenText assigns clause connections ("connect").

No additional research questions will be pursued until this question has been answered.

---

# Architectural Impact

Current architecture becomes:

Finite Verbs
↓

Clause Builder
↓

Clause Openings
↓

Paragraph Connections
↓

Primary Grammatical Progression

Notice that "dependency" has intentionally been removed until its relationship to paragraph-level connection is understood.

---

# Conclusion

This investigation has already produced one significant result.

The repeated failure to determine clause dependency directly from completed clauses was not due to poor implementation.

It arose because the problem itself appears to belong to a higher level of grammatical analysis.

The next stage of research is therefore no longer Greek clause construction, but OpenText's methodology for connecting completed clauses within paragraphs.