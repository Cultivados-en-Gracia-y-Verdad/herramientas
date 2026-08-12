#!/usr/bin/env python3
"""Guarded patch: require explicit human provenance for investigation approval.

Dry-run by default. Use --apply to modify public/index.html, public/main.js, and
server.js. Every replacement is exact and count-checked so this script refuses to
run against an unexpected local state.

This patch deliberately does not touch investigation content or approval status.
Existing legacy Approved decisions remain as-is, but the UI will stop consuming
an Approved decision as binding policy until human approval provenance is present.
The same Approve button can then record that provenance without changing the
translation decision itself.
"""
from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} exact match(es), found {count}")
    return text.replace(old, new)


def patch_index(text: str) -> str:
    old = '''                <label>\n                  Confidence\n                  <select id="decision-confidence">\n                    <option>High</option>\n                    <option>Medium</option>\n                    <option>Low</option>\n                  </select>\n                </label>\n              </div>\n'''
    new = '''                <label>\n                  Confidence\n                  <select id="decision-confidence">\n                    <option>High</option>\n                    <option>Medium</option>\n                    <option>Low</option>\n                  </select>\n                </label>\n                <label>\n                  Approval Authority\n                  <input id="decision-approval-authority" type="text" readonly />\n                </label>\n                <label>\n                  Approved By\n                  <input id="decision-approved-by" type="text" readonly />\n                </label>\n                <label>\n                  Approved At\n                  <input id="decision-approved-at" type="text" readonly />\n                </label>\n              </div>\n'''
    text = replace_exact(text, old, new, "index decision provenance fields")

    old = '''              <div class="decision-actions">\n                <button id="approve-decision" class="primary-action" type="button">Approve</button>\n              </div>\n'''
    new = '''              <div class="decision-actions">\n                <p>Final investigation approval must be explicitly human initiated and attributed.</p>\n                <button id="approve-decision" class="primary-action" type="button">Approve</button>\n              </div>\n'''
    return replace_exact(text, old, new, "index human approval notice")


def patch_main(text: str) -> str:
    old = '''const decisionReason = document.querySelector("#decision-reason");\nconst approveDecision = document.querySelector("#approve-decision");\n'''
    new = '''const decisionReason = document.querySelector("#decision-reason");\nconst decisionApprovalAuthority = document.querySelector("#decision-approval-authority");\nconst decisionApprovedBy = document.querySelector("#decision-approved-by");\nconst decisionApprovedAt = document.querySelector("#decision-approved-at");\nconst approveDecision = document.querySelector("#approve-decision");\n'''
    text = replace_exact(text, old, new, "main decision provenance selectors")

    old = '''function applyDecisionToTranslation(decision) {\n  if (decision?.status !== "Approved" || !decision.preferredRendering) return;\n'''
    new = '''function decisionHasHumanApproval(decision) {\n  return decision?.status === "Approved"\n    && decision?.approvalAuthority === "human"\n    && Boolean(String(decision?.approvedBy || "").trim())\n    && Boolean(String(decision?.approvedAt || "").trim());\n}\n\nfunction applyDecisionToTranslation(decision) {\n  if (!decisionHasHumanApproval(decision) || !decision.preferredRendering) return;\n'''
    text = replace_exact(text, old, new, "main human approval predicate")

    old = '''      approved: decision.status === "Approved" && Boolean(decision.preferredRendering),\n      rendering: decision.preferredRendering || "",\n      source: decision.status === "Approved"\n        ? `Decision ${decision.version}`\n        : decision.status || "Draft"\n    });\n\n    if (decision?.status === "Approved" && decision.preferredRendering) {\n'''
    new = '''      approved: decisionHasHumanApproval(decision) && Boolean(decision.preferredRendering),\n      rendering: decision.preferredRendering || "",\n      source: decisionHasHumanApproval(decision)\n        ? `Human-approved decision ${decision.version}`\n        : decision.status === "Approved"\n          ? "Approved status missing human provenance"\n          : decision.status || "Draft"\n    });\n\n    if (decisionHasHumanApproval(decision) && decision.preferredRendering) {\n'''
    text = replace_exact(text, old, new, "main approved decision consumption")

    old = '''  decisionConfidence.value = decision.confidence || "Medium";\n  decisionReason.value = decision.reason || "";\n  approveDecision.disabled = decision.status === "Approved";\n  decisionStatus.disabled = decision.status === "Approved" || decision.status === "Superseded";\n}\n'''
    new = '''  decisionConfidence.value = decision.confidence || "Medium";\n  decisionReason.value = decision.reason || "";\n  decisionApprovalAuthority.value = decision.approvalAuthority || "";\n  decisionApprovedBy.value = decision.approvedBy || "";\n  decisionApprovedAt.value = decision.approvedAt || "";\n  const humanApproved = decisionHasHumanApproval(decision);\n  approveDecision.disabled = humanApproved || decision.status === "Superseded";\n  approveDecision.textContent = decision.status === "Approved" && !humanApproved\n    ? "Record Human Approval"\n    : "Approve";\n  decisionStatus.disabled = decision.status === "Approved" || decision.status === "Superseded";\n}\n'''
    text = replace_exact(text, old, new, "main decision form provenance")

    old = '''async function saveDecision(action = "save") {\n  const { decision } = await api(`/api/investigations/${state.investigation}/decision`, {\n    method: "PUT",\n    body: JSON.stringify({ ...readDecisionForm(), action })\n  });\n'''
    new = '''async function saveDecision(action = "save", approval = {}) {\n  const { decision } = await api(`/api/investigations/${state.investigation}/decision`, {\n    method: "PUT",\n    body: JSON.stringify({ ...readDecisionForm(), ...approval, action })\n  });\n'''
    text = replace_exact(text, old, new, "main saveDecision approval payload")

    old = '''  const approvedRendering = decision?.status === "Approved" ? decision.preferredRendering : "";\n'''
    new = '''  const approvedRendering = decisionHasHumanApproval(decision) ? decision.preferredRendering : "";\n'''
    text = replace_exact(text, old, new, "main return-to-translation approval check")

    old = '''    approved: decision?.status === "Approved",\n    rendering: decision?.preferredRendering || "",\n'''
    new = '''    approved: decisionHasHumanApproval(decision),\n    rendering: decision?.preferredRendering || "",\n'''
    text = replace_exact(text, old, new, "main investigation panel approval check")

    old = '''approveDecision.addEventListener("click", () => {\n  void (async () => {\n    await saveDecision("approve");\n    prototypeMessage.textContent = "Decision approved.";\n  })().catch(error => {\n    prototypeMessage.textContent = error.message || "Decision approval error.";\n  });\n});\n'''
    new = '''approveDecision.addEventListener("click", () => {\n  void (async () => {\n    const approver = window.prompt(\n      "Type the human approver's name. This records final human approval for this investigation decision."\n    );\n    if (approver == null) return;\n    const approvedBy = approver.trim();\n    if (!approvedBy) {\n      prototypeMessage.textContent = "Human approver name is required.";\n      return;\n    }\n    await saveDecision("approve", { approvedBy, humanConfirmation: true });\n    prototypeMessage.textContent = "Human approval recorded.";\n  })().catch(error => {\n    prototypeMessage.textContent = error.message || "Decision approval error.";\n  });\n});\n'''
    return replace_exact(text, old, new, "main explicit human approval click")


def patch_server(text: str) -> str:
    old = '''  preferredRendering: "",\n  confidence: "Medium",\n  reason: ""\n};\n'''
    new = '''  preferredRendering: "",\n  confidence: "Medium",\n  reason: "",\n  approvalAuthority: "",\n  approvedBy: "",\n  approvedAt: ""\n};\n'''
    text = replace_exact(text, old, new, "server decision defaults")

    old = '''      preferredRendering: readField("Preferred Rendering"),\n      confidence: readField("Confidence") || "Medium",\n      reason\n'''
    new = '''      preferredRendering: readField("Preferred Rendering"),\n      confidence: readField("Confidence") || "Medium",\n      approvalAuthority: readField("Approval Authority"),\n      approvedBy: readField("Approved By"),\n      approvedAt: readField("Approved At"),\n      reason\n'''
    text = replace_exact(text, old, new, "server parse approval provenance")

    old = '''Preferred Rendering: ${valueOrDash(version.preferredRendering)}\nConfidence: ${valueOrDash(version.confidence)}\n\n### Reason\n'''
    new = '''Preferred Rendering: ${valueOrDash(version.preferredRendering)}\nConfidence: ${valueOrDash(version.confidence)}\nApproval Authority: ${valueOrDash(version.approvalAuthority)}\nApproved By: ${valueOrDash(version.approvedBy)}\nApproved At: ${valueOrDash(version.approvedAt)}\n\n### Reason\n'''
    text = replace_exact(text, old, new, "server serialize approval provenance")

    old = '''    preferredRendering: normalizeDecisionValue(body.preferredRendering),\n    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",\n    reason: normalizeDecisionValue(body.reason)\n'''
    new = '''    preferredRendering: normalizeDecisionValue(body.preferredRendering),\n    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",\n    reason: normalizeDecisionValue(body.reason),\n    approvalAuthority: normalizeDecisionValue(fallback.approvalAuthority),\n    approvedBy: normalizeDecisionValue(fallback.approvedBy),\n    approvedAt: normalizeDecisionValue(fallback.approvedAt)\n'''
    text = replace_exact(text, old, new, "server preserve existing provenance")

    old = '''      effectiveDate: ""\n    };\n'''
    new = '''      effectiveDate: "",\n      approvalAuthority: "",\n      approvedBy: "",\n      approvedAt: ""\n    };\n'''
    text = replace_exact(text, old, new, "server clear provenance on revised draft")

    old = '''  if (body.action === "approve") {\n    const current = versions.at(-1);\n    if (!normalizeDecisionValue(current.preferredRendering) || !normalizeDecisionValue(current.reason)) {\n      sendJson(response, 400, { error: "Preferred Rendering and Reason are required before approval." });\n      return;\n    }\n\n    const previousApproved = versions.slice(0, -1).filter(version => version.status === "Approved");\n'''
    new = '''  if (body.action === "approve") {\n    const current = versions.at(-1);\n    if (!normalizeDecisionValue(current.preferredRendering) || !normalizeDecisionValue(current.reason)) {\n      sendJson(response, 400, { error: "Preferred Rendering and Reason are required before approval." });\n      return;\n    }\n    const approvedBy = normalizeDecisionValue(body.approvedBy);\n    if (body.humanConfirmation !== true || !approvedBy) {\n      sendJson(response, 400, { error: "Explicit human confirmation and approver name are required before approval." });\n      return;\n    }\n    if (approvedBy.length > 120) {\n      sendJson(response, 400, { error: "Approver name is too long." });\n      return;\n    }\n\n    const previousApproved = versions.slice(0, -1).filter(version => version.status === "Approved");\n'''
    text = replace_exact(text, old, new, "server require explicit human approval")

    old = '''    if (current.status !== "Approved") {\n      current.status = "Approved";\n      current.effectiveDate = current.effectiveDate || todayIsoDate();\n      historyEntries.push(`Approved decision ${current.version} for ${current.strongs} ${current.lemma}.`);\n    }\n'''
    new = '''    const alreadyApproved = current.status === "Approved";\n    current.status = "Approved";\n    current.effectiveDate = current.effectiveDate || todayIsoDate();\n    current.approvalAuthority = "human";\n    current.approvedBy = approvedBy;\n    current.approvedAt = new Date().toISOString();\n    if (alreadyApproved) {\n      historyEntries.push(`Recorded human approval for decision ${current.version} by ${approvedBy}.`);\n    } else {\n      historyEntries.push(`Approved decision ${current.version} for ${current.strongs} ${current.lemma} by ${approvedBy}.`);\n    }\n'''
    return replace_exact(text, old, new, "server record human approval provenance")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply the checked patch. Default is dry-run.")
    args = parser.parse_args()

    targets = [
        (ROOT / "public" / "index.html", patch_index),
        (ROOT / "public" / "main.js", patch_main),
        (ROOT / "server.js", patch_server),
    ]

    patched: list[tuple[Path, str]] = []
    print("HUMAN INVESTIGATION APPROVAL PATCH")
    for path, patcher in targets:
        original = path.read_text(encoding="utf-8")
        updated = patcher(original)
        if updated == original:
            raise RuntimeError(f"{path.relative_to(ROOT)}: patch produced no change")
        patched.append((path, updated))
        print(f"{path.relative_to(ROOT)}: patch ready")

    if not args.apply:
        print("DRY RUN: no files changed. Re-run with --apply to patch.")
        return 0

    for path, updated in patched:
        path.write_text(updated, encoding="utf-8")
        print(f"PATCHED {path.relative_to(ROOT)}")

    print("PASS: investigation approval now requires explicit recorded human provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
