#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

MECHANICAL_PHASE = [
 ["scripts/rebuild/rebuild_stages_1_4_book.py","{book}","--date","{date}"],
 ["scripts/stage4/build_predicate_completeness.py","{book}"],
 ["scripts/stage4/validate_predicate_completeness.py","{book}"],
 ["scripts/stage4/build_independent_clause_candidates.py","{book}"],
 ["scripts/stage4/validate_independent_clause_candidates.py","{book}"],
 ["scripts/stage4/build_suggested_trunk_draft.py","{book}"],
 ["scripts/stage4/promote_suggested_trunk_rows.py","{book}"],
 ["scripts/stage4/export_review_batch_candidate.py","{book}"],
]

AUTHORITATIVE_PHASE = [
 ["scripts/stage4/accept_review_batch_candidate.py","{book}","--batch","01","--reviewer","{reviewer}","--confirm-reviewed"],
 ["scripts/rebuild/rebuild_stages_1_4_book.py","{book}","--date","{date}"],
 ["scripts/rebuild/rebuild_stage5_book.py","{book}"],
]

def root_from_script() -> Path:
 return Path(__file__).resolve().parents[2]

def run_command(args, cwd):
 print(f'\nRUNNING: {" ".join(args)}\n')
 return subprocess.run(args, cwd=cwd).returncode

def materialize(template, book, date, reviewer):
 return [t.format(book=book, date=date, reviewer=reviewer) for t in template]

def main():
 p = argparse.ArgumentParser()
 p.add_argument('book')
 p.add_argument('--date', required=True)
 p.add_argument('--reviewer', default='UNSPECIFIED_REVIEWER')
 p.add_argument('--confirm-reviewed', action='store_true')
 args = p.parse_args()
 root = root_from_script()
 book = args.book.strip().lower()

 print('MNA Honest Rebuild Orchestrator')
 print(f'BOOK: {book}')
 print('\nPHASE 1 — MECHANICAL GENERATION\n')

 for template in MECHANICAL_PHASE:
  command = materialize(template, book, args.date, args.reviewer)
  code = run_command([sys.executable] + command, root)
  if code != 0:
   print('\nPIPELINE STOPPED DURING MECHANICAL PHASE')
   return code

 if not args.confirm_reviewed:
  print('\nSTOPPED BEFORE REVIEW BOUNDARY')
  print('Review-batch candidates exported.')
  print('Human review still required.')
  return 0

 print('\nPHASE 2 — AUTHORITATIVE REBUILD\n')

 for template in AUTHORITATIVE_PHASE:
  command = materialize(template, book, args.date, args.reviewer)
  code = run_command([sys.executable] + command, root)
  if code != 0:
   print('\nPIPELINE STOPPED DURING AUTHORITATIVE PHASE')
   return code

 print('\nSTAGE 5 COMPLETE')
 print(f'BOOK: {book}')
 print('PIPELINE STATUS: PASS')
 return 0

if __name__ == '__main__':
 raise SystemExit(main())