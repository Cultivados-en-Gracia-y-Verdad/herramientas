# Finding 002

# OpenText Paragraph Annotation
## Current Findings

**Status:** In Progress

---

## Research Objective

Determine how OpenText establishes relationships between completed clauses.

This investigation is intentionally limited to one question.

> How does OpenText determine the "connect" relationship between clauses?

The objective is not to reproduce OpenText.

The objective is to understand whether its methodology provides objective grammatical observations suitable for The Reader.

---

# Background

During the investigation of clause dependency, repeated attempts were made to determine clause relationships directly from completed finite-verb clauses.

Those attempts consistently reached the same limitation.

The question appeared impossible to answer objectively at the clause level.

OpenText was therefore selected for investigation because it provides one of the most influential syntactic annotations of the Greek New Testament.

---

# Finding 1

OpenText explicitly separates clause identification from clause connection.

Clause identification belongs to clause annotation.

Clause connection belongs to paragraph annotation.

This distinction is fundamental.

It means that identifying a clause and determining how that clause relates to surrounding clauses are treated as two different problems.

**Result**

Clause construction and clause relationship should not be treated as the same stage within The Reader.

---

# Finding 2

Questions of "connection" and "dependency" are intentionally postponed.

OpenText explicitly states that questions regarding clause connection and dependency are not resolved while annotating individual clauses.

Instead, they are addressed at the paragraph level.

This explains why repeated attempts to determine dependency directly from completed clauses continually failed.

The problem was being asked at the wrong analytical level.

**Result**

Stop attempting to determine complete clause relationships from clause construction alone.

---

# Finding 3

The Reader's architecture changes.

Previous assumption:

Finite Verbs
↓

Clauses
↓

Dependency

Current understanding:

Finite Verbs
↓

Clause Builder
↓

Completed Clauses
↓

Paragraph Relationships

Dependency is therefore no longer assumed to be the next stage.

Instead, paragraph-level relationships become the next research target.

---

# Current Unknowns

The following questions remain unanswered.

1. What exactly is a "connect" relationship?

2. How is a connect relationship assigned?

3. Is connect determined purely from grammar?

4. Does connect require interpretive judgment?

5. Which observations remain objective?

These questions now define the entire scope of the investigation.

---

# Impact on The Reader

This finding significantly changes development priorities.

The Reader will continue to develop objective observation tools.

Relationship analysis will remain suspended until OpenText's paragraph methodology has been understood.

No implementation of clause dependency should proceed before this investigation is complete.

---

# Current Hypothesis

The Clause Opening tool may provide part of the observable evidence used when readers recognize clause relationships.

This remains a hypothesis only.

No implementation decisions should be based upon it until OpenText's methodology has been examined.

---

# Next Investigation

OpenText Paragraph Annotation

Goal:

Determine exactly how clause connections ("connect") are established.

Only after this question has been answered should implementation resume.

---

# Conclusion

This investigation has already prevented a significant architectural mistake.

The repeated failure to determine dependency at the clause level did not result from poor implementation.

It resulted from asking clause analysis to answer a question that OpenText itself assigns to paragraph analysis.

The next stage of research is therefore no longer clause dependency, but paragraph connection.