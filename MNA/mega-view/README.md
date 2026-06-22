# CGV Mega View Prototype

This prototype reads CGV interlinear JSONL token files and produces book-level observable signals for Mega View study.

It does **not** produce ROOTS results or interpretation. It only surfaces data useful for manual observation.

## Input

Place interlinear token files here:

```text
datasets/interlinear/<book>.tokens.jsonl
```

Required token fields:

```json
{"book":"efesios","ch":1,"vs":1,"tok":1,"surface":"Παῦλος","lemma":"Παῦλος","morph":"N-----NSM-","es":"Pablo"}
```

## Run

```bash
python3 src/run_mega.py efesios
```

## Output

```text
output/<book>/
  discourse_markers.json
  mood_distribution.json
  imperatives.json
  repeated_lemmas.json
  contrast_markers.json
  boundary_signals.json
  mega_view.json
  mega_view.md
```

## Current engines

1. Discourse markers
2. Mood distribution
3. Imperative list
4. Repeated lemmas
5. Contrast marker / pair detection
6. Possible boundary signals

## Philosophy

The engine reports observable signals only:

- repeated lemmas
- discourse markers
- imperatives
- mood distribution
- contrast pairs
- possible transition signals

The human observer still determines movement, tension, patterns, and ROOTS structure.
