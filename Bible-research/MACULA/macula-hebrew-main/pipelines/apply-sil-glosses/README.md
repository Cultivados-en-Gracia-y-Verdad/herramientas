# apply-sil-glosses

Pipeline to apply gloss mappings from a TSV file to `<m>` elements in `WLC/nodes` XML files.

## Setup

```bash
cd pipelines/apply-sil-glosses
poetry install
```

## Usage

```bash
poetry run python main.py ../../sources/biblicalhumanities/sil-hebrew-annotations/sil-gloss-mapping.tsv
```

This will apply glosses to all XML files in `WLC/nodes/` using the mappings from the TSV file.

### Options

```bash
poetry run python main.py <tsv-path> [options]

Options:
  --edition EDITION   Edition to process (default: WLC)
  --filter PATTERN    Glob pattern for files (default: *.xml)
  --dry-run           Report changes without writing files
  --verbose, -v       Print detailed progress
  --workers N         Number of parallel workers (default: auto)
  --debug             Run sequentially for easier debugging
```

### Examples

```bash
# Dry run to preview changes
poetry run python main.py ../../sources/biblicalhumanities/sil-hebrew-annotations/sil-gloss-mapping.tsv --dry-run

# Process only Genesis files with verbose output
poetry run python main.py ../../sources/biblicalhumanities/sil-hebrew-annotations/sil-gloss-mapping.tsv --filter "*Gen*" --verbose

# Debug mode (sequential processing)
poetry run python main.py ../../sources/biblicalhumanities/sil-hebrew-annotations/sil-gloss-mapping.tsv --debug
```

## How it works

The pipeline:
1. Loads gloss mappings from the TSV file (columns: `macula_id`, `gloss`)
2. Parses each XML file with lxml
3. Finds `<m>` elements and sets `gloss` attributes based on the mapping
4. Serializes the modified XML back to the file

Files are processed in parallel using `ProcessPoolExecutor` for efficiency.

## Post-processing

After running this pipeline, run the `nodes-format` pipeline to restore consistent XML formatting:

```bash
cd ../nodes-format
poetry run python main.py WLC
```

## Input format

The TSV file should have two columns:
- `macula_id`: The morph ID with `o` prefix (e.g., `o010010010011`)
- `gloss`: The gloss text (e.g., `in`, `beginning`, `he.created`)

## Statistics

The pipeline reports:
- Files processed and modified
- Morphs updated (new glosses added)
- Morphs that already had glosses
- Gloss mismatches (existing gloss differs from expected)
