# Stage 5 Current State

## Purpose

Stage 5 is the true trunk-survivability layer.

It does not replace ROOTS. It prepares mechanically auditable survival decisions from prior MNA stages.

## Current Status

Stage 5 is active and mechanically usable, but not final.

Current 1 Corinthians v2 survival totals:

```text
SURVIVE       854
PRESERVE_WARN 173
```

Current policy audit:

```text
FAILURES: 0
WARNINGS: 54
FLAGS: 0
```

The warnings are intentional anomaly-monitoring warnings, not policy failures.

## Major Achievements

Stage 5 now has:

- connector normalization
- connector environment profiling
- anomaly detection
- structural-state classification
- policy-state classification
- policy-aware survival gating
- survival-policy auditing
- anchor-skeleton enrichment
- inherited-survival environment profiling

## Key Datasets

```text
MNA/datasets/stage5/1corintios/1corintios-stage5-input.jsonl
MNA/datasets/stage5/1corintios/1corintios-trunk-survival-v2.jsonl
MNA/datasets/stage5/1corintios/1corintios-trunk-survival-v2-enriched.jsonl
MNA/datasets/stage5/1corintios/connector-structural-states.jsonl
MNA/datasets/stage5/1corintios/connector-policy-states.jsonl
MNA/datasets/stage5/1corintios/survival-policy-audit-v2.jsonl
MNA/datasets/stage5/1corintios/inherited-survival-environments.jsonl
```

## Key Scripts

```text
MNA/scripts/stage5/export_stage4_for_stage5.py
MNA/scripts/stage5/extract_trunk_survival.py
MNA/scripts/stage5/extract_trunk_survival_v2.py
MNA/scripts/stage5/connector_normalization.py
MNA/scripts/stage5/summarize_connector_environments.py
MNA/scripts/stage5/detect_connector_anomalies.py
MNA/scripts/stage5/classify_connector_structural_states.py
MNA/scripts/stage5/classify_connector_policy_states.py
MNA/scripts/stage5/audit_survival_against_policy.py
MNA/scripts/stage5/enrich_survival_with_anchor_skeleton.py
MNA/scripts/stage5/profile_inherited_stage4_survivals.py
MNA/scripts/stage5/classify_inherited_survival_environments.py
```

## Connector Structural States

Current normalized connector structural states for 1 Corinthians:

```text
UNIFORM:
ὅτι, ἐὰν, καθὼς, εἴτε, ὅταν, ἐπεὶ, ἐπειδὴ, ὅτε

DOMINANT_WITH_SPARSE_ANOMALIES:
εἰ, ἵνα

MIXED_SUBCLASS:
ὡς, ὥστε, ἄχρι

UNRESOLVED_LOW_DATA:
εἴπερ, καθάπερ, ἕως, ὅπως
```

## Connector Policy States

Current deterministic policy mapping:

```text
UNIFORM -> PRESERVE_SAFE
DOMINANT_WITH_SPARSE_ANOMALIES -> PRESERVE_WITH_ANOMALY_MONITORING
MIXED_SUBCLASS -> SUBCLASS_REQUIRED
UNRESOLVED_LOW_DATA -> INSUFFICIENT_DATA
```

Policy state does not equal survival decision.

Policy state constrains allowed survival behavior.

## Current Rule Distribution

Current v2 survival rule counts:

```text
728  S5-PRESERVE-STAGE4-SURVIVES-001
173  S5-PRESERVE-WARN-UNKNOWN-001
102  S5-PRESERVE-CONDITIONAL-UNIT-001
 12  S5-TEMPORAL-CONDITION-SURVIVE-001
 12  S5-COORDINATING-SURVIVE-001
```

## Inherited Stage 4 Survival Layer

The inherited layer currently contains:

```text
728 inherited survivals
604 indicative
 92 imperative
 31 subjunctive
  1 optative
```

This layer is no longer opaque because anchor-skeleton enrichment now attaches observable predicate metadata to each inherited survival row.

## Important Current Constraint

The inherited Stage 4 layer is still large.

Do not treat it as final trunk certainty.

It is currently observable inherited survivability, not fully independent Stage 5 survivability.

## Current Stage 5 Discipline

Stage 5 must continue to follow:

```text
observe
measure
classify
refine
recount
audit
```

No semantic importance.

No rhetorical weighting.

No intuition-driven promotion.

No forced convergence toward SURVIVE.

## Next Work

The next Stage 5 work should focus on:

1. Persisting all current v2 outputs.
2. Auditing inherited survival environments.
3. Reducing opaque inherited survival dependence only through observable environment rules.
4. Keeping SUBCLASS_REQUIRED families blocked from global survival until subclass rules exist.
5. Preparing a final Stage 5 candidate only after inherited environments are sufficiently profiled.
