export const DECISION_SCOPES = Object.freeze([
  "Occurrence",
  "Construction",
  "Book Default"
]);

const SCOPE_PRIORITY = Object.freeze({
  "Occurrence": 3,
  "Construction": 2,
  "Book Default": 1
});

export function isDecisionScope(value = "") {
  return DECISION_SCOPES.includes(String(value || "").trim());
}

export function validateDecisionScope({ scope = "", scopeReference = "", scopeCondition = "" } = {}) {
  const normalizedScope = String(scope || "").trim();
  if (!isDecisionScope(normalizedScope)) {
    return { valid: false, error: "Decision Scope is required." };
  }
  if (normalizedScope === "Occurrence" && !String(scopeReference || "").trim()) {
    return { valid: false, error: "Occurrence scope requires Scope Reference." };
  }
  if (normalizedScope === "Construction" && !String(scopeCondition || "").trim()) {
    return { valid: false, error: "Construction scope requires Scope Condition." };
  }
  return { valid: true, error: null };
}

export function policyMatchesLemma(row = {}, policy = {}) {
  const strongs = String(row.strongs || "").trim().toUpperCase();
  const lemma = String(row.lemma || "").trim();
  const policyStrongs = String(policy.strongs || "").trim().toUpperCase();
  const policyLemma = String(policy.lemma || "").trim();
  return Boolean(
    (strongs && policyStrongs && strongs === policyStrongs)
    || (lemma && policyLemma && lemma === policyLemma)
  );
}

export function constructionConditionMatches(row = {}, condition = "") {
  const clauses = String(condition || "")
    .split(";")
    .map(item => item.trim())
    .filter(Boolean);
  if (!clauses.length) return false;

  const supported = {
    morph: String(row.rmac || row.morph || ""),
    surface: String(row.greek || row.surface || ""),
    lemma: String(row.lemma || ""),
    strongs: String(row.strongs || "").trim().toUpperCase()
  };

  for (const clause of clauses) {
    const match = clause.match(/^(morph|surface|lemma|strongs)=(.+)$/u);
    if (!match) return false;
    const [, key, expectedRaw] = match;
    const expected = key === "strongs"
      ? expectedRaw.trim().toUpperCase()
      : expectedRaw.trim();
    if (supported[key] !== expected) return false;
  }
  return true;
}

export function policyApplicability(policy = {}, row = {}, reference = "") {
  if (!policyMatchesLemma(row, policy)) return null;
  if (policy.scope === "Occurrence") {
    return String(policy.scopeReference || "").trim() === String(reference || "").trim()
      ? { priority: SCOPE_PRIORITY.Occurrence, kind: "occurrence" }
      : null;
  }
  if (policy.scope === "Construction") {
    return constructionConditionMatches(row, policy.scopeCondition)
      ? { priority: SCOPE_PRIORITY.Construction, kind: "construction" }
      : null;
  }
  if (policy.scope === "Book Default") {
    return { priority: SCOPE_PRIORITY["Book Default"], kind: "book-default" };
  }
  return null;
}

export function selectApplicableDecision(row = {}, policies = [], reference = "") {
  return policies
    .map(policy => ({ policy, match: policyApplicability(policy, row, reference) }))
    .filter(item => item.match)
    .sort((left, right) => right.match.priority - left.match.priority)[0]?.policy || null;
}
