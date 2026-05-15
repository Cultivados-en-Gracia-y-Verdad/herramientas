#!/bin/bash

# Usage:
# ./verify_only.sh 1corintios-7-24

REF=$1

if [ -z "$REF" ]; then
  echo "Usage: ./verify_only.sh 1corintios-7-24"
  exit 1
fi

python3 scripts/validate_alignment.py \
  "data/g-tokens/$REF.txt" \
  "data/s-tokens/$REF.txt" \
  "data/alignments/$REF.tsv"