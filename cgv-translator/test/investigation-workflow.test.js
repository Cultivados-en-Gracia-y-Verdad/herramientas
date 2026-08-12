import test from "node:test";
import assert from "node:assert/strict";

import {
  constructionConditionMatches,
  policyApplicability,
  selectApplicableDecision,
  validateDecisionScope
} from "../src/investigations/decisionScope.js";
import {
  formatInvestigationId,
  parseInvestigationId
} from "../src/investigations/createInvestigation.js";

test("canonical investigation ids encode book ownership", () => {
  assert.equal(formatInvestigationId(27, 1), "INV-27-0001");
  assert.deepEqual(parseInvestigationId("INV-56-0042"), { bookNumber: 56, sequence: 42 });
  assert.throws(() => formatInvestigationId(0, 1), /book number/i);
  assert.throws(() => formatInvestigationId(27, 0), /sequence/i);
});

test("approval scope is explicit and structurally valid", () => {
  assert.deepEqual(validateDecisionScope({}), {
    valid: false,
    error: "Decision Scope is required."
  });
  assert.equal(validateDecisionScope({ scope: "Occurrence" }).valid, false);
  assert.equal(validateDecisionScope({
    scope: "Occurrence",
    scopeReference: "Daniel 1:1"
  }).valid, true);
  assert.equal(validateDecisionScope({ scope: "Construction" }).valid, false);
  assert.equal(validateDecisionScope({
    scope: "Construction",
    scopeCondition: "morph=HNcmsc; strongs=H4428"
  }).valid, true);
  assert.equal(validateDecisionScope({ scope: "Book Default" }).valid, true);
});

test("construction scope accepts only machine-verifiable condition syntax", () => {
  const row = {
    strongs: "H4428",
    lemma: "מֶלֶךְ",
    surface: "מֶלֶךְ",
    morph: "HNcmsc"
  };

  assert.equal(constructionConditionMatches(row, "morph=HNcmsc; strongs=h4428"), true);
  assert.equal(constructionConditionMatches(row, "morph=HNcmsc; surface=מֶלֶךְ"), true);
  assert.equal(constructionConditionMatches(row, "case=construct"), false);
  assert.equal(constructionConditionMatches(row, "morph"), false);
  assert.equal(constructionConditionMatches(row, ""), false);
});

test("scope specificity is Occurrence > Construction > Book Default", () => {
  const row = {
    strongs: "H4428",
    lemma: "מֶלֶךְ",
    surface: "מֶלֶךְ",
    morph: "HNcmsc"
  };
  const policies = [
    {
      investigationId: "INV-27-0001",
      strongs: "H4428",
      lemma: "מֶלֶךְ",
      scope: "Book Default",
      preferredRendering: "rey"
    },
    {
      investigationId: "INV-27-0002",
      strongs: "H4428",
      lemma: "מֶלֶךְ",
      scope: "Construction",
      scopeCondition: "morph=HNcmsc",
      preferredRendering: "monarca"
    },
    {
      investigationId: "INV-27-0003",
      strongs: "H4428",
      lemma: "מֶלֶךְ",
      scope: "Occurrence",
      scopeReference: "Daniel 1:1",
      preferredRendering: "rey"
    }
  ];

  assert.equal(
    selectApplicableDecision(row, policies, "Daniel 1:1")?.investigationId,
    "INV-27-0003"
  );
  assert.equal(
    selectApplicableDecision(row, policies, "Daniel 1:2")?.investigationId,
    "INV-27-0002"
  );
  assert.equal(
    selectApplicableDecision({ ...row, morph: "HNcmsa" }, policies, "Daniel 1:2")?.investigationId,
    "INV-27-0001"
  );
});

test("a policy never crosses to another lemma merely because scope matches", () => {
  const policy = {
    strongs: "H4428",
    lemma: "מֶלֶךְ",
    scope: "Occurrence",
    scopeReference: "Daniel 1:1"
  };
  assert.equal(
    policyApplicability(policy, { strongs: "H5174", lemma: "נְחָשָׁא" }, "Daniel 1:1"),
    null
  );
});
