from pathlib import Path
import argparse
from .model import *

ROOT = Path(__file__).resolve().parents[2]
PROJECTS = ROOT / "projects"
TEMPLATE = ROOT / "state.template.yaml"

def ppath(pid): return PROJECTS / pid / "state.yaml"

def get(pid):
    p = ppath(pid)
    if not p.exists(): raise SystemExit(f"Project not found: {pid}")
    return p, load_yaml(p)

def cmd_init(a):
    p = ppath(a.project)
    if p.exists(): raise SystemExit("Project already exists")
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
    transition_gate(s,a.gate,a.status,a.actor,a.notes or "")
    save_yaml(p,s)
    print(f"{a.gate}: {s['gates'][a.gate]['status']}")
    print("Next:", next_action(s))

def cmd_gate0_accept(a):
    p,s=get(a.project)
    ap=Path(a.attestation).expanduser().resolve()
    if not ap.exists(): raise SystemExit(f"Attestation not found: {ap}")
    try:
        accept_gate0(s, load_yaml(ap), str(ap), a.actor)
    except ValueError as e:
        print(e); raise SystemExit(1)
    save_yaml(p,s)
    print("G0_ALIGNMENT: PASS")
    print(f"Source revision: {s['source']['revision']}")
    print(f"Alignment revision: {s['alignment']['revision']}")
    print("G1_COMPILE: READY")
    print("Next:", next_action(s))

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
    a=parser().parse_args(); a.func(a)
