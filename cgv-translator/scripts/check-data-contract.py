#!/usr/bin/env python3
"""
cgv-translator boundary check.

Derived from DATA_CONTRACT.md (normative) and
Biblia-LBF/docs/architecture/CGV_DATA_ARCHITECTURE.md.

cgv-translator is the human editing and approval application for the LBF project.
It provides workflows over Biblia-LBF; it does not own an independent translation
or alignment corpus. It rejects:

  * direct writes to cgv-data;
  * independent canonical corpus files kept here;
  * approval records without exact revision binding;
  * automatic approval of machine-generated work.

Clearly labelled, minimal test fixtures are allowed.

READ-ONLY, and dependency-free (standard library only, so CI needs no install
step). `--emit-baseline` prints JSON to stdout; it writes no file.

Exit codes:
  0  no new violations
  1  new violations found (not present in the baseline)
  2  usage or internal error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_NAME = "cgv-translator"
BASELINE_FILENAME = ".data-contract-baseline.json"
MAX_FIXTURE_BYTES = 64 * 1024

FINDINGS: list[dict] = []
NOTES: list[str] = []


def add(rule: str, path: str, message: str, key: str = "") -> None:
    FINDINGS.append(
        {"id": f"{rule}|{path}|{key}", "rule": rule, "path": path, "key": key, "message": message}
    )


def note(message: str) -> None:
    NOTES.append(message)


SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", "public"}


def walk(repo: Path):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name == ".DS_Store":
                continue
            yield (Path(dirpath) / name).relative_to(repo)


def tracked_files(repo: Path) -> list[Path]:
    """Files as CI sees them: git-tracked only, relative to this directory."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        result = None
    if result is None or result.returncode != 0:
        note("Not a git checkout; falling back to a filesystem walk.")
        return list(walk(repo))
    return [
        Path(entry)
        for entry in result.stdout.split("\0")
        if entry and not entry.endswith(".DS_Store")
    ]


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return exc


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

FIXTURE = re.compile(r"(^|/)(fixtures?|__fixtures__|test|tests|test_py)(/|$)", re.I)

# A hand-maintained corpus of translation or alignment truth. Canonical input is
# a named Biblia-LBF branch and commit; it is not copied in here.
INDEPENDENT_CORPUS = re.compile(
    r"""(?x)
    ^translations/
    | -phrases\.json$
    | -reverse-links(\.[a-z0-9-]+)?\.json$
    | -spine\.json$
    | \.alignment\.json$
    | \.lbf\.md$
    """,
    re.I,
)

CGV_DATA_WRITE = re.compile(
    r"""(?x)
    (open\s*\(|write_text|write_bytes|copyfile|copytree|copy2|shutil\.move|
     writeFileSync|writeFile\s*\(|outputFile|createWriteStream)
    [^\n]{0,200} cgv-data
    |
    cgv-data [^\n]{0,200}
    (write_text|write_bytes|writeFileSync|createWriteStream)
    |
    git\s+-C\s+\S*cgv-data\s+(commit|push|add)
    """
)

# Approval markers, and the evidence that an approval is bound to exact content.
APPROVAL_MARKER = re.compile(
    r"""(?xm)
    ^\s*-?\s*(decision|status|translation|alignment)\s*:\s*["']?APPROVED\b
    | "(decision|status)"\s*:\s*"APPROVED"
    | ^\s*approved\s*:\s*true\s*$
    """,
    re.I,
)
REVISION_BINDING = re.compile(
    r"""(?x)
    \b(TR|ALN|SRC)-[a-z0-9]+-[0-9a-f]{12}\b
    | translationRevision
    | alignmentRevision
    | translation_revision
    | alignment_revision
    | inputRevisionIds
    | baseCommit
    | base_commit
    """,
    re.I,
)
HUMAN_APPROVER = re.compile(
    r"""(?x)
    \bapprovedBy\b | \bapproved_by\b | \bapprover\b | \breviewedBy\b
    | \breviewed_by\b | \bgithubLogin\b | \bgithub_login\b
    """,
    re.I,
)
MACHINE_MARKER = re.compile(
    r"""(?x)
    \baiUsed\s*[:=]\s*true\b | \busesAI\s*[:=]\s*true\b
    | \bmachine[_-]?generated\b | \bmodel\s*[:=]\s*["'](gpt|claude|gemini)
    | \bdeterministic-[a-z0-9-]*v\d
    """,
    re.I,
)
# Code that writes an approved state instead of recording a human decision.
AUTO_APPROVAL_CODE = re.compile(
    r"""(?x)
    (status|decision|state)\s*[:=]\s*["']APPROVED["']
    | \.status\s*=\s*["']APPROVED["']
    | promote[_-]?to[_-]?approved
    | auto[_-]?approve
    """,
    re.I,
)
# Token ids rebuilt from position rather than persisted.
TOKEN_ID_FROM_INDEX = re.compile(
    r"""(?x)
    (token_?Id|tokenID)\s*[:=][^\n]{0,80}
    (enumerate\(|\bidx\b|\bindex\b|\bi\s*\+\s*1\b|\{i[:}]|position)
    """,
    re.I,
)

APPROVAL_LIKE_PATH = re.compile(
    r"(approval|approve|review|verdict|decision|gate|queue|verification)", re.I
)
DATA_SUFFIXES = {".yaml", ".yml", ".json"}
CODE_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".tsx", ".sh"}


def is_fixture(rel: Path) -> bool:
    return FIXTURE.search(rel.as_posix()) is not None


def check(repo: Path) -> None:
    for rel in tracked_files(repo):
        posix = rel.as_posix()
        if posix == "scripts/check-data-contract.py" or posix.startswith(".github/"):
            continue

        fixture = is_fixture(rel)
        path = repo / rel

        if INDEPENDENT_CORPUS.search(posix):
            if fixture:
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                if size > MAX_FIXTURE_BYTES:
                    add(
                        "OVERSIZED_FIXTURE",
                        posix,
                        f"Fixture is {size // 1024} KiB. A fixture must be minimal "
                        f"(<= {MAX_FIXTURE_BYTES // 1024} KiB); at this size it is a "
                        "corpus copy wearing a fixture label.",
                    )
            else:
                add(
                    "INDEPENDENT_CORPUS",
                    posix,
                    "This looks like canonical translation or alignment truth kept "
                    "here. Canonical input is a named Biblia-LBF branch and commit; "
                    "this application does not own a corpus.",
                )

        suffix = rel.suffix.lower()
        if suffix in CODE_SUFFIXES:
            text = read_text(path)
            if CGV_DATA_WRITE.search(text):
                add(
                    "CGV_DATA_WRITE",
                    posix,
                    "This file appears to write into cgv-data. Publication begins "
                    "only after approvals are merged into Biblia-LBF and pass its "
                    "export gate.",
                )
            if AUTO_APPROVAL_CODE.search(text) and not HUMAN_APPROVER.search(text):
                add(
                    "AUTO_APPROVAL",
                    posix,
                    "This code sets an approved state without recording an "
                    "authenticated human approver. Machine output must stay draft "
                    "until a human approves it.",
                )
            if TOKEN_ID_FROM_INDEX.search(text):
                add(
                    "TOKEN_ID_FROM_POSITION",
                    posix,
                    "Token ids appear to be derived from array position. Token ids "
                    "are persisted and never silently regenerated.",
                )

        if suffix in DATA_SUFFIXES and not fixture:
            text = read_text(path)
            if not APPROVAL_MARKER.search(text):
                continue
            if not REVISION_BINDING.search(text):
                add(
                    "APPROVAL_WITHOUT_REVISION_BINDING",
                    posix,
                    "Record carries approval decisions but binds no exact translation "
                    "or alignment revision. Approval on display text alone is not "
                    "approval.",
                )
            if not HUMAN_APPROVER.search(text):
                add(
                    "APPROVAL_WITHOUT_APPROVER",
                    posix,
                    "Record carries approval decisions but names no authenticated "
                    "approver.",
                )
            if MACHINE_MARKER.search(text) and not HUMAN_APPROVER.search(text):
                add(
                    "MACHINE_APPROVED",
                    posix,
                    "Machine-generated content is marked approved with no human "
                    "approver. Machine suggestions stay distinguishable from human "
                    "decisions.",
                )

    if not any(
        (repo / candidate).exists()
        for candidate in ("src/adapter", "src/repository-adapter", "adapter")
    ):
        add(
            "NO_REPOSITORY_ADAPTER",
            "src/adapter",
            "No repository adapter is present. Canonical reads and writes must go "
            "through one defined Biblia-LBF adapter rather than ad-hoc file access.",
            key="missing",
        )


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{REPO_NAME} data-contract boundary check")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--baseline", default=None)
    parser.add_argument("--emit-baseline", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2

    check(repo)
    FINDINGS.sort(key=lambda f: (f["rule"], f["path"], f["key"]))

    if args.emit_baseline:
        print(
            json.dumps(
                {
                    "_comment": (
                        "Violations that already existed when the boundary check was "
                        "introduced. CI fails on anything not listed here. Shrink this "
                        "list; never grow it."
                    ),
                    "repository": REPO_NAME,
                    "accepted": [f["id"] for f in FINDINGS],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    baseline_path = Path(args.baseline) if args.baseline else repo / BASELINE_FILENAME
    accepted: set[str] = set()
    if baseline_path.is_file():
        loaded = load_json(baseline_path)
        if isinstance(loaded, dict):
            accepted = set(loaded.get("accepted", []))
        else:
            print(f"error: cannot read baseline {baseline_path}", file=sys.stderr)
            return 2

    new = [f for f in FINDINGS if f["id"] not in accepted]
    fixed = sorted(accepted - {f["id"] for f in FINDINGS})

    if args.json:
        print(
            json.dumps(
                {
                    "repository": REPO_NAME,
                    "new": new,
                    "baselined": len(FINDINGS) - len(new),
                    "fixed": fixed,
                    "notes": NOTES,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 1 if new else 0

    print(f"{REPO_NAME} data-contract boundary check")
    print(f"  findings: {len(FINDINGS)}   baselined: {len(FINDINGS) - len(new)}   new: {len(new)}")
    if fixed:
        print(f"  fixed since baseline: {len(fixed)} (remove these from the baseline)")
    if NOTES:
        print("\nnotes:")
        for entry in NOTES:
            print(f"  - {entry}")
    if new:
        print("\nNEW VIOLATIONS")
        for finding in new:
            print(f"  [{finding['rule']}] {finding['path']}")
            print(f"      {finding['message']}")
        return 1
    print("\nOK - no new violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
