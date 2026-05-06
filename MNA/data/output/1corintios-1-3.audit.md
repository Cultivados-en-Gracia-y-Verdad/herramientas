# 1 Corinthians 1-3 MNA Audit

Audit command:

```bash
python3 MNA/audit_mna.py --morph MNA/data/MorphGNT/1corintios-morphgnt.txt MNA/data/fixtures/valid-1cor-1-1-10.md MNA/data/fixtures/valid-1cor-1-11-20.md MNA/data/fixtures/valid-1cor-1-21-30.md MNA/data/fixtures/valid-1cor-1-31.md MNA/data/fixtures/valid-1cor-2-1-10.md MNA/data/fixtures/valid-1cor-2-11-16.md MNA/data/fixtures/valid-1cor-3-1-10.md MNA/data/fixtures/valid-1cor-3-11-20.md MNA/data/fixtures/valid-1cor-3-21-23.md
```

Result:

```text
No audit errors found.
```

Scope checked:

- MNA validator errors
- Greek token sequence against MorphGNT
- MorphGNT verse availability

Notes:

- The audit initially flagged Greek-order mismatches in 1 Corinthians 1:2 and 1:7.
- Those were corrected so the MNA Greek and alignment order now follow SBLGNT/MorphGNT order.
