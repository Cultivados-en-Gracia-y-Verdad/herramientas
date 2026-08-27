from pathlib import Path
import argparse
from .model import *

import os, unicodedata

ROOT = Path(__file__).resolve().parents[2]          # …/CGV-curriculo/manager
CGV = ROOT.parent                                    # …/CGV-curriculo
TEMPLATE = CGV / "templates" / "state.template.yaml"

# Per-book state lives with the book, not in the method repo (WORKFLOW.md §29).
# Override for a non-standard checkout with CGV_COURSES.
COURSES = Path(os.environ.get("CGV_COURSES", CGV.parents[1] / "curriculo"))
# Repo root that relative paths in state.yaml resolve against.
REPOS = Path(os.environ.get("CGV_REPOS", COURSES.parent))


def _fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def course_dir(pid):
    """Resolve a project id to its course folder: 'apocalipsis' -> '23.Apocalipsis'."""
    if not COURSES.is_dir():
        raise SystemExit(f"Courses directory not found: {COURSES}\n"
                         f"Set CGV_COURSES to the curriculo checkout.")
    direct = COURSES / pid
    if direct.is_dir():
        return direct
    want = _fold(pid)
    hits = [d for d in sorted(COURSES.iterdir())
            if d.is_dir() and _fold(d.name.split(".", 1)[-1]) == want]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f"No course folder in {COURSES} matches project id {pid!r}")
    raise SystemExit(f"Ambiguous project id {pid!r}: {', '.join(d.name for d in hits)}")


def ppath(pid): return course_dir(pid) / "state.yaml"

def get(pid):
    p = ppath(pid)
    if not p.exists(): raise SystemExit(f"Project not found: {pid}")
    return p, load_yaml(p)

def cmd_init(a):
    p = ppath(a.project)          # fails loudly if the course folder does not exist
    if p.exists(): raise SystemExit(f"Project state already exists: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    s = new_state(load_yaml(TEMPLATE), a.project, a.title or a.project)
    save_yaml(p,s)
    print(f"Created {p}")
    print("Next:", next_action(s))

def cmd_status(a):
    _,s=get(a.project); recompute(s)
    print("CGV MANAGER\n")
    print(f"Project: {s['project']['title']} ({s['project']['id']})")
    print(f"Project status: {s['project']['status']}")
    print(f"Workflow: {s['project']['workflow_version']}")
    print(f"Source: {s['source']['name']} {s['source']['revision'] or '[unversioned]'}")
    print(f"Alignment: {s['alignment']['status']}")
    print(f"Artifact: {'CURRENT' if s['artifact']['current'] else 'STALE / NONE'}\n")
    cg=s['workflow']['current_gate']
    print(f"Current gate: {cg} — {GATE_LABELS[cg]}")
    print(f"Next action: {next_action(s)}\n")
    symbols={"PASS":"✓","READY":"○","RUNNING":"▶","BLOCKED":"■","FAIL":"✗","REVIEW_REQUIRED":"!","STALE":"~","NOT_STARTED":"·","SKIPPED":"-"}
    print("GATES")
    for g in GATES:
        st=s["gates"][g]["status"]
        print(f"{symbols.get(st,'?')} {g:<16} {GATE_LABELS[g]:<38} {st}")
    print("\nBLOCKERS")
    bs=open_blockers(s)
    print("None" if not bs else "\n".join(f"- {b['id']} — {b['reason']}" for b in bs))
    print("\nRELEASE")
    print(s["workflow"]["release_status"])

def cmd_gate(a):
    p,s=get(a.project)
    notes = a.notes or ""
    if a.gate == "G0_ALIGNMENT" and a.status == "PASS":
        raise SystemExit("G0_ALIGNMENT cannot be hand-set to PASS. Accept a verified attestation instead.")
    if a.gate == "G1_COMPILE" and a.status == "PASS":
        raise SystemExit("G1_COMPILE cannot be hand-set to PASS. Use 'compile record' instead.")
    try:
        if a.gate == "G0_ALIGNMENT" and a.status == "SKIPPED":
            waive_gate0(s, REPOS, a.actor, notes)
        else:
            record_gate_status(s,a.gate,a.status,a.actor,notes)
    except ValueError as e:
        print(e); raise SystemExit(1)
    save_yaml(p,s)
    print(f"{a.gate}: {s['gates'][a.gate]['status']}")
    print("Next:", next_action(s))

def cmd_gate0_accept(a):
    p,s=get(a.project)
    ap=Path(a.attestation).expanduser().resolve()
    if not ap.exists(): raise SystemExit(f"Attestation not found: {ap}")
    try:
        accept_gate0(s, load_yaml(ap), str(ap), a.actor, REPOS)
    except ValueError as e:
        print(e); raise SystemExit(1)
    save_yaml(p,s)
    print("G0_ALIGNMENT: PASS")
    print(f"Source revision: {s['source']['revision']}")
    print(f"Alignment revision: {s['alignment']['revision']}")
    print("G1_COMPILE: READY")
    print("Next:", next_action(s))

def cmd_compile_record(a):
    p, s = get(a.project)
    try:
        digest = record_compile(s, REPOS, a.skeleton, a.progress, a.compiler_version or "", a.actor)
    except ValueError as e:
        print(e); raise SystemExit(1)
    save_yaml(p, s)
    g = s["gates"]["G1_COMPILE"]
    print("G1_COMPILE: PASS")
    print(f"  artifact revision   {g['output_artifact_revision']}")
    print(f"  artifact checksum   {digest}")
    print(f"  from source rev     {g['input_source_revision'] or '[none]'}")
    print(f"  from alignment rev  {g['input_alignment_revision'] or '[none]'}")
    print(f"  compiler            {g['compiler_version']}")
    if g.get("input_progress_checksum"):
        print(f"  observer progress   {g['input_progress_checksum'][:16]}…")
    print("Next:", next_action(s))


def cmd_provenance(a):
    p, s = get(a.project)
    findings = input_drift(s, REPOS)
    if not findings:
        print("PASS  every declared input matches what state records.")
        print("The reading is still required: that the recorded inputs are the right ones.")
        return
    print(f"DRIFT  {len(findings)} finding(s)\n")
    for what, detail in findings:
        print(f"  {what}\n      {detail}")
    if not a.apply:
        print("\nThis is evidence, not a verdict. Re-run with --apply to mark downstream gates STALE.")
        raise SystemExit(1)
    touched = mark_stale(s, [f"{w}: {d.splitlines()[0]}" for w, d in findings], a.actor)
    save_yaml(p, s)
    print("\nMarked STALE:", ", ".join(touched) or "nothing was PASS")
    print("regeneration_required = true")
    print("Next:", next_action(s))


def cmd_check(a):
    """Run every gate script for this book and print one verdict."""
    import subprocess
    course = course_dir(a.project)
    scripts = CGV / "scripts"
    lbf = None
    for cand in (REPOS/"cgv-data/bibles/LBF"/f"{a.project}.lbf.md",):
        if cand.exists(): lbf = cand
    if lbf is None:
        raise SystemExit(f"No LBF text found for {a.project}")

    def newest(folder, pattern):
        hits = sorted(folder.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True) if folder.is_dir() else []
        return hits[0] if hits else None

    progress = newest(course/"observation", "*progress*.json")
    skeleton = newest(course/"skeleton", "*skeleton*.md")
    manual   = newest(course/"manual", "*.md")
    blocks   = course/"blocks.md"

    steps = []
    if progress: steps.append(("Spans (Observer)", [scripts/"verify-clause-spans.py", "--progress", progress, "--lbf", lbf]))
    if skeleton: steps.append(("Skeleton packaging", [scripts/"verify-skeleton-h4-packaging.py", "--manual", skeleton, "--lbf", lbf]))
    if skeleton: steps.append(("Manual checks", [scripts/"run-manual-checks.py", "--manual", skeleton, "--lbf", lbf,
                                                 "--book", a.project, "--out", course/"reports/PYTHON_REPORT.md"]))
    if blocks.exists() and "NOT STARTED" not in blocks.read_text(encoding="utf-8"):
        steps.append(("Block inventory", [scripts/"verify-blocks.py", "--blocks", blocks, "--lbf", lbf]))
    if manual: steps.append(("Context quotes", [scripts/"build-context-quotes.py", "--manual", manual, "--lbf", lbf, "--check"]))

    if not steps:
        raise SystemExit(f"Nothing to check yet in {course.name} — no export, skeleton, blocks or manual.")

    print(f"CGV CHECK — {a.project}\n")
    results = []
    for label, argv in steps:
        r = subprocess.run(["python3", *[str(x) for x in argv]], capture_output=True, text=True)
        ok = r.returncode == 0
        results.append((label, ok, r.stdout))
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
    print()
    bad = [(l, out) for l, ok, out in results if not ok]
    if not bad:
        print("All checks pass. The reading is still required — a script is one witness, not the gate.")
        return 0
    for label, out in bad:
        print("─" * 68)
        print(f"{label}\n")
        print("\n".join(out.strip().splitlines()[:24]))
    print("─" * 68)
    print(f"\n{len(bad)} of {len(results)} failed. Evidence, not a verdict.")
    return 1


def cmd_validate(a):
    _,s=get(a.project)
    errs=validate_state(s)
    if errs:
        print("INVALID")
        for e in errs: print("-",e)
        raise SystemExit(1)
    print("VALID")

def parser():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)

    p=sub.add_parser("init"); p.add_argument("project"); p.add_argument("--title"); p.set_defaults(func=cmd_init)
    p=sub.add_parser("status"); p.add_argument("project"); p.set_defaults(func=cmd_status)
    p=sub.add_parser("validate"); p.add_argument("project"); p.set_defaults(func=cmd_validate)

    p=sub.add_parser("check", help="run every gate script for this book and print one verdict")
    p.add_argument("project"); p.set_defaults(func=cmd_check)

    c=sub.add_parser("compile", help="record a Compiler Generate against the declared inputs")
    cs=c.add_subparsers(dest="ccmd", required=True)
    p=cs.add_parser("record")
    p.add_argument("project"); p.add_argument("--skeleton", required=True)
    p.add_argument("--progress"); p.add_argument("--compiler-version", dest="compiler_version")
    p.add_argument("--actor", default="human")
    p.set_defaults(func=cmd_compile_record)

    p=sub.add_parser("provenance", help="recompute declared inputs and report drift")
    p.add_argument("project"); p.add_argument("--apply", action="store_true",
                   help="mark downstream gates STALE when drift is found")
    p.add_argument("--actor", default="human")
    p.set_defaults(func=cmd_provenance)

    p=sub.add_parser("gate")
    p.add_argument("project"); p.add_argument("gate",choices=GATES)
    p.add_argument("status",choices=["BLOCKED","NOT_STARTED","READY","RUNNING","REVIEW_REQUIRED","FAIL","PASS","STALE","SKIPPED"])
    p.add_argument("--actor",default="human"); p.add_argument("--notes")
    p.set_defaults(func=cmd_gate)

    g0=sub.add_parser("gate0")
    ss=g0.add_subparsers(dest="g0cmd",required=True)
    p=ss.add_parser("accept")
    p.add_argument("project"); p.add_argument("--attestation",required=True); p.add_argument("--actor",default="human")
    p.set_defaults(func=cmd_gate0_accept)
    return ap

def main():
    a=parser().parse_args()
    rc = a.func(a)
    if isinstance(rc, int) and rc: raise SystemExit(rc)
