# README-steps

## 1. Create / Edit TSV

TSV files live in:

```text
data/alignments/filemon/
```

Example:

```text
data/alignments/filemon/filemon-1-1.tsv
```

Each TSV must contain this header:

```tsv
BOOK	CH	VS	G_IDX	GREEK	NBLA_IDX	NBLA_TEXT	ALIGNMENT
```

Example rows:

```tsv
filemon	1	1	01	Παῦλος	01,02	Pablo ,	expanded
filemon	1	1	02	δέσμιος	03	prisionero	direct
```

---

## 2. Validate TSV

Validate BEFORE building JSON.

Run:

```bash
python3 scripts/validate_interlinear_tsv.py data/alignments/filemon/filemon-1-1.tsv
```

Expected:

```text
PASS filemon 1:1
```

---

## 3. Build JSON

Convert TSV → JSON.

Run:

```bash
python3 scripts/build_interlinear_json.py data/alignments/filemon/filemon-1-1.tsv
```

Output:

```text
data/interlinear/filemon/1/1.json
```

---

## 4. Enrich JSON

Attach:

- lemma
- MorphGNT morphology
- RMAC

from MorphGNT source.

Run:

```bash
python3 scripts/enrich_interlinear_json.py data/interlinear/filemon/1/1.json
```

---

## 5. Render Interlinear

Render the JSON as a reverse interlinear.

Run:

```bash
python3 scripts/render_interlinear.py data/interlinear/filemon/1/1.json
```

---

## 6. Build Entire Filemón

Automatically:

- build all JSON files
- enrich all JSON files

Run:

```bash
python3 scripts/build_filemon_interlinear.py
```

---

## Current Pipeline

```text
TSV
→ validate
→ JSON
→ enrich
→ render
```

---

## Architecture

### TSV

Canonical alignment source.

### JSON

Structured runtime format.

### Renderer

NBLA-centered reverse interlinear display.

### MorphGNT

Provides:

- lemma
- MorphGNT morphology
- RMAC conversion

---

## Important Principle

The system is:

```text
NBLA-centered
```

Meaning:

- NBLA order controls rendering
- Greek attaches underneath
- TSV rows become interlinear columns
