MNA
sources/ is immutable input authority.
Scripts may read from sources/.
Scripts may NEVER modify sources/.

-----

Stage 1
finite verbs

Stage 2
predicate anchors

Stage 3
ordered anchor skeleton

Stage 4
independency testing

Stage 5
true trunk extraction
(independent clauses only)

Stage 6
connector relationships on stable trunk structure

Stage 7
[S] + [M]

Stage 8
labels / patterns / units

Stage 9
titles

-----

\# STAGE 1 — finite verbs

python3 scripts/stage1/build_finite_verbs.py 1corintios
python3 scripts/stage1/update_verification_ledger.py 1corintios --date 2026-05-15


\# STAGE 2 — predicate anchors

python3 scripts/stage2/build_predicate_anchors.py 1corintios
python3 scripts/stage2/validate_predicate_anchors.py 1corintios


\# STAGE 3 — anchor skeleton + provisional signatures

python3 scripts/stage3/build_anchor_skeleton.py 1corintios
python3 scripts/stage3/validate_anchor_skeleton.py 1corintios