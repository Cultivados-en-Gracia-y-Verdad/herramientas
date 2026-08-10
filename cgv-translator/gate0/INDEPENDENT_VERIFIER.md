# Independent Translator Gate 0 Verifier

## Input

Review the exact artifacts and `translator-gate0-report.yaml`.

## Required behavior

Do not modify Translator artifacts.

Treat the producer report as evidence, not truth.

Focus judgment on cases the deterministic audit cannot settle:

- whether phrase-to-source spans are linguistically defensible;
- whether reverse links are semantically/grammatically plausible;
- whether mechanically seeded links hide wrong relationships;
- whether suspicious omissions/duplications are genuine;
- whether the export preserves the intended LBF wording.

## Required result

Return structured findings and one of:

- `PASS`
- `REVIEW_REQUIRED`
- `FAIL`

A `PASS` requires no unresolved critical/high concern within the verifier's scope.
