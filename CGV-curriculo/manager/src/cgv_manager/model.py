from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import yaml

GATES = [
    "G0_ALIGNMENT","G1_COMPILE","G2_MECHANICAL","G3_TEXTUAL","G4_SPECIALISTS",
    "G5_ARCHITECTURE","G6_WRITING","G7_EDITORIAL","G8_FINAL_VERIFY",
    "G9_HUMAN_REVIEW","G10_RELEASE",
]

GATE_LABELS = {
    "G0_ALIGNMENT": "Source / Alignment Validation",
    "G1_COMPILE": "Compiler Generate",
    "G2_MECHANICAL": "Structural / Mechanical Validation",
    "G3_TEXTUAL": "Textual Validation",
    "G4_SPECIALISTS": "Specialist Validation",
    "G5_ARCHITECTURE": "Architectural Review",
    "G6_WRITING": "Authorized Writing",
    "G7_EDITORIAL": "Editorial Processing",
    "G8_FINAL_VERIFY": "Final Verification",
    "G9_HUMAN_REVIEW": "Human Review",
    "G10_RELEASE": "Release Gate",
}

VALID_TRANSITIONS = {
    "NOT_STARTED": {"READY","BLOCKED"},
    "READY": {"RUNNING","BLOCKED"},
    "RUNNING": {"PASS","FAIL","REVIEW_REQUIRED","BLOCKED"},
    "REVIEW_REQUIRED": {"PASS","FAIL"},
    "FAIL": {"READY"},
    "PASS": {"STALE"},
    "STALE": {"READY"},
    "BLOCKED": {"READY"},
    "SKIPPED": set(),
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def new_state(template, project_id, title):
    s = deepcopy(template)
    s["project"]["id"] = project_id
    s["project"]["title"] = title
    return s

def open_blockers(state):
    return [b for b in state.get("blockers", []) if not b.get("resolved", False)]

def compute_current_gate(state):
    for g in GATES:
        if state["gates"][g]["status"] not in {"PASS","SKIPPED"}:
            return g
    return "G10_RELEASE"

def recompute(state):
    state["workflow"]["current_gate"] = compute_current_gate(state)
    if open_blockers(state):
        state["project"]["status"] = "BLOCKED"
    elif state["workflow"].get("release_status") == "RELEASED":
        state["project"]["status"] = "RELEASED"
    elif state["project"].get("status") not in {"PAUSED","ARCHIVED"}:
        state["project"]["status"] = "ACTIVE"

def record_event(state, actor, action, gate="", notes=""):
    events = state.setdefault("provenance", [])
    events.append({
        "id": f"EVT-{len(events)+1:06d}",
        "timestamp": now_iso(),
        "actor": actor,
        "action": action,
        "gate": gate,
        "notes": notes,
    })

def transition_gate(state, gate, new_status, actor="human", notes=""):
    cur = state["gates"][gate]["status"]
    if new_status == cur:
        return
    if new_status not in VALID_TRANSITIONS.get(cur, set()):
        raise ValueError(f"Illegal transition: {gate} {cur} -> {new_status}")
    idx = GATES.index(gate)
    if new_status in {"RUNNING","PASS","REVIEW_REQUIRED"}:
        for prev in GATES[:idx]:
            if state["gates"][prev]["status"] not in {"PASS","SKIPPED"}:
                raise ValueError(f"{gate} cannot proceed: {prev} has not passed.")
    if open_blockers(state) and new_status in {"RUNNING","PASS"}:
        raise ValueError("Project has open blockers.")
    state["gates"][gate]["status"] = new_status
    if new_status == "PASS" and idx + 1 < len(GATES):
        nxt = GATES[idx+1]
        if state["gates"][nxt]["status"] in {"BLOCKED","NOT_STARTED"}:
            state["gates"][nxt]["status"] = "READY"
    recompute(state)
    record_event(state, actor, f"{cur} -> {new_status}", gate, notes)


def skip_gate(state, gate, actor="human", notes=""):
    """Record an explicit human waiver without pretending that the gate passed."""
    if not notes.strip():
        raise ValueError("A skipped gate requires a reason and the person who decided.")
    cur = state["gates"][gate]["status"]
    if cur not in {"READY", "NOT_STARTED", "BLOCKED"}:
        raise ValueError(f"Illegal skip: {gate} is {cur}.")
    idx = GATES.index(gate)
    for prev in GATES[:idx]:
        if state["gates"][prev]["status"] not in {"PASS", "SKIPPED"}:
            raise ValueError(f"{gate} cannot be skipped: {prev} has not passed or been explicitly skipped.")
    state["gates"][gate]["status"] = "SKIPPED"
    state["gates"][gate]["skip_reason"] = notes
    if idx + 1 < len(GATES):
        nxt = GATES[idx + 1]
        if state["gates"][nxt]["status"] in {"BLOCKED", "NOT_STARTED"}:
            state["gates"][nxt]["status"] = "READY"
    recompute(state)
    record_event(state, actor, f"{cur} -> SKIPPED", gate, notes)


def record_gate_status(state, gate, new_status, actor="human", notes=""):
    """Apply an operator decision while preserving the state machine transitions.

    RUNBOOK commands record terminal results directly (for example READY -> PASS).
    Internally we still record the required RUNNING transition first.
    """
    if new_status == "SKIPPED":
        return skip_gate(state, gate, actor, notes)
    cur = state["gates"][gate]["status"]
    if cur == "READY" and new_status in {"PASS", "FAIL", "REVIEW_REQUIRED"}:
        transition_gate(state, gate, "RUNNING", actor, "Gate work began.")
    transition_gate(state, gate, new_status, actor, notes)

def verify_gate0_attestation(att, project_id, base: Path | None = None):
    errors = []
    if att.get("schema_version") != "0.1":
        errors.append("unsupported schema version")
    project = att.get("project", {})
    if project.get("book") != project_id:
        errors.append(f"book/project mismatch: expected {project_id}")
    if project.get("producer_project") != "cgv-translator":
        errors.append("producer_project must be cgv-translator")

    source = att.get("source", {})
    alignment = att.get("alignment", {})
    if source.get("name") != "LBF":
        errors.append("source must be LBF")

    for label, obj in [("source",source),("alignment",alignment)]:
        if not obj.get("path"): errors.append(f"{label} path missing")
        if not obj.get("revision"): errors.append(f"{label} revision missing")
        if not obj.get("checksum_sha256"): errors.append(f"{label} checksum missing")

    producer_required = [
        "verse_completeness","verse_order","duplicate_source_segments",
        "missing_source_segments","token_accounting","span_integrity","reproducibility"
    ]
    producer = att.get("producer", {})
    if producer.get("status") != "PASS":
        errors.append("producer status not PASS")
    for c in producer_required:
        if producer.get("checks", {}).get(c) != "PASS":
            errors.append(f"producer check not PASS: {c}")

    independent_required = [
        "source_identity","source_text_integrity","alignment_integrity",
        "span_boundary_review","suspicious_omission_review","suspicious_duplication_review"
    ]
    independent = att.get("independent_verification", {})
    if independent.get("status") != "PASS":
        errors.append("independent verification not PASS")
    for c in independent_required:
        if independent.get("checks", {}).get(c) != "PASS":
            errors.append(f"independent check not PASS: {c}")

    human = att.get("human_linguistic_review", {})
    if human.get("required", True) and human.get("status") != "PASS":
        errors.append("required human linguistic review not PASS")

    final = att.get("attestation", {})
    if final.get("status") != "VERIFIED":
        errors.append("attestation status not VERIFIED")
    if final.get("blockers"):
        errors.append("attestation has unresolved blockers")

    for label, obj in [("source",source),("alignment",alignment)]:
        p = Path(obj.get("path", "")).expanduser()
        if base is not None and not p.is_absolute():
            p = base / p
        if p.exists():
            if checksum(p) != obj.get("checksum_sha256"):
                errors.append(f"{label} checksum mismatch")
        else:
            errors.append(f"{label} file not found for checksum verification: {p}")

    return errors

def accept_gate0(state, att, attestation_path, actor="human", base: Path | None = None):
    errors = verify_gate0_attestation(att, state["project"]["id"], base)
    if errors:
        raise ValueError("Gate 0 attestation rejected:\n- " + "\n- ".join(errors))

    source = att["source"]
    alignment = att["alignment"]

    state["source"].update({
        "name":"LBF",
        "path":source["path"],
        "revision":source["revision"],
        "checksum":source["checksum_sha256"],
        "validated":True,
    })
    state["alignment"].update({
        "path":alignment["path"],
        "revision":alignment["revision"],
        "checksum":alignment["checksum_sha256"],
        "status":"PASS",
        "validated_at":att.get("attestation",{}).get("issued_at"),
        "validated_by":[
            att.get("producer",{}).get("tool_version") or "cgv-translator",
            att.get("independent_verification",{}).get("verifier") or "independent-verifier",
            att.get("human_linguistic_review",{}).get("reviewer") or "human-reviewer",
        ],
    })
    g = state["gates"]["G0_ALIGNMENT"]
    g.update({
        "attestation_path":attestation_path,
        "source_revision":source["revision"],
        "alignment_revision":alignment["revision"],
        "source_checksum":source["checksum_sha256"],
        "alignment_checksum":alignment["checksum_sha256"],
    })

    if g["status"] == "READY":
        transition_gate(state, "G0_ALIGNMENT", "RUNNING", actor, "Attestation received.")
    if state["gates"]["G0_ALIGNMENT"]["status"] in {"RUNNING","REVIEW_REQUIRED"}:
        transition_gate(state, "G0_ALIGNMENT", "PASS", actor, "Verified Translator attestation accepted.")

    state["artifact"]["current"] = False
    state["workflow"]["regeneration_required"] = True
    recompute(state)

# ---------------------------------------------------------------------------
# G1_COMPILE provenance
#
# STATE_MODEL.md §11 requires the compile to record which inputs produced which
# artifact. Without it the Manager cannot tell a fresh skeleton from a stale one,
# and §12 staleness cannot be computed — it can only be believed.
# ---------------------------------------------------------------------------

def short_rev(digest: str) -> str:
    return digest[:12]


def resolve(base: Path, declared: str) -> Path:
    p = Path(declared).expanduser()
    return p if p.is_absolute() else (base / p)


def waive_gate0(state, base: Path, actor="human", notes=""):
    """Proceed without certification while pinning the exact inputs by checksum.

    This is not a PASS and does not claim independent verification. The snapshots
    are needed so G1 can still refuse a compile if either input later changes.
    """
    if state["gates"]["G0_ALIGNMENT"]["status"] != "READY":
        raise ValueError("G0_ALIGNMENT can only be waived while READY.")
    snapshots = {}
    for label in ("source", "alignment"):
        obj = state.get(label, {})
        declared = obj.get("path", "")
        if not declared:
            raise ValueError(f"Cannot waive Gate 0: {label} path is missing.")
        path = resolve(base, declared)
        if not path.exists():
            raise ValueError(f"Cannot waive Gate 0: {label} file is missing: {path}")
        digest = checksum(path)
        obj["checksum"] = digest
        obj["revision"] = obj.get("revision") or f"sha256-{digest[:12]}"
        snapshots[label] = digest
    state["source"]["validated"] = False
    state["alignment"]["status"] = "SKIPPED"
    state["gates"]["G0_ALIGNMENT"].update({
        "waived": True,
        "source_checksum": snapshots["source"],
        "alignment_checksum": snapshots["alignment"],
    })
    skip_gate(state, "G0_ALIGNMENT", actor, notes)
    state["artifact"]["current"] = False
    state["workflow"]["regeneration_required"] = True
    recompute(state)


def input_drift(state, base: Path):
    """Recompute the declared inputs and report anything that no longer matches state.

    Returns a list of (what, detail). Empty means every declared input is unchanged.
    This is evidence. Marking gates STALE is a separate, recorded decision.
    """
    findings = []
    for label in ("source", "alignment"):
        obj = state.get(label, {})
        declared, recorded = obj.get("path"), obj.get("checksum")
        if not declared:
            findings.append((label, "no path declared in state"))
            continue
        f = resolve(base, declared)
        if not f.exists():
            findings.append((label, f"declared file is missing: {f}"))
            continue
        if not recorded:
            findings.append((label, "no checksum recorded — provenance was never established"))
            continue
        actual = checksum(f)
        if actual != recorded:
            findings.append((label, f"checksum changed\n      recorded {recorded[:16]}…\n      actual   {actual[:16]}…"))

    art = state.get("artifact", {})
    if art.get("path"):
        f = resolve(base, art["path"])
        if not f.exists():
            findings.append(("artifact", f"declared artifact is missing: {f}"))
        elif art.get("checksum") and checksum(f) != art["checksum"]:
            findings.append(("artifact", "artifact changed on disk since it was recorded"))

    if art.get("current"):
        if art.get("generated_from_source_revision") != state.get("source", {}).get("revision"):
            findings.append(("artifact", "marked current but built from a different source revision"))
        if art.get("generated_from_alignment_revision") != state.get("alignment", {}).get("revision"):
            findings.append(("artifact", "marked current but built from a different alignment revision"))
    return findings


def record_compile(state, base: Path, skeleton, progress=None, compiler_version="", actor="human"):
    """Record a Compiler Generate: which inputs, which output, and their checksums.

    Refuses when the declared inputs no longer match what G0 approved — a compile
    run against changed source is not a compile of the approved book.
    """
    sk = resolve(base, str(skeleton))
    if not sk.exists():
        raise ValueError(f"Skeleton not found: {sk}")

    drift = [d for d in input_drift(state, base) if d[0] in ("source", "alignment")]
    if drift:
        raise ValueError(
            "Refusing to record the compile — its declared inputs no longer match state:\n- "
            + "\n- ".join(f"{w}: {d}" for w, d in drift)
            + "\nResolve at G0 first. A compile against changed source is not a compile of the approved book."
        )

    art_sum = checksum(sk)
    g = state["gates"]["G1_COMPILE"]
    g.update({
        "compiler_version": compiler_version or "unrecorded",
        "input_source_revision": state["source"].get("revision", ""),
        "input_alignment_revision": state["alignment"].get("revision", ""),
        "input_source_checksum": state["source"].get("checksum", ""),
        "input_alignment_checksum": state["alignment"].get("checksum", ""),
        "output_artifact_revision": short_rev(art_sum),
        "output_checksum": art_sum,
        "generated_at": now_iso(),
    })
    if progress:
        pf = resolve(base, str(progress))
        if not pf.exists():
            raise ValueError(f"Observer progress file not found: {pf}")
        g["input_progress_path"] = str(progress)
        g["input_progress_checksum"] = checksum(pf)

    state["artifact"].update({
        "path": str(skeleton),
        "revision": short_rev(art_sum),
        "checksum": art_sum,
        "generated_from_source_revision": state["source"].get("revision", ""),
        "generated_from_alignment_revision": state["alignment"].get("revision", ""),
        "generated_at": g["generated_at"],
        "current": True,
    })
    state["compiler"].update({
        "name": state.get("compiler", {}).get("name") or "CGV Reader Compiler",
        "version": compiler_version or "unrecorded",
        "last_run_at": g["generated_at"],
    })
    state["workflow"]["regeneration_required"] = False

    if state["gates"]["G1_COMPILE"]["status"] == "STALE":
        transition_gate(state, "G1_COMPILE", "READY", actor, "Regenerating after upstream change.")
    if state["gates"]["G1_COMPILE"]["status"] == "READY":
        transition_gate(state, "G1_COMPILE", "RUNNING", actor, "Compiler Generate recorded.")
    if state["gates"]["G1_COMPILE"]["status"] == "RUNNING":
        transition_gate(state, "G1_COMPILE", "PASS", actor,
                        f"artifact {short_rev(art_sum)} from source {state['source'].get('revision','?')}")
    record_event(state, actor, "compile recorded", "G1_COMPILE",
                 f"artifact={short_rev(art_sum)} compiler={compiler_version or 'unrecorded'}")
    recompute(state)
    return art_sum


def mark_stale(state, reasons, actor="human", from_gate="G0_ALIGNMENT"):
    """STATE_MODEL §12 — an upstream change invalidates downstream passes.

    Only PASS gates become STALE; the transition table forbids anything else.
    """
    start = GATES.index(from_gate)
    touched, blocked = [], []
    why = "; ".join(reasons)[:200]
    for g in GATES[start:]:
        st = state["gates"][g]["status"]
        if st == "PASS":
            transition_gate(state, g, "STALE", actor, why)
            touched.append(g)
        elif st in {"READY", "NOT_STARTED", "RUNNING", "REVIEW_REQUIRED"}:
            # A gate cannot be eligible while a prerequisite is stale (STATE_MODEL §12).
            if st in {"RUNNING", "REVIEW_REQUIRED"}:
                transition_gate(state, g, "BLOCKED", actor, why)
            else:
                state["gates"][g]["status"] = "BLOCKED"
            blocked.append(g)
    if blocked:
        record_event(state, actor, "downstream gates blocked", from_gate, ", ".join(blocked))
    state["artifact"]["current"] = False
    state["workflow"]["regeneration_required"] = True
    state["workflow"]["release_status"] = "NOT_RELEASED"
    record_event(state, actor, "upstream change — downstream marked STALE", from_gate, "; ".join(reasons)[:300])
    recompute(state)
    return touched


def validate_state(state):
    errors = []
    for idx, g in enumerate(GATES):
        status = state["gates"][g]["status"]
        if status in {"PASS","SKIPPED"}:
            for prev in GATES[:idx]:
                if state["gates"][prev]["status"] not in {"PASS","SKIPPED"}:
                    errors.append(f"{g} passed while {prev} has not passed")
    if state["gates"]["G1_COMPILE"]["status"] == "PASS":
        g1 = state["gates"]["G1_COMPILE"]
        if not g1.get("output_checksum"):
            errors.append("G1_COMPILE passed with no output checksum — provenance was never recorded")
        if not g1.get("input_source_revision"):
            errors.append("G1_COMPILE passed with no input source revision")
    if state["artifact"].get("current"):
        if state["artifact"].get("generated_from_source_revision") != state["source"].get("revision"):
            errors.append("current artifact source revision mismatch")
        if state["artifact"].get("generated_from_alignment_revision") != state["alignment"].get("revision"):
            errors.append("current artifact alignment revision mismatch")
    return errors

def next_action(state):
    if open_blockers(state):
        b = open_blockers(state)[0]
        return f"Resolve blocker {b['id']}: {b['reason']}"
    g = compute_current_gate(state)
    st = state["gates"][g]["status"]
    label = GATE_LABELS[g]
    if st == "READY": return f"Start {g} — {label}"
    if st == "RUNNING": return f"Complete {g} — {label}"
    if st == "REVIEW_REQUIRED": return f"Review {g} — {label}"
    if st == "FAIL": return f"Resolve failures and reset {g} to READY"
    if st == "STALE": return f"Rerun {g} — {label}"
    if st == "BLOCKED": return f"{g} — {label} is blocked"
    return f"Review {g} — {label}"
