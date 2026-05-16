MNA
sources/ is immutable input authority.
Scripts may read from sources/.
Scripts may NEVER modify sources/.



**STAGE 1:**

python3 scripts/stage1/build_finite_verbs.py 1corintios
python3 scripts/stage1/update_verification_ledger.py 1corintios --date 2026-05-15

**STAGE 2:**

python3 scripts/stage2/build_predicate_anchors.py 1corintios
python3 scripts/stage2/validate_predicate_anchors.py 1corintios

**STAGE 3:**
python3 scripts/stage3/build_anchor_skeleton.py 1corintios
python3 scripts/stage3/validate_anchor_skeleton.py 1corintios

