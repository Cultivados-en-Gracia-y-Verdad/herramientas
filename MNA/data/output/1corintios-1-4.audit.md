# 1 Corinthians 1-4 MNA Audit

Audit command:

```bash
python3 MNA/audit_mna.py --morph MNA/data/MorphGNT/1corintios-morphgnt.txt MNA/data/output/1corintios-1-4.mna.locked.md
```

Result:

```text
No audit errors found.
```

Validation:

```text
Verses checked: 91
Errors: 0
Warnings: 0
```

Scope checked:

- MNA validator errors
- Greek token sequence against MorphGNT
- MorphGNT verse availability
