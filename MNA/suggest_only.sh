#!/bin/bash

REF=$1

if [ -z "$REF" ]; then
  echo "Usage: ./suggest_only.sh 1corintios-7-34"
  exit 1
fi

G="data/g-tokens/$REF.txt"
S="data/s-tokens/$REF.txt"
OUT="data/alignments/$REF.tsv"
ORIG="data/alignments/$REF.original.tsv"
RULES="data/rules/alignment_rules.yaml"

echo "▶ Running engine..."
python3 scripts/suggest_alignment.py "$G" "$S" "$RULES" > "$OUT"

# Only create original if it doesn't exist
if [ ! -f "$ORIG" ]; then
  cp "$OUT" "$ORIG"
  echo "✔ Original snapshot created"
else
  echo "⚠ Original already exists — not overwriting"
fi

echo "Draft written to $OUT"