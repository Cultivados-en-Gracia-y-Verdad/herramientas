from __future__ import annotations

import cgi
import json
import os
import socket
import subprocess
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .cli import CGV, COURSES, REPOS, course_dir
from .model import (
    GATES,
    GATE_LABELS,
    MECHANICAL_PASS_GATES,
    VALID_TRANSITIONS,
    accept_gate0,
    apply_mechanical_gate_result,
    checksum,
    compute_current_gate,
    invalidate_stale_mechanical_passes,
    load_yaml,
    input_drift,
    next_action,
    open_blockers,
    record_compile,
    record_event,
    recompute,
    save_yaml,
    record_gate_status,
    transition_gate,
    validate_state,
    waive_gate0,
)

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"
HOST = "127.0.0.1"
PORT = 8765
MAX_UPLOAD = 20 * 1024 * 1024
STATE_LOCK = threading.Lock()
PIPELINE_DIRS = ("observation", "skeleton", "architecture", "manual", "reports", "slides")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


def preferred_manual(folder: Path):
    """Student surface for G7/G8: prefer manual.md, else newest markdown."""
    named = folder / "manual" / "manual.md"
    if named.is_file():
        return named
    manuals = files_in(folder / "manual", {".md", ".markdown"})
    return manuals[0] if manuals else None


def files_in(folder: Path, suffixes=None):
    if not folder.is_dir():
        return []
    found = [p for p in folder.rglob("*") if p.is_file() and not p.name.startswith(".")]
    if suffixes:
        found = [p for p in found if p.suffix.lower() in suffixes]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPOS.resolve()))
    except ValueError:
        return str(path.resolve())


def state_for(course: str):
    folder = course_dir(course)
    state_path = folder / "state.yaml"
    if not state_path.exists():
        raise ValueError(f"No state.yaml exists in {folder.name}.")
    state = load_yaml(state_path)
    before = {g: state["gates"][g]["status"] for g in MECHANICAL_PASS_GATES}
    invalidate_stale_mechanical_passes(state, preferred_manual(folder))
    recompute(state)
    after = {g: state["gates"][g]["status"] for g in MECHANICAL_PASS_GATES}
    if before != after:
        save_yaml(state_path, state)
    return folder, state_path, state


def repo_snapshot():
    repos = [
        ("herramientas", REPOS / "herramientas"),
        ("curriculo", REPOS / "curriculo"),
        ("cgv-reader", REPOS / "cgv-reader"),
        ("cgv-data", REPOS / "cgv-data"),
    ]
    results = []
    for name, path in repos:
        if not (path / ".git").exists():
            results.append({"name": name, "clean": False, "count": 0, "note": "Repository not found"})
            continue
        try:
            run = subprocess.run(
                ["git", "-C", str(path), "status", "--short"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            changes = [line for line in run.stdout.splitlines() if line.strip()]
            results.append({"name": name, "clean": not changes, "count": len(changes), "note": ""})
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append({"name": name, "clean": False, "count": 0, "note": str(exc)})
    return results


def gate_rank(state, gate: str) -> int:
    current = compute_current_gate(state)
    return GATES.index(current) - GATES.index(gate)


def step_status(done: bool, active: bool = False, blocked: bool = False) -> str:
    if done:
        return "done"
    if blocked:
        return "blocked"
    if active:
        return "active"
    return "waiting"


def build_steps(folder: Path, state: dict, repos: list[dict]):
    manager = state.get("manager", {})
    preflight = manager.get("preflight", {})
    evidence = manager.get("evidence", {})
    cursor_link = Path.home() / ".cursor" / "agents" / "arquitecto.md"
    cursor_confirmed = bool(preflight.get("cursor_agents_verified"))
    cursor_on_disk = cursor_link.exists()
    all_clean = all(item["clean"] for item in repos)
    missing_course_items = [name for name in ("spec.md", "blocks.md", "state.yaml") if not (folder / name).exists()]
    missing_course_items += [f"{name}/" for name in PIPELINE_DIRS if not (folder / name).is_dir()]
    course_valid = not validate_state(state)
    observer_files = files_in(folder / "observation")
    skeleton_files = files_in(folder / "skeleton", {".md", ".markdown", ".txt"})
    blocks = folder / "blocks.md"
    blocks_started = blocks.exists() and "NOT STARTED" not in blocks.read_text(encoding="utf-8", errors="ignore")
    blocks_verified = False
    if blocks_started and evidence.get("blocks_checksum"):
        blocks_verified = checksum(blocks) == evidence["blocks_checksum"]
    manuals = files_in(folder / "manual", {".md", ".markdown"})
    quote_count = 0
    if manuals:
        quote_count = sum(1 for line in manuals[0].read_text(encoding="utf-8", errors="ignore").splitlines() if line.startswith("="))

    g = state["gates"]
    skeleton_checked = bool(skeleton_files and evidence.get("skeleton_checks_checksum") == checksum(skeleton_files[0]))
    final_checked = bool(manuals and evidence.get("final_verify_checksum") == checksum(manuals[0]))
    return [
        {
            "number": 0,
            "title": "Confirm Cursor agents",
            "detail": "Type @arquitecto in Cursor and confirm that the agent appears.",
            "status": step_status(cursor_confirmed, active=not cursor_confirmed),
            "note": "Symlink resolves on disk; Cursor still needs your confirmation." if cursor_on_disk and not cursor_confirmed else ("Confirmed" if cursor_confirmed else "Agent link not found"),
            "action": "confirm-cursor" if not cursor_confirmed else "",
        },
        {
            "number": 1,
            "title": "Commit the working repositories",
            "detail": "The process starts from recorded, reproducible inputs.",
            "status": step_status(all_clean, active=cursor_confirmed and not all_clean),
            "note": "All four repositories are clean." if all_clean else ", ".join(f"{r['name']}: {r['count']} change(s)" for r in repos if not r["clean"]),
            "action": "",
        },
        {
            "number": 2,
            "title": "Validate the course workspace",
            "detail": "Confirm spec.md, blocks.md, state.yaml, the pipeline folders, and a valid Manager state.",
            "status": step_status(not missing_course_items and course_valid, active=all_clean),
            "note": ("Course workspace is complete and state.yaml is VALID" if not missing_course_items and course_valid else ("Missing: " + ", ".join(missing_course_items) if missing_course_items else "state.yaml needs attention")),
            "action": "prepare-course" if missing_course_items else "",
        },
        {
            "number": "G0",
            "title": "Establish source and alignment",
            "detail": "Accept an independently verified attestation, or explicitly record a human decision to proceed without one. Never hand-set PASS.",
            "status": step_status(g["G0_ALIGNMENT"]["status"] in {"PASS", "SKIPPED"}, active=g["G0_ALIGNMENT"]["status"] == "READY", blocked=g["G0_ALIGNMENT"]["status"] == "BLOCKED"),
            "note": f"G0 Alignment: {g['G0_ALIGNMENT']['status']}",
            "action": "",
        },
        {
            "number": "G1a",
            "title": "Export Observer work",
            "detail": f"Jason assists the human; export the completed Observer progress into {folder.name}/observation/.",
            "status": step_status(bool(observer_files), active=g["G0_ALIGNMENT"]["status"] in {"PASS", "SKIPPED"} and not observer_files, blocked=g["G0_ALIGNMENT"]["status"] not in {"PASS", "SKIPPED"}),
            "note": f"{len(observer_files)} file(s) found" if observer_files else "Waiting for the Observer export",
            "action": "open-observation",
        },
        {
            "number": "G1b",
            "title": "Import and record the Compiler skeleton",
            "detail": f"Copy Generate output into {folder.name}/skeleton/ and bind it to the Observer, source, alignment, and Compiler version.",
            "status": step_status(bool(skeleton_files) and g["G1_COMPILE"]["status"] == "PASS", active=bool(observer_files) or bool(skeleton_files), blocked=g["G1_COMPILE"]["status"] == "BLOCKED" and not skeleton_files),
            "note": (f"{skeleton_files[0].name} is recorded with provenance" if g["G1_COMPILE"]["status"] == "PASS" else (f"{skeleton_files[0].name} is staged; Gate 0 must pass before it can be recorded" if skeleton_files else "No skeleton imported yet")),
            "action": "record-skeleton" if skeleton_files and g["G1_COMPILE"]["status"] == "READY" else "import-skeleton",
        },
        {
            "number": "G2",
            "title": "Check the skeleton with two witnesses",
            "detail": "Run the blocking H4 packaging check and the evidence-only manual checks, then read the surface yourself.",
            "status": step_status(g["G2_MECHANICAL"]["status"] == "PASS", active=g["G2_MECHANICAL"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"}, blocked=g["G2_MECHANICAL"]["status"] == "BLOCKED"),
            "note": ("File check passed. Next: run /estructura." if skeleton_checked else "Ready to check."),
            "action": "check-skeleton" if skeleton_files and g["G1_COMPILE"]["status"] == "PASS" else "",
        },
        {
            "number": "G3–4",
            "title": "Record textual and specialist review",
            "detail": "Until Verificador and Specialist agents exist, read the work and record exactly what was checked. Skip G4 only when no specialist question arose.",
            "status": step_status(g["G3_TEXTUAL"]["status"] == "PASS" and g["G4_SPECIALISTS"]["status"] in {"PASS", "SKIPPED"}, active=g["G3_TEXTUAL"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"} or g["G4_SPECIALISTS"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"}, blocked=g["G3_TEXTUAL"]["status"] == "BLOCKED"),
            "note": f"G3 Textual: {g['G3_TEXTUAL']['status']} · G4 Specialists: {g['G4_SPECIALISTS']['status']}",
            "action": "",
        },
        {
            "number": "G5",
            "title": "/estructura — clauses, blocks, then structure",
            "detail": "Arquitecto gives the Step 0 verdict, proposes the block inventory for your approval, then builds H1/H2/H3, telos, and title from blocks.md.",
            "status": step_status(g["G5_ARCHITECTURE"]["status"] == "PASS", active=g["G5_ARCHITECTURE"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"}, blocked=g["G5_ARCHITECTURE"]["status"] == "BLOCKED"),
            "note": ("blocks.md matches its last successful verification" if blocks_verified else ("blocks.md is ready to verify" if blocks_started else f"G5 Architecture: {g['G5_ARCHITECTURE']['status']}")),
            "action": "verify-blocks" if blocks_started else "open-blocks",
        },
        {
            "number": "G6",
            "title": "Build context quotes, then write with Escriba",
            "detail": "Generate Scripture quotes from the LBF, then run /manual one H3 per pass. The introduction must name and count the book's series.",
            "status": step_status(g["G6_WRITING"]["status"] == "PASS", active=g["G6_WRITING"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"}, blocked=g["G6_WRITING"]["status"] == "BLOCKED"),
            "note": f"{quote_count} context quote line(s) found · G6 Writing: {g['G6_WRITING']['status']}",
            "action": "build-quotes" if manuals and quote_count == 0 else ("open-manual" if manuals else ""),
        },
        {
            "number": "G7",
            "title": "Editor · Corrector · mechanical speaker/hearing",
            "detail": "Agents edit; PASS only when verify-g7 exits 0. On FAIL: mechanical Corrector (correct-g7), then agent Corrector for remaining CRITICAL, then re-verify.",
            "status": step_status(g["G7_EDITORIAL"]["status"] == "PASS", active=g["G7_EDITORIAL"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED", "FAIL", "STALE"}, blocked=g["G7_EDITORIAL"]["status"] == "BLOCKED"),
            "note": f"G7 Editorial: {g['G7_EDITORIAL']['status']}",
            "action": (
                "run-g7-correct" if manuals and g["G7_EDITORIAL"]["status"] == "FAIL"
                else ("run-g7-check" if manuals and g["G7_EDITORIAL"]["status"] != "BLOCKED" else "")
            ),
        },
        {
            "number": "G8",
            "title": "Mechanical final stream (auto PASS/FAIL)",
            "detail": "verify-g8-final.py records PASS or FAIL. Human sufficiency reading is G9 only.",
            "status": step_status(g["G8_FINAL_VERIFY"]["status"] == "PASS", active=g["G8_FINAL_VERIFY"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED", "FAIL", "STALE"}, blocked=g["G8_FINAL_VERIFY"]["status"] == "BLOCKED"),
            "note": f"G8 Final verification: {g['G8_FINAL_VERIFY']['status']}",
            "action": "run-final-checks" if manuals and g["G8_FINAL_VERIFY"]["status"] != "BLOCKED" else "",
        },
        {
            "number": "G9–10",
            "title": "Human review and release",
            "detail": "Only after G7 and G8 mechanical PASS: sufficiency reading, release manifest, named human approval. Default remains NOT RELEASED.",
            "status": step_status(g["G10_RELEASE"]["status"] == "PASS" and state["workflow"]["release_status"] == "RELEASED", active=g["G9_HUMAN_REVIEW"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"} or g["G10_RELEASE"]["status"] in {"READY", "RUNNING", "REVIEW_REQUIRED"}, blocked=g["G9_HUMAN_REVIEW"]["status"] == "BLOCKED"),
            "note": f"G9 Human: {g['G9_HUMAN_REVIEW']['status']} · G10 Release: {g['G10_RELEASE']['status']} · {state['workflow']['release_status']}",
            "action": "",
        },
    ]


def gate_actions(state: dict):
    gate = compute_current_gate(state)
    status = state["gates"][gate]["status"]
    if gate == "G0_ALIGNMENT" and status == "READY":
        return [{"status": "SKIPPED", "label": "Proceed without attestation"}]
    if gate == "G1_COMPILE":
        return []
    # G7/G8: humans never click PASS — only run mechanical verify.
    if gate in MECHANICAL_PASS_GATES:
        return []
    labels = {
        "RUNNING": "Start this gate",
        "REVIEW_REQUIRED": "Send for review",
        "PASS": "Approve and pass",
        "FAIL": "Mark as failed",
        "BLOCKED": "Block this gate",
        "SKIPPED": "Skip with recorded reason",
    }
    allowed = []
    for target in VALID_TRANSITIONS.get(status, set()):
        if target in labels and target != "BLOCKED":
            allowed.append({"status": target, "label": labels[target]})
    if status == "READY" and gate == "G4_SPECIALISTS":
        allowed.append({"status": "SKIPPED", "label": labels["SKIPPED"]})
    if "BLOCKED" in VALID_TRANSITIONS.get(status, set()):
        allowed.append({"status": "BLOCKED", "label": labels["BLOCKED"]})
    return allowed



def artifact_milestones(folder: Path, state: dict | None = None) -> dict:
    architecture = files_in(folder / "architecture", {".md", ".markdown", ".txt"})
    skeleton = files_in(folder / "skeleton", {".md", ".markdown", ".txt"})

    step0_candidates = [path for path in architecture + skeleton if "step0" in path.stem.lower()]
    step0_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    step0 = step0_candidates[0] if step0_candidates else None
    step0_status = "missing"
    if step0:
        text = step0.read_text(encoding="utf-8", errors="ignore")
        if "**Puedo continuar" in text:
            step0_status = "clear"
        elif "**Bloqueado" in text:
            step0_status = "corrections"

    block_proposals = [
        path for path in architecture
        if "block" in path.stem.lower() and ("propuesta" in path.stem.lower() or "proposal" in path.stem.lower())
    ]
    block_proposal = block_proposals[0] if block_proposals else None

    blocks = folder / "blocks.md"
    blocks_approved = blocks.exists() and "NOT STARTED" not in blocks.read_text(encoding="utf-8", errors="ignore")

    structure_proposals = [
        path for path in architecture
        if "outline" in path.stem.lower() or "estructura" in path.stem.lower()
    ]
    structure_proposal = structure_proposals[0] if structure_proposals else None
    evidence = (state or {}).get("manager", {}).get("evidence", {})
    structure_approved = bool(
        structure_proposal
        and evidence.get("structure_approved_checksum") == checksum(structure_proposal)
    )

    manuals = files_in(folder / "manual", {".md", ".markdown"})
    context_quote_count = 0
    if manuals:
        manual_text = manuals[0].read_text(encoding="utf-8", errors="ignore")
        context_quote_count = sum(
            1 for section in manual_text.split("\n## ")[1:] if "\n= " in section
        )
    context_quotes_built = bool(
        context_quote_count and evidence.get("context_quotes_built_at")
    )
    return {
        "step0Status": step0_status,
        "step0File": relative(step0) if step0 else "",
        "blockProposalFile": relative(block_proposal) if block_proposal else "",
        "blocksApproved": blocks_approved,
        "structureProposalFile": relative(structure_proposal) if structure_proposal else "",
        "structureApproved": structure_approved,
        "contextQuotesBuilt": context_quotes_built,
        "contextQuoteCount": context_quote_count,
        "manualFile": relative(manuals[0]) if manuals else "",
    }
def dashboard(course: str):
    folder, _, state = state_for(course)
    repos = repo_snapshot()
    errors = validate_state(state)
    current = compute_current_gate(state)
    return {
        "course": {"id": state["project"]["id"], "title": state["project"]["title"], "folder": folder.name},
        "projectStatus": state["project"]["status"],
        "releaseStatus": state["workflow"]["release_status"],
        "currentGate": current,
        "currentGateLabel": GATE_LABELS[current],
        "nextAction": next_action(state),
        "artifactCurrent": bool(state["artifact"].get("current")),
        "artifactPath": state["artifact"].get("path") or "No skeleton recorded",
        "blockers": open_blockers(state),
        "validationErrors": errors,
        "repos": repos,
        "milestones": artifact_milestones(folder, state),
        "steps": build_steps(folder, state, repos),
        "gates": [{"id": gate, "label": GATE_LABELS[gate], "status": state["gates"][gate]["status"]} for gate in GATES],
        "gateActions": gate_actions(state),
        "provenance": list(reversed(state.get("provenance", [])[-8:])),
        "knownGaps": [
            {"gap": "Compiler exports outside the course", "effect": "One manual import per book until the Compiler changes."},
            {"gap": "Verificador and Specialists have no agent", "effect": "G3 and G4 are read and recorded by hand."},
            {"gap": "Cursor symlink discovery is unverified", "effect": "If @arquitecto fails, fall back to copies plus a sync step."},
            {"gap": "Revision strings are labels", "effect": "SHA-256 checksums are the ground truth."},
            {"gap": "Step 1, blocks.md, and = quotes are untested", "effect": "Apocalipsis is the first real exercise; record what breaks."},
        ],
    }


def course_list():
    courses = []
    if COURSES.is_dir():
        for folder in sorted(COURSES.iterdir()):
            state_path = folder / "state.yaml"
            if folder.is_dir() and state_path.exists():
                state = load_yaml(state_path)
                courses.append({"id": state.get("project", {}).get("id", folder.name), "title": state.get("project", {}).get("title", folder.name), "folder": folder.name})
    return courses


def safe_upload(field, target_dir: Path, allowed_suffixes: set[str]) -> Path:
    if not getattr(field, "filename", ""):
        raise ValueError("Choose a file first.")
    name = Path(field.filename).name
    if Path(name).suffix.lower() not in allowed_suffixes:
        raise ValueError(f"Unsupported file type: {Path(name).suffix or 'none'}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / name
    data = field.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise ValueError("The selected file is larger than 20 MB.")
    target.write_bytes(data)
    return target


class ManagerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def log_message(self, format, *args):
        return

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_json(self, value, status=200):
        data = json_bytes(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD:
            raise ValueError("Request is too large.")
        return json.loads(self.rfile.read(length) or b"{}")

    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD + 1024 * 1024:
            raise ValueError("Upload is too large.")
        return cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
        )

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/courses":
                return self.send_json({"courses": course_list()})
            if parsed.path == "/api/dashboard":
                course = parse_qs(parsed.query).get("course", [""])[0]
                return self.send_json(dashboard(course))
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 400)
        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/confirm-cursor":
                body = self.read_json()
                with STATE_LOCK:
                    _, state_path, state = state_for(body["course"])
                    state.setdefault("manager", {}).setdefault("preflight", {}).update({"cursor_agents_verified": True, "verified_at": now_iso()})
                    record_event(state, "human", "Cursor agent discovery confirmed", "", "@arquitecto appeared in Cursor")
                    save_yaml(state_path, state)
                return self.send_json({"message": "Cursor agent discovery confirmed."})

            if self.path == "/api/prepare-course":
                body = self.read_json()
                folder, _, _ = state_for(body["course"])
                for name in PIPELINE_DIRS:
                    (folder / name).mkdir(parents=True, exist_ok=True)
                return self.send_json({"message": "The six pipeline folders are ready."})

            if self.path == "/api/import-observer":
                form = self.read_form()
                course = form.getfirst("course", "")
                folder, state_path, state = state_for(course)
                target = safe_upload(form["file"], folder / "observation", {".json"})
                if state["gates"]["G1_COMPILE"]["status"] == "PASS":
                    state["gates"]["G1_COMPILE"].update({"input_progress_path": relative(target), "input_progress_checksum": checksum(target)})
                    record_event(state, "human", "Observer progress attached", "G1_COMPILE", relative(target))
                    save_yaml(state_path, state)
                return self.send_json({"message": f"Imported {target.name} into {folder.name}/observation/."})

            if self.path == "/api/import-compiler":
                form = self.read_form()
                course = form.getfirst("course", "")
                with STATE_LOCK:
                    folder, state_path, state = state_for(course)
                    progress = None
                    if "observer" in form and getattr(form["observer"], "filename", ""):
                        progress = safe_upload(form["observer"], folder / "observation", {".json"})
                    target = safe_upload(form["skeleton"], folder / "skeleton", {".md", ".markdown", ".txt"})
                    if state["gates"]["G0_ALIGNMENT"]["status"] == "READY":
                        waive_gate0(
                            state,
                            REPOS,
                            "manager",
                            "Manual production inherited the existing source files; alignment work is upstream of this stage.",
                        )
                    version = form.getfirst("compiler_version", "").strip() or "cgv-reader unrecorded"
                    record_compile(
                        state,
                        REPOS,
                        relative(target),
                        relative(progress) if progress else None,
                        version,
                        actor="human",
                    )
                    save_yaml(state_path, state)
                message = f"Imported and recorded {target.name}."
                if progress:
                    message += f" Observer progress {progress.name} is attached."
                return self.send_json({"message": message})

            if self.path == "/api/import-skeleton":
                form = self.read_form()
                course = form.getfirst("course", "")
                with STATE_LOCK:
                    folder, state_path, state = state_for(course)
                    target = safe_upload(form["file"], folder / "skeleton", {".md", ".markdown", ".txt"})
                    message = f"Imported {target.name} into {folder.name}/skeleton/."
                    if state["gates"]["G1_COMPILE"]["status"] == "READY":
                        progress = files_in(folder / "observation", {".json"})
                        version = form.getfirst("compiler_version", "").strip()
                        if progress and version:
                            record_compile(state, REPOS, relative(target), relative(progress[0]), version, actor="human")
                            save_yaml(state_path, state)
                            message += " Observer and Compiler provenance recorded; G1 passed."
                        else:
                            message += " It is staged; Observer progress and a Compiler version are required to record G1."
                return self.send_json({"message": message})

            if self.path == "/api/record-skeleton":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    skeletons = files_in(folder / "skeleton", {".md", ".markdown", ".txt"})
                    if not skeletons:
                        raise ValueError("No staged skeleton was found.")
                    progress = files_in(folder / "observation", {".json"})
                    version = str(body.get("compilerVersion", "")).strip()
                    if not version:
                        raise ValueError("Enter the Compiler version before recording G1.")
                    if state["gates"]["G0_ALIGNMENT"]["status"] == "READY":
                        waive_gate0(
                            state,
                            REPOS,
                            "manager",
                            "Manual production inherited the existing source files; alignment work is upstream of this stage.",
                        )
                    record_compile(state, REPOS, relative(skeletons[0]), relative(progress[0]) if progress else None, version, actor="human")
                    save_yaml(state_path, state)
                return self.send_json({"message": f"Recorded {skeletons[0].name}; G1 passed."})

            if self.path == "/api/accept-gate0":
                form = self.read_form()
                course = form.getfirst("course", "")
                with STATE_LOCK:
                    folder, state_path, state = state_for(course)
                    target = safe_upload(form["file"], folder / "attestations", {".yaml", ".yml"})
                    accept_gate0(state, load_yaml(target), relative(target), actor="human", base=REPOS)
                    save_yaml(state_path, state)
                return self.send_json({"message": "Gate 0 attestation accepted and G1 is ready."})

            if self.path == "/api/transition":
                body = self.read_json()
                with STATE_LOCK:
                    _, state_path, state = state_for(body["course"])
                    gate = compute_current_gate(state)
                    notes = str(body.get("notes", "")).strip()
                    if gate == "G0_ALIGNMENT" and body["status"] == "PASS":
                        raise ValueError("Gate 0 cannot be hand-set to PASS. Import an attestation.")
                    if gate == "G1_COMPILE":
                        raise ValueError("G1 must be completed by recording a Compiler skeleton.")
                    if gate in MECHANICAL_PASS_GATES and body["status"] == "PASS":
                        raise ValueError(
                            f"{gate} PASS is recorded only by mechanical verify "
                            "(run-g7-check / run-final-checks). Do not hand-approve."
                        )
                    if body["status"] in {"PASS", "FAIL", "REVIEW_REQUIRED", "BLOCKED"} and not notes:
                        raise ValueError("Add a short note explaining this decision.")
                    if gate == "G0_ALIGNMENT" and body["status"] == "SKIPPED":
                        waive_gate0(state, REPOS, "human", notes)
                    else:
                        record_gate_status(state, gate, body["status"], "human", notes)
                    save_yaml(state_path, state)
                return self.send_json({"message": f"{gate} is now {body['status']}."})

            if self.path == "/api/run-g7-check":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    manual = preferred_manual(folder)
                    if not manual:
                        raise ValueError("No manual Markdown file was found.")
                    reports = folder / "reports"
                    reports.mkdir(parents=True, exist_ok=True)
                    out = reports / "SPEAKER_HEARING_REPORT.md"
                    run = subprocess.run(
                        [
                            "/usr/bin/python3",
                            str(CGV / "scripts" / "verify-g7-editorial.py"),
                            "--manual",
                            str(manual),
                            "--out",
                            str(out),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        check=False,
                    )
                    output = (run.stdout + run.stderr).strip()
                    passed = run.returncode == 0
                    dig = checksum(manual)
                    apply_mechanical_gate_result(
                        state,
                        "G7_EDITORIAL",
                        passed,
                        manual_checksum=dig,
                        notes=output[-500:] or ("G7 mechanical PASS" if passed else "G7 mechanical FAIL"),
                        actor="verify-g7-editorial",
                    )
                    save_yaml(state_path, state)
                if not passed:
                    return self.send_json(
                        {"error": output or "G7 speaker/hearing verification failed.", "gate": "G7_EDITORIAL", "status": "FAIL"},
                        400,
                    )
                return self.send_json({"message": "G7_EDITORIAL PASS — speaker/hearing mechanical verify exited 0.", "gate": "G7_EDITORIAL", "status": "PASS"})

            if self.path == "/api/run-g7-correct":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    manual = preferred_manual(folder)
                    if not manual:
                        raise ValueError("No manual Markdown file was found.")
                    run = subprocess.run(
                        [
                            "/usr/bin/python3",
                            str(CGV / "scripts" / "correct-g7-surface.py"),
                            "--manual",
                            str(manual),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        check=False,
                    )
                    output = (run.stdout + run.stderr).strip()
                    if run.returncode not in (0, 1):
                        raise ValueError(output or "correct-g7-surface failed")
                    record_event(
                        state,
                        "correct-g7-surface",
                        "mechanical Corrector applied on gate surface",
                        "G7_EDITORIAL",
                        output[-400:],
                    )
                    st = state["gates"]["G7_EDITORIAL"]["status"]
                    if st in {"FAIL", "STALE"}:
                        transition_gate(
                            state, "G7_EDITORIAL", "READY", "correct-g7-surface",
                            "Re-open after mechanical Corrector.",
                        )
                    # Chain verify
                    reports = folder / "reports"
                    reports.mkdir(parents=True, exist_ok=True)
                    out = reports / "SPEAKER_HEARING_REPORT.md"
                    vrun = subprocess.run(
                        [
                            "/usr/bin/python3",
                            str(CGV / "scripts" / "verify-g7-editorial.py"),
                            "--manual",
                            str(manual),
                            "--out",
                            str(out),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=180,
                        check=False,
                    )
                    vout = (vrun.stdout + vrun.stderr).strip()
                    passed = vrun.returncode == 0
                    apply_mechanical_gate_result(
                        state,
                        "G7_EDITORIAL",
                        passed,
                        manual_checksum=checksum(manual),
                        notes=vout[-500:] or ("PASS" if passed else "FAIL after Corrector"),
                        actor="verify-g7-editorial",
                    )
                    save_yaml(state_path, state)
                msg = output + "\n\n" + vout
                if not passed:
                    return self.send_json(
                        {
                            "error": msg or "G7 still FAIL after mechanical Corrector — run @corrector for remaining CRITICAL.",
                            "gate": "G7_EDITORIAL",
                            "status": "FAIL",
                        },
                        400,
                    )
                return self.send_json({
                    "message": "Mechanical Corrector applied; G7_EDITORIAL PASS.",
                    "gate": "G7_EDITORIAL",
                    "status": "PASS",
                })

            if self.path == "/api/run-final-checks":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    manual = preferred_manual(folder)
                    if not manual:
                        raise ValueError("No manual Markdown file was found.")
                    source = Path(state["source"]["path"])
                    source = source if source.is_absolute() else REPOS / source
                    blocks = folder / "blocks.md"
                    cmd = [
                        "/usr/bin/python3",
                        str(CGV / "scripts" / "verify-g8-final.py"),
                        "--manual",
                        str(manual),
                        "--book",
                        state["project"]["id"],
                        "--reports-dir",
                        str(folder / "reports"),
                    ]
                    if source.is_file():
                        cmd.extend(["--lbf", str(source)])
                    if blocks.is_file():
                        cmd.extend(["--blocks", str(blocks)])
                    run = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
                    output = (run.stdout + run.stderr).strip()
                    if run.returncode == 0:
                        drift = input_drift(state, REPOS)
                        if drift:
                            raise ValueError(
                                "Provenance drift found: "
                                + "; ".join(f"{kind}: {detail.splitlines()[0]}" for kind, detail in drift)
                            )
                    passed = run.returncode == 0
                    dig = checksum(manual)
                    apply_mechanical_gate_result(
                        state,
                        "G8_FINAL_VERIFY",
                        passed,
                        manual_checksum=dig,
                        notes=output[-500:] or ("G8 mechanical PASS" if passed else "G8 mechanical FAIL"),
                        actor="verify-g8-final",
                    )
                    state.setdefault("manager", {}).setdefault("evidence", {}).update({
                        "final_verify_checksum": dig,
                        "final_verify_at": now_iso(),
                        "final_verify_outputs": [output],
                    })
                    save_yaml(state_path, state)
                if not passed:
                    return self.send_json(
                        {"error": output or "G8 mechanical stream failed.", "gate": "G8_FINAL_VERIFY", "status": "FAIL"},
                        400,
                    )
                return self.send_json({
                    "message": "G8_FINAL_VERIFY PASS — mechanical stream exited 0. Human sufficiency reading is G9.",
                    "gate": "G8_FINAL_VERIFY",
                    "status": "PASS",
                })

            if self.path == "/api/open":
                body = self.read_json()
                folder, _, state = state_for(body["course"])
                milestones = artifact_milestones(folder, state)
                targets = {
                    "course": folder,
                    "observation": folder / "observation",
                    "blocks": folder / "blocks.md",
                    "manual": folder / "manual",
                    "step0": REPOS / milestones["step0File"] if milestones["step0File"] else folder / "architecture",
                    "block-proposal": REPOS / milestones["blockProposalFile"] if milestones["blockProposalFile"] else folder / "architecture",
                    "structure-proposal": REPOS / milestones["structureProposalFile"] if milestones["structureProposalFile"] else folder / "architecture",
                }
                target = targets.get(body.get("target"), folder)
                if not target.exists() and target.suffix == "":
                    target.mkdir(parents=True, exist_ok=True)
                subprocess.Popen(["open", str(target)])
                return self.send_json({"message": f"Opened {target.name}."})

            if self.path == "/api/approve-structure":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    milestones = artifact_milestones(folder, state)
                    if not milestones["structureProposalFile"]:
                        raise ValueError("No structure proposal was found.")
                    proposal = REPOS / milestones["structureProposalFile"]
                    state.setdefault("manager", {}).setdefault("evidence", {}).update({
                        "structure_approved_checksum": checksum(proposal),
                        "structure_approved_at": now_iso(),
                    })
                    record_event(
                        state,
                        "human",
                        "structure approved",
                        "G5_ARCHITECTURE",
                        f"Approved {relative(proposal)}. Next: build context quotes.",
                    )
                    save_yaml(state_path, state)
                return self.send_json({"message": "Structure approved. Next: build context quotes."})

            if self.path == "/api/verify-blocks":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    blocks = folder / "blocks.md"
                    source = Path(state["source"]["path"])
                    source = source if source.is_absolute() else REPOS / source
                    script = CGV / "scripts" / "verify-blocks.py"
                    run = subprocess.run(["/usr/bin/python3", str(script), "--blocks", str(blocks), "--lbf", str(source)], capture_output=True, text=True, timeout=120, check=False)
                    output = (run.stdout + run.stderr).strip()
                    if run.returncode:
                        raise ValueError(output or "Block verification failed.")
                    state.setdefault("manager", {}).setdefault("evidence", {}).update({"blocks_checksum": checksum(blocks), "blocks_verified_at": now_iso(), "blocks_verifier_output": output})
                    record_event(state, "manager", "blocks.md verified", "G5_ARCHITECTURE", output[-300:])
                    save_yaml(state_path, state)
                return self.send_json({"message": output or "blocks.md passed verification."})

            if self.path == "/api/check-skeleton":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    skeletons = files_in(folder / "skeleton", {".md", ".markdown", ".txt"})
                    if not skeletons:
                        raise ValueError("No skeleton was found.")
                    source = Path(state["source"]["path"])
                    source = source if source.is_absolute() else REPOS / source
                    packaging = CGV / "scripts" / "verify-skeleton-h4-packaging.py"
                    checks = CGV / "scripts" / "run-manual-checks.py"
                    first = subprocess.run(["/usr/bin/python3", str(packaging), "--manual", str(skeletons[0]), "--lbf", str(source)], capture_output=True, text=True, timeout=120, check=False)
                    first_output = (first.stdout + first.stderr).strip()
                    if first.returncode:
                        raise ValueError(first_output or "The blocking H4 packaging check failed.")
                    second = subprocess.run(["/usr/bin/python3", str(checks), "--manual", str(skeletons[0]), "--lbf", str(source), "--book", state["project"]["id"]], capture_output=True, text=True, timeout=120, check=False)
                    second_output = (second.stdout + second.stderr).strip()
                    state.setdefault("manager", {}).setdefault("evidence", {}).update({
                        "skeleton_checks_checksum": checksum(skeletons[0]),
                        "skeleton_checks_at": now_iso(),
                        "skeleton_packaging_output": first_output,
                        "skeleton_manual_checks_output": second_output,
                    })
                    record_event(state, "python-checker", "skeleton checks recorded", "G2_MECHANICAL", "Blocking packaging check passed; manual checks emitted evidence. Human surface reading remains required.")
                    save_yaml(state_path, state)
                return self.send_json({"message": "The blocking packaging check passed. Manual-check evidence was recorded; now read the skeleton yourself before deciding G2."})

            if self.path == "/api/build-quotes":
                body = self.read_json()
                with STATE_LOCK:
                    folder, state_path, state = state_for(body["course"])
                    manual = preferred_manual(folder) or (files_in(folder / "manual", {".md", ".markdown"}) or [None])[0]
                    if not manual:
                        raise ValueError("No manual Markdown file was found.")
                    source = Path(state["source"]["path"])
                    source = source if source.is_absolute() else REPOS / source
                    script = CGV / "scripts" / "build-context-quotes.py"
                    run = subprocess.run(["/usr/bin/python3", str(script), "--manual", str(manual), "--lbf", str(source), "--write"], capture_output=True, text=True, timeout=120, check=False)
                    output = (run.stdout + run.stderr).strip()
                    if run.returncode:
                        raise ValueError(output or "Context quote build failed.")
                    state.setdefault("manager", {}).setdefault("evidence", {}).update({"context_quotes_checksum": checksum(manual), "context_quotes_built_at": now_iso()})
                    record_event(state, "manager", "context quotes built", "G5_ARCHITECTURE", output[-300:])
                    save_yaml(state_path, state)
                return self.send_json({"message": output or "Context quotes were written."})

            return self.send_json({"error": "Unknown action."}, 404)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 400)


def port_is_open() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.25)
        return probe.connect_ex((HOST, PORT)) == 0


def main():
    url = f"http://{HOST}:{PORT}/"
    if port_is_open():
        webbrowser.open(url)
        return
    server = ThreadingHTTPServer((HOST, PORT), ManagerHandler)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
