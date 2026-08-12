#!/usr/bin/env python3
"""Guarded patch: make investigation decision scope explicit and enforceable.

Run only after:
  1. migrate_investigation_ids.py --apply
  2. apply_human_investigation_approval_patch.py --apply

Dry-run by default. Use --apply to modify:
- public/index.html
- public/main.js
- server.js
- src/investigations/createInvestigation.js
- src/pipeline/analyzeGates.js
- src/pipeline/assistGates.js

Scopes:
- Occurrence
- Construction
- Book Default

Book Default is lexical guidance, not a hard exact-string replacement rule.
Occurrence and machine-verifiable Construction decisions are more specific.
Unknown Construction condition syntax is documented but never auto-applied.
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
    old = '''                <label>\n                  Confidence\n                  <select id="decision-confidence">\n                    <option>High</option>\n                    <option>Medium</option>\n                    <option>Low</option>\n                  </select>\n                </label>\n                <label>\n                  Approval Authority\n'''
    new = '''                <label>\n                  Confidence\n                  <select id="decision-confidence">\n                    <option>High</option>\n                    <option>Medium</option>\n                    <option>Low</option>\n                  </select>\n                </label>\n                <label>\n                  Scope\n                  <select id="decision-scope">\n                    <option value="">Select scope…</option>\n                    <option>Occurrence</option>\n                    <option>Construction</option>\n                    <option>Book Default</option>\n                  </select>\n                </label>\n                <label>\n                  Scope Reference\n                  <input id="decision-scope-reference" type="text" autocomplete="off" placeholder="Daniel 1:1" />\n                </label>\n                <label>\n                  Scope Condition\n                  <input id="decision-scope-condition" type="text" autocomplete="off" placeholder="morph=HNcmsc; surface=מֶלֶךְ" />\n                </label>\n                <label>\n                  Approval Authority\n'''
    text = replace_exact(text, old, new, "index decision scope fields")

    old = '''                <p>Final investigation approval must be explicitly human initiated and attributed.</p>\n'''
    new = '''                <p>Final investigation approval must be explicitly human initiated and attributed. Scope is part of what is approved.</p>\n'''
    return replace_exact(text, old, new, "index scope approval notice")


def patch_main(text: str) -> str:
    old = '''const decisionReason = document.querySelector("#decision-reason");\nconst decisionApprovalAuthority = document.querySelector("#decision-approval-authority");\n'''
    new = '''const decisionReason = document.querySelector("#decision-reason");\nconst decisionScope = document.querySelector("#decision-scope");\nconst decisionScopeReference = document.querySelector("#decision-scope-reference");\nconst decisionScopeCondition = document.querySelector("#decision-scope-condition");\nconst decisionApprovalAuthority = document.querySelector("#decision-approval-authority");\n'''
    text = replace_exact(text, old, new, "main scope selectors")

    old = '''  decisionConfidence.value = decision.confidence || "Medium";\n  decisionReason.value = decision.reason || "";\n  decisionApprovalAuthority.value = decision.approvalAuthority || "";\n'''
    new = '''  decisionConfidence.value = decision.confidence || "Medium";\n  decisionReason.value = decision.reason || "";\n  decisionScope.value = decision.scope || "";\n  decisionScopeReference.value = decision.scopeReference || "";\n  decisionScopeCondition.value = decision.scopeCondition || "";\n  decisionApprovalAuthority.value = decision.approvalAuthority || "";\n'''
    text = replace_exact(text, old, new, "main fill scope fields")

    old = '''    preferredRendering: decisionRendering.value,\n    confidence: decisionConfidence.value,\n    reason: decisionReason.value\n'''
    new = '''    preferredRendering: decisionRendering.value,\n    confidence: decisionConfidence.value,\n    scope: decisionScope.value,\n    scopeReference: decisionScopeReference.value,\n    scopeCondition: decisionScopeCondition.value,\n    reason: decisionReason.value\n'''
    text = replace_exact(text, old, new, "main save scope fields")

    old = '''    const approver = window.prompt(\n      "Type the human approver's name. This records final human approval for this investigation decision."\n    );\n'''
    new = '''    const scope = decisionScope.value;\n    if (!scope) {\n      prototypeMessage.textContent = "Select the decision scope before approval.";\n      decisionScope.focus();\n      return;\n    }\n    if (scope === "Occurrence" && !decisionScopeReference.value.trim()) {\n      prototypeMessage.textContent = "Occurrence scope requires a reference.";\n      decisionScopeReference.focus();\n      return;\n    }\n    if (scope === "Construction" && !decisionScopeCondition.value.trim()) {\n      prototypeMessage.textContent = "Construction scope requires a condition.";\n      decisionScopeCondition.focus();\n      return;\n    }\n    const approver = window.prompt(\n      `Type the human approver's name. This approves the rendering and its ${scope} scope.`\n    );\n'''
    text = replace_exact(text, old, new, "main validate scope before approval")
    return text


def patch_server(text: str) -> str:
    old = '''  reason: "",\n  approvalAuthority: "",\n'''
    new = '''  reason: "",\n  scope: "",\n  scopeReference: "",\n  scopeCondition: "",\n  approvalAuthority: "",\n'''
    text = replace_exact(text, old, new, "server scope defaults")

    old = '''      preferredRendering: readField("Preferred Rendering"),\n      confidence: readField("Confidence") || "Medium",\n      approvalAuthority: readField("Approval Authority"),\n'''
    new = '''      preferredRendering: readField("Preferred Rendering"),\n      confidence: readField("Confidence") || "Medium",\n      scope: readField("Scope"),\n      scopeReference: readField("Scope Reference"),\n      scopeCondition: readField("Scope Condition"),\n      approvalAuthority: readField("Approval Authority"),\n'''
    text = replace_exact(text, old, new, "server parse scope")

    old = '''Preferred Rendering: ${valueOrDash(version.preferredRendering)}\nConfidence: ${valueOrDash(version.confidence)}\nApproval Authority: ${valueOrDash(version.approvalAuthority)}\n'''
    new = '''Preferred Rendering: ${valueOrDash(version.preferredRendering)}\nConfidence: ${valueOrDash(version.confidence)}\nScope: ${valueOrDash(version.scope)}\nScope Reference: ${valueOrDash(version.scopeReference)}\nScope Condition: ${valueOrDash(version.scopeCondition)}\nApproval Authority: ${valueOrDash(version.approvalAuthority)}\n'''
    text = replace_exact(text, old, new, "server serialize scope")

    old = '''    "preferredRendering",\n    "confidence",\n    "reason"\n'''
    new = '''    "preferredRendering",\n    "confidence",\n    "scope",\n    "scopeReference",\n    "scopeCondition",\n    "reason"\n'''
    text = replace_exact(text, old, new, "server scope changes create revision")

    old = '''    preferredRendering: normalizeDecisionValue(body.preferredRendering),\n    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",\n    reason: normalizeDecisionValue(body.reason),\n    approvalAuthority: normalizeDecisionValue(fallback.approvalAuthority),\n'''
    new = '''    preferredRendering: normalizeDecisionValue(body.preferredRendering),\n    confidence: ["High", "Medium", "Low"].includes(body.confidence) ? body.confidence : "Medium",\n    scope: ["Occurrence", "Construction", "Book Default"].includes(body.scope) ? body.scope : "",\n    scopeReference: normalizeDecisionValue(body.scopeReference),\n    scopeCondition: normalizeDecisionValue(body.scopeCondition),\n    reason: normalizeDecisionValue(body.reason),\n    approvalAuthority: normalizeDecisionValue(fallback.approvalAuthority),\n'''
    text = replace_exact(text, old, new, "server decision body scope")

    old = '''      approvalAuthority: "",\n      approvedBy: "",\n      approvedAt: ""\n'''
    new = '''      approvalAuthority: "",\n      approvedBy: "",\n      approvedAt: ""\n'''
    # This is intentionally a no-op guard ensuring the human-approval patch is present.
    if text.count(old) < 1:
        raise RuntimeError("server human approval provenance reset not found")

    old = '''    const approvedBy = normalizeDecisionValue(body.approvedBy);\n    if (body.humanConfirmation !== true || !approvedBy) {\n'''
    new = '''    if (!["Occurrence", "Construction", "Book Default"].includes(current.scope)) {\n      sendJson(response, 400, { error: "Decision Scope is required before approval." });\n      return;\n    }\n    if (current.scope === "Occurrence" && !normalizeDecisionValue(current.scopeReference)) {\n      sendJson(response, 400, { error: "Occurrence scope requires Scope Reference." });\n      return;\n    }\n    if (current.scope === "Construction" && !normalizeDecisionValue(current.scopeCondition)) {\n      sendJson(response, 400, { error: "Construction scope requires Scope Condition." });\n      return;\n    }\n    const approvedBy = normalizeDecisionValue(body.approvedBy);\n    if (body.humanConfirmation !== true || !approvedBy) {\n'''
    return replace_exact(text, old, new, "server require approved scope")


def patch_create_investigation(text: str) -> str:
    old = '''Preferred Rendering: \nConfidence: \nApproval Authority: \n'''
    new = '''Preferred Rendering: \nConfidence: \nScope: Occurrence\nScope Reference: ${reference}\nScope Condition: \nApproval Authority: \n'''
    return replace_exact(text, old, new, "new investigation defaults to originating occurrence")


def patch_analyze_gates(text: str) -> str:
    old = '''      preferredRendering: fields["preferred rendering"] || "",\n      confidence: fields.confidence || "",\n      approvalAuthority: fields["approval authority"] || "",\n'''
    new = '''      preferredRendering: fields["preferred rendering"] || "",\n      confidence: fields.confidence || "",\n      scope: fields.scope || "",\n      scopeReference: fields["scope reference"] || "",\n      scopeCondition: fields["scope condition"] || "",\n      approvalAuthority: fields["approval authority"] || "",\n'''
    text = replace_exact(text, old, new, "analyze parse scope")

    old = '''      reason: latest.reason || "",\n      status: latest.status || "Draft",\n      approvalAuthority: latest.approvalAuthority || "",\n'''
    new = '''      reason: latest.reason || "",\n      status: latest.status || "Draft",\n      scope: latest.scope || "",\n      scopeReference: latest.scopeReference || "",\n      scopeCondition: latest.scopeCondition || "",\n      approvalAuthority: latest.approvalAuthority || "",\n'''
    text = replace_exact(text, old, new, "analyze policy scope record")

    old = '''function findPolicy(row, policies) {\n  const strongs = String(row.strongs || "").toUpperCase();\n  const lemma = row.lemma || "";\n  return policies.find(item =>\n    (strongs && item.strongs && item.strongs.toUpperCase() === strongs)\n    || (lemma && item.lemma === lemma)\n  ) || null;\n}\n\nfunction findOpenInvestigation(row, openInvestigations) {\n  return findPolicy(row, openInvestigations);\n}\n\nfunction analyzeLemmaGate(tokenRows, policies, openInvestigations = []) {\n'''
    new = '''function policyMatchesLemma(row, policy) {\n  const strongs = String(row.strongs || "").toUpperCase();\n  const lemma = row.lemma || "";\n  return Boolean(\n    (strongs && policy.strongs && policy.strongs.toUpperCase() === strongs)\n    || (lemma && policy.lemma === lemma)\n  );\n}\n\nfunction constructionConditionMatches(row, condition = "") {\n  const clauses = String(condition || "").split(";").map(item => item.trim()).filter(Boolean);\n  if (!clauses.length) return false;\n  const supported = {\n    morph: String(row.rmac || row.morph || ""),\n    surface: String(row.greek || row.surface || ""),\n    lemma: String(row.lemma || ""),\n    strongs: String(row.strongs || "").toUpperCase()\n  };\n  for (const clause of clauses) {\n    const match = clause.match(/^(morph|surface|lemma|strongs)=(.+)$/u);\n    if (!match) return false;\n    const [, key, expectedRaw] = match;\n    const expected = key === "strongs" ? expectedRaw.trim().toUpperCase() : expectedRaw.trim();\n    if (supported[key] !== expected) return false;\n  }\n  return true;\n}\n\nfunction policyApplicability(policy, row, reference) {\n  if (!policyMatchesLemma(row, policy)) return null;\n  if (policy.scope === "Occurrence") {\n    return policy.scopeReference === reference ? { priority: 3, kind: "occurrence" } : null;\n  }\n  if (policy.scope === "Construction") {\n    return constructionConditionMatches(row, policy.scopeCondition)\n      ? { priority: 2, kind: "construction" }\n      : null;\n  }\n  if (policy.scope === "Book Default") return { priority: 1, kind: "book-default" };\n  return null;\n}\n\nfunction findPolicy(row, policies, reference) {\n  return policies\n    .map(policy => ({ policy, match: policyApplicability(policy, row, reference) }))\n    .filter(item => item.match)\n    .sort((a, b) => b.match.priority - a.match.priority)[0]?.policy || null;\n}\n\nfunction findOpenInvestigation(row, openInvestigations, reference) {\n  const scoped = openInvestigations.find(item => policyApplicability(item, row, reference));\n  if (scoped) return scoped;\n  // Legacy/unscoped drafts remain blocking for their lemma until a human assigns scope.\n  return openInvestigations.find(item => policyMatchesLemma(row, item) && !item.scope) || null;\n}\n\nfunction analyzeLemmaGate(tokenRows, policies, openInvestigations = [], reference = "") {\n'''
    text = replace_exact(text, old, new, "analyze scope applicability engine")

    old = '''    const policy = findPolicy(row, policies);\n    const openInv = findOpenInvestigation(row, openInvestigations);\n'''
    new = '''    const policy = findPolicy(row, policies, reference);\n    const openInv = findOpenInvestigation(row, openInvestigations, reference);\n'''
    text = replace_exact(text, old, new, "analyze scoped policy lookup")

    old = '''      if (policy) {\n        status = "resolved";\n        allowedRenderings = [policy.preferredRendering].filter(Boolean);\n        policySource = `investigation/${policy.investigationId}`;\n'''
    new = '''      if (policy) {\n        status = "resolved";\n        // Book Default is lexical guidance, not a hard exact-string constraint.\n        allowedRenderings = policy.scope === "Book Default"\n          ? []\n          : [policy.preferredRendering].filter(Boolean);\n        policySource = `investigation/${policy.investigationId}`;\n'''
    text = replace_exact(text, old, new, "analyze book-default guidance")

    old = '''      confidence: policy?.confidence || (status === "provisional" ? "Low" : null),\n      status\n'''
    new = '''      confidence: policy?.confidence || (status === "provisional" ? "Low" : null),\n      policyScope: policy?.scope || null,\n      guidanceRendering: policy?.preferredRendering || null,\n      status\n'''
    text = replace_exact(text, old, new, "analyze expose scope guidance")

    old = '''  const lemma = analyzeLemmaGate(tokenRows, approved, openInvestigations);\n'''
    new = '''  const lemma = analyzeLemmaGate(tokenRows, approved, openInvestigations, reference);\n'''
    return replace_exact(text, old, new, "analyze pass reference to scope engine")


def patch_assist_gates(text: str) -> str:
    old = '''        t.allowedRenderings?.length\n          ? `prefer ${t.allowedRenderings.join("/")}`\n          : t.status === "blocked"\n            ? "BLOCKED — no policy"\n            : "no approved policy yet"\n'''
    new = '''        t.allowedRenderings?.length\n          ? `specific approved rendering ${t.allowedRenderings.join("/")} (${t.policyScope || "scoped"})`\n          : t.guidanceRendering\n            ? `book-default lexical guidance: ${t.guidanceRendering}; inflect/realize according to morphology and syntax`\n            : t.status === "blocked"\n              ? "BLOCKED — no applicable approved decision"\n              : "no applicable approved decision yet"\n'''
    return replace_exact(text, old, new, "assist distinguishes guidance from hard rendering")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply checked patch. Default is dry-run.")
    args = parser.parse_args()

    targets = [
        (ROOT / "public" / "index.html", patch_index),
        (ROOT / "public" / "main.js", patch_main),
        (ROOT / "server.js", patch_server),
        (ROOT / "src" / "investigations" / "createInvestigation.js", patch_create_investigation),
        (ROOT / "src" / "pipeline" / "analyzeGates.js", patch_analyze_gates),
        (ROOT / "src" / "pipeline" / "assistGates.js", patch_assist_gates),
    ]

    patched = []
    print("INVESTIGATION DECISION SCOPE PATCH")
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

    print("PASS: decision scope is explicit; book defaults are guidance, not exact-string rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
