import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

function todayIsoDate() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/La_Paz" });
}

function normalizeStrongs(value = "") {
  const raw = String(value || "").trim().toUpperCase();
  if (!raw) return "";
  if (/^G\d+$/.test(raw)) return raw;
  if (/^\d+$/.test(raw)) return `G${raw}`;
  return raw;
}

function bookFromReference(reference = "") {
  const match = String(reference || "").trim().match(/^(.+?)\s+\d+/u);
  return match ? match[1].trim() : "Titus";
}

function investigationNumber(id = "") {
  const match = String(id).match(/^INV-(\d{4})$/);
  return match ? Number(match[1]) : 0;
}

function parseDecisionVersions(markdown) {
  const sections = String(markdown || "").split(/^## Version\s+/m).slice(1);
  return sections.map(section => {
    const lines = section.replace(/\r\n/g, "\n").split("\n");
    const fields = {};
    for (const line of lines) {
      const match = line.match(/^([^:]+):\s*(.*)$/);
      if (!match) continue;
      fields[match[1].trim().toLowerCase()] = match[2].trim();
    }
    return {
      lemma: fields.lemma || "",
      strongs: normalizeStrongs(fields["strong's"] || fields.strongs || ""),
      status: fields.status || ""
    };
  });
}

function readPrimarySubject(readme = "") {
  const match = String(readme).match(/## Primary Subject\s*\n+([^\n]+)/);
  return (match?.[1] || "").trim();
}

export async function listInvestigationIds(investigationsDir) {
  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);
  return entries
    .filter(entry => entry.isDirectory() && /^INV-\d{4}$/.test(entry.name))
    .map(entry => entry.name)
    .sort();
}

export async function allocateNextInvestigationId(investigationsDir) {
  const ids = await listInvestigationIds(investigationsDir);
  const next = Math.max(0, ...ids.map(investigationNumber)) + 1;
  return `INV-${String(next).padStart(4, "0")}`;
}

export async function findInvestigationByLemma(investigationsDir, { lemma = "", strongs = "" } = {}) {
  const targetLemma = String(lemma || "").trim();
  const targetStrongs = normalizeStrongs(strongs);
  if (!targetLemma && !targetStrongs) return null;

  const ids = await listInvestigationIds(investigationsDir);
  for (const id of ids) {
    const dir = join(investigationsDir, id);
    const [decisionMd, readme] = await Promise.all([
      readFile(join(dir, "decision.md"), "utf8").catch(() => ""),
      readFile(join(dir, "README.md"), "utf8").catch(() => "")
    ]);
    const latest = parseDecisionVersions(decisionMd).at(-1);
    const primary = readPrimarySubject(readme);
    const primaryStrongs = normalizeStrongs((primary.match(/\bG\d+\b/) || [])[0] || "");
    const primaryLemma = primary.replace(/^G\d+\s*[—-]\s*/u, "").trim();

    const strongsMatch = targetStrongs
      && (latest?.strongs === targetStrongs || primaryStrongs === targetStrongs);
    const lemmaMatch = targetLemma
      && (latest?.lemma === targetLemma || primaryLemma === targetLemma);

    if (strongsMatch || lemmaMatch) {
      return {
        id,
        lemma: latest?.lemma || primaryLemma || targetLemma,
        strongs: latest?.strongs || primaryStrongs || targetStrongs,
        status: latest?.status || "Draft"
      };
    }
  }

  return null;
}

function buildScaffold({
  id,
  lemma,
  strongs,
  reference,
  clause,
  surface,
  ble,
  book
}) {
  const date = todayIsoDate();
  const number = id.replace(/^INV-/u, "");
  const subject = [strongs, lemma].filter(Boolean).join(" — ") || lemma;
  const clauseText = clause || surface || lemma;
  const bleNote = ble || "—";

  const readme = `# Investigation ${number}

## Origin

Project

La Biblia Fiel

Book

${book}

Reference

${reference}

Clause

${clauseText}

---

## Why this investigation exists

Translation paused because the translator chose to investigate the Greek lemma ${lemma}${strongs ? ` (${strongs})` : ""}.

---

## Objective

Determine whether a stable LBF rendering is needed for the primary subject of this investigation.

---

## Final Authority

The biblical text.

---

## Primary Subject

${subject}

---

## Related Subjects

None identified.

---

## Current Status

Observation
`;

  const observations = `# Observations

## Objective

Record only observations that are directly supported by the biblical text.

Do not record conclusions.

Do not establish translation policy.

Questions belong in \`questions.md\`.

---

## Origin Text

${reference}

> ${clauseText}

---

## Initial Observations

### O-001

The investigation originates from ${reference}.

### O-002

The current BLE provisional rendering is ${bleNote}.
`;

  const decision = `# Decision

## Version 0.1

Status: Draft
Version: 0.1
Effective Date: ${date}
Lemma: ${lemma}
Strong's: ${strongs}
Preferred Rendering: 
Confidence: 

### Reason

Investigation opened; decision not yet made.
`;

  const questions = `# Questions

## Initial Questions

### Q-001

Does ${lemma} require an LBF decision beyond the provisional BLE rendering?
`;

  const evidence = `# Evidence

Evidence has not been gathered yet.
`;

  const research = `# Research

No research notes recorded yet.
`;

  const policy = `# Policy

No policy has been established yet.
`;

  const history = `# History

## ${date}

Investigation created from ${reference || "translator request"} for ${subject}.
`;

  const evidenceReadme = `# Evidence

## Purpose

This directory contains objective evidence gathered during the investigation.

Evidence should be directly traceable to the biblical text.

Research and interpretation belong elsewhere.

---

## Current Evidence

None yet.

Additional evidence may be added as the investigation requires.
`;

  return {
    "README.md": readme,
    "observations.md": observations,
    "decision.md": decision,
    "questions.md": questions,
    "evidence.md": evidence,
    "research.md": research,
    "policy.md": policy,
    "history.md": history,
    "evidence/README.md": evidenceReadme
  };
}

/**
 * Create a new investigation folder from a lemma, or return an existing match.
 */
export async function createInvestigationFromLemma(rootDir, body = {}) {
  const lemma = String(body.lemma || "").trim();
  if (!lemma) {
    throw new Error("lemma is required");
  }

  const strongs = normalizeStrongs(body.strongs);
  const reference = String(body.reference || "").trim() || "Titus 1:1";
  const clause = String(body.clause || "").trim();
  const surface = String(body.surface || "").trim();
  const ble = String(body.ble || body.rendering || "").trim();
  const book = String(body.book || "").trim() || bookFromReference(reference);
  const investigationsDir = join(rootDir, "investigations");

  const existing = await findInvestigationByLemma(investigationsDir, { lemma, strongs });
  if (existing && body.force !== true) {
    return {
      created: false,
      existing: true,
      id: existing.id,
      lemma: existing.lemma || lemma,
      strongs: existing.strongs || strongs,
      status: existing.status || "Draft"
    };
  }

  const id = await allocateNextInvestigationId(investigationsDir);
  const investigationDir = join(investigationsDir, id);
  const files = buildScaffold({
    id,
    lemma,
    strongs,
    reference,
    clause,
    surface,
    ble,
    book
  });

  await mkdir(join(investigationDir, "evidence"), { recursive: true });
  for (const [relativePath, content] of Object.entries(files)) {
    const target = join(investigationDir, relativePath);
    await writeFile(target, content.endsWith("\n") ? content : `${content}\n`, "utf8");
  }

  return {
    created: true,
    existing: false,
    id,
    lemma,
    strongs,
    status: "Draft",
    reference
  };
}
