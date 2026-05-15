#!/bin/bash

# Usage:
# ./run_alignment.sh 1corintios-7-21

REF=$1

if [ -z "$REF" ]; then
  echo "Usage: ./run_alignment.sh 1corintios-7-21"
  exit 1
fi

G="data/g-tokens/$REF.txt"
S="data/s-tokens/$REF.txt"
OUT="data/alignments/$REF.tsv"
RULES="data/rules/alignment_rules.yaml"

echo "▶ Running engine..."
python3 scripts/suggest_alignment.py "$G" "$S" "$RULES" > "$OUT"

echo "▶ Running validator..."
python3 scripts/validate_alignment.py "$G" "$S" "$OUT"