# 1 Corinthians 4 MNA Audit

Audit command:

```bash
python3 MNA/audit_mna.py --morph MNA/data/MorphGNT/1corintios-morphgnt.txt MNA/data/fixtures/valid-1cor-4-1-10.md MNA/data/fixtures/valid-1cor-4-11-20.md MNA/data/fixtures/valid-1cor-4-21.md
```

Result:

```text
No audit errors found.
```

Scope checked:

- MNA validator errors
- Greek token sequence against MorphGNT
- MorphGNT verse availability
