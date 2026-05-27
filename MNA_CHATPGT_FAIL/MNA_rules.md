SPAN RULE

For every Greek token, the Spanish field must contain the full NBLA expression assigned to that token.

A Spanish span is valid only if:

1. every non-supplied word appears in the NBLA verse;
2. the words appear in the same order as NBLA;
3. the span is contiguous in NBLA unless the alignment explicitly allows a split span;
4. if the Spanish expression contains more than one NBLA word, alignment must be expanded, merged-forward, or merged-backward, not direct;
5. direct is allowed only when one Greek token maps to one Spanish word;
6. missing is allowed only when no NBLA word is used and the supplied Spanish is marked with parentheses;
7. supplied words may not be counted as NBLA words;
8. two identical Greek forms in the same verse must have occurrence numbers internally so the validator does not collapse them.