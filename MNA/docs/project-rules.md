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
predicate completeness / independency testing

Stage 5
true trunk extraction
(independent clauses only)

Stage 6
[S] + [M] on trunk clauses only

Stage 7
connector relationships

Stage 8
labels / patterns / units

Stage 9
titles

-----

# STAGE 1

python3 scripts/stage1/build_finite_verbs.py 1corintios
python3 scripts/stage1/update_verification_ledger.py 1corintios --date 2026-05-15


# STAGE 2

python3 scripts/stage2/build_predicate_anchors.py 1corintios
python3 scripts/stage2/validate_predicate_anchors.py 1corintios


# STAGE 3

python3 scripts/stage3/build_anchor_skeleton.py 1corintios
python3 scripts/stage3/validate_anchor_skeleton.py 1corintios