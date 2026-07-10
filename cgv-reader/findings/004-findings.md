# Finding 004

# PROIEL Annotation Methodology

**Status:** In Progress

---

## Research Objective

Investigate whether PROIEL's syntactic annotation methodology provides objective procedures that can assist the development of The Reader.

The purpose of this investigation is not to adopt dependency grammar.

The purpose is to identify objective annotation principles that expose the grammatical structure of the Greek text.

---

# Background

Unlike OpenText, PROIEL publishes its annotation guidelines.

This provides direct access to the methodology used by annotators rather than only the finished annotation.

This makes PROIEL an important source for understanding objective syntactic decisions.

---

# Finding 1

The verb remains the grammatical center.

PROIEL identifies one main predicate for every sentence.

Other verbal forms are interpreted according to their relationship to that predicate.

The annotation process therefore begins with the verb rather than with conjunctions.

**Result**

This strongly confirms the architecture already adopted by The Reader.

Finite verbs remain the primary structural anchor.

---

# Finding 2

Conjunctions are not the grammatical head.

Subordinating conjunctions do not become the head of subordinate clauses.

The finite verb remains the grammatical center of the clause.

The conjunction functions only as the grammatical connector.

**Result**

Clause openings are important observations.

However, they do not replace the finite verb as the organizing center of the clause.

---

# Finding 3

Relative clauses follow the same principle.

Relative pronouns are not treated as the head of the clause.

The finite verb remains the head.

The relative pronoun performs its grammatical role within the clause.

**Result**

The Reader should continue treating finite verbs as the primary anchor regardless of clause type.

---

# Finding 4

PROIEL separates grammatical structure from secondary evidence.

The annotation guidelines distinguish morphosyntactic structure from punctuation.

Punctuation may assist the annotator but does not determine the grammatical analysis.

**Result**

Objective grammatical evidence must remain primary.

Secondary clues should never replace grammatical evidence.

---

# Finding 5

Subordination cannot always be identified by conjunctions.

The annotation guidelines contain procedures for finite subordinate clauses without an explicit subordinating conjunction.

This demonstrates that conjunctions alone are insufficient for determining clause relationships.

The methodology must therefore include additional objective grammatical criteria.

**Result**

The investigation into clause relationships continues.

Searching only for connective words will not solve the problem.

---

# Impact on The Reader

This investigation strengthens several existing design decisions.

✓ Finite verbs remain the structural center.

✓ Clause Builder remains the correct second stage.

✓ Clause openings remain important observations.

✓ Connectives should not replace the finite verb as the organizing principle.

At the same time, the investigation demonstrates that clause openings alone cannot explain every subordinate relationship.

---

# Current Unknown

How does PROIEL objectively recognize finite subordinate clauses when no explicit subordinating conjunction is present?

This now becomes the primary research question.

Understanding this procedure may reveal objective grammatical principles that extend beyond connective words.

---

# Conclusion

PROIEL has reinforced rather than challenged the current architecture of The Reader.

The project independently arrived at the same fundamental principle adopted by PROIEL:

The finite verb is the grammatical center of the clause.

However, PROIEL also demonstrates that objective clause relationships cannot be reduced to connective words alone.

The next stage of investigation will therefore focus on the objective procedures used to recognize subordinate finite clauses that lack explicit conjunctions.