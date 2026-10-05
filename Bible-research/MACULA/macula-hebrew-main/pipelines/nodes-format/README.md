# nodes-format

Pipeline to reformat XML files in `WLC/nodes` with consistent pretty-printing.

## Setup

```bash
cd pipelines/nodes-format
poetry install
```

## Usage

```bash
poetry run python main.py WLC
```

This will reformat all XML files in `WLC/nodes/` in-place using Saxon to parse and serialize with consistent formatting.

## How it works

The pipeline uses Saxon (via `saxonche`) to:
1. Parse each XML file
2. Serialize it back with consistent formatting
3. Re-insert the XML declaration
4. Write the result back to the same file

Files are processed in parallel using `ProcessPoolExecutor` for efficiency.

## Environment Variables

- `MAX_WORKERS`: Number of parallel workers (default: CPU count - 1)
