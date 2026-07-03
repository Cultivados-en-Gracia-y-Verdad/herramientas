#!/usr/bin/env node
/**
 * Validate CGV Dictionary lemma files and regenerate language indexes.
 *
 * Usage (from repo root):
 *   npm run dictionary:validate
 */

import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SCHEMA_PATH = join(ROOT, "schema", "lemma.schema.json");
const GREEK_DIR = join(ROOT, "greek");
const INDEX_PATH = join(ROOT, "indexes", "greek.json");

const VALID_STATUS = new Set(["draft", "review", "approved", "published"]);

const REQUIRED_FIELDS = [
  "id",
  "strongs",
  "language",
  "lemma",
  "transliteration",
  "partOfSpeech",
  "status",
  "preferredRenderings",
  "alternativeRenderings",
  "coreIdea",
  "translationNotes",
  "translationWarnings",
  "observations",
  "contexts",
  "family",
  "related",
  "examples",
  "metadata",
];

function rel(path) {
  return relative(ROOT, path) || ".";
}

function findLemmaFiles() {
  const files = [];
  if (!statSync(GREEK_DIR, { throwIfNoEntry: false })) {
    return files;
  }
  for (const entry of readdirSync(GREEK_DIR)) {
    if (!/^G\d+$/.test(entry)) continue;
    const lemmaPath = join(GREEK_DIR, entry, "lemma.json");
    try {
      statSync(lemmaPath);
      files.push(lemmaPath);
    } catch {
      // no lemma.json in this folder
    }
  }
  return files.sort();
}

function loadSchema() {
  return JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));
}

function schemaPathErrors(value, subschema, pathParts = []) {
  const errors = [];
  const at = pathParts.join(".") || "(root)";

  if (subschema.type === "object") {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      errors.push(`${at}: expected object`);
      return errors;
    }
    for (const key of subschema.required || []) {
      if (!(key in value)) {
        errors.push(`${at}: missing required field "${key}"`);
      }
    }
    for (const [key, propSchema] of Object.entries(subschema.properties || {})) {
      if (key in value) {
        errors.push(...schemaPathErrors(value[key], propSchema, [...pathParts, key]));
      }
    }
    if (subschema.additionalProperties === false) {
      for (const key of Object.keys(value)) {
        if (!subschema.properties?.[key]) {
          errors.push(`${at}: unexpected field "${key}"`);
        }
      }
    }
    return errors;
  }

  if (subschema.type === "array") {
    if (!Array.isArray(value)) {
      errors.push(`${at}: expected array`);
      return errors;
    }
    if (subschema.items) {
      value.forEach((item, i) => {
        errors.push(...schemaPathErrors(item, subschema.items, [...pathParts, String(i)]));
      });
    }
    return errors;
  }

  if (subschema.type === "string") {
    if (typeof value !== "string") {
      errors.push(`${at}: expected string`);
      return errors;
    }
    if (subschema.minLength && value.length < subschema.minLength) {
      errors.push(`${at}: string too short`);
    }
    if (subschema.pattern && !new RegExp(subschema.pattern).test(value)) {
      errors.push(`${at}: does not match pattern ${subschema.pattern}`);
    }
    if (subschema.enum && !subschema.enum.includes(value)) {
      errors.push(`${at}: invalid value "${value}" (expected ${subschema.enum.join(" | ")})`);
    }
    return errors;
  }

  if (subschema.type === "integer") {
    if (!Number.isInteger(value)) {
      errors.push(`${at}: expected integer`);
      return errors;
    }
    if (subschema.minimum !== undefined && value < subschema.minimum) {
      errors.push(`${at}: must be >= ${subschema.minimum}`);
    }
    return errors;
  }

  return errors;
}

function missingRequiredFields(data) {
  return REQUIRED_FIELDS.filter((field) => !(field in data));
}

function compactRecord(data) {
  return {
    id: data.id,
    strongs: data.strongs,
    lemma: data.lemma,
    transliteration: data.transliteration,
    partOfSpeech: data.partOfSpeech,
    status: data.status,
    preferredRenderings: data.preferredRenderings,
  };
}

function strongsSortKey(strongs) {
  const m = String(strongs).match(/^[GH](\d+)$/);
  return m ? Number(m[1]) : Number.MAX_SAFE_INTEGER;
}

function main() {
  const schema = loadSchema();
  const lemmaFiles = findLemmaFiles();

  const report = {
    invalidJson: [],
    missingRequiredFields: [],
    duplicateStrongs: [],
    duplicateIds: [],
    missingPreferredRenderings: [],
    invalidStatus: [],
    schemaErrors: [],
  };

  const byStrongs = new Map();
  const byId = new Map();
  const validEntries = [];

  console.log("CGV Dictionary — validate Greek lemmas");
  console.log(`Schema: ${rel(SCHEMA_PATH)}`);
  console.log(`Found: ${lemmaFiles.length} lemma file(s)\n`);

  if (!lemmaFiles.length) {
    console.warn("Warning: no files matched greek/G*/lemma.json");
  }

  for (const filePath of lemmaFiles) {
    const label = rel(filePath);
    let data;

    try {
      data = JSON.parse(readFileSync(filePath, "utf8"));
    } catch (err) {
      report.invalidJson.push({ file: label, error: err.message });
      continue;
    }

    const missing = missingRequiredFields(data);
    if (missing.length) {
      report.missingRequiredFields.push({ file: label, fields: missing });
    }

    if (!Array.isArray(data.preferredRenderings) || data.preferredRenderings.length === 0) {
      report.missingPreferredRenderings.push({ file: label, id: data.id || null });
    }

    if (data.status && !VALID_STATUS.has(data.status)) {
      report.invalidStatus.push({ file: label, status: data.status });
    }

    const schemaErrs = schemaPathErrors(data, schema);
    for (const msg of schemaErrs) {
      report.schemaErrors.push({ file: label, error: msg });
    }

    if (data.strongs) {
      const prev = byStrongs.get(data.strongs);
      if (prev) {
        report.duplicateStrongs.push({
          strongs: data.strongs,
          files: [prev, label],
        });
      } else {
        byStrongs.set(data.strongs, label);
      }
    }

    if (data.id) {
      const prev = byId.get(data.id);
      if (prev) {
        report.duplicateIds.push({
          id: data.id,
          files: [prev, label],
        });
      } else {
        byId.set(data.id, label);
      }
    }

    const hasBlockingIssue =
      missing.length > 0
      || !Array.isArray(data.preferredRenderings)
      || data.preferredRenderings.length === 0
      || (data.status && !VALID_STATUS.has(data.status))
      || schemaErrs.length > 0;

    if (!hasBlockingIssue) {
      validEntries.push(compactRecord(data));
    }
  }

  // Expand duplicate reports to include all colliding files
  for (const [strongs, file] of byStrongs.entries()) {
    const matches = lemmaFiles
      .map((p) => rel(p))
      .filter((f) => {
        try {
          const d = JSON.parse(readFileSync(join(ROOT, f), "utf8"));
          return d.strongs === strongs;
        } catch {
          return false;
        }
      });
    if (matches.length > 1) {
      const existing = report.duplicateStrongs.find((d) => d.strongs === strongs);
      if (existing) existing.files = matches;
      else report.duplicateStrongs.push({ strongs, files: matches });
    }
  }

  for (const [id, file] of byId.entries()) {
    const matches = lemmaFiles
      .map((p) => rel(p))
      .filter((f) => {
        try {
          const d = JSON.parse(readFileSync(join(ROOT, f), "utf8"));
          return d.id === id;
        } catch {
          return false;
        }
      });
    if (matches.length > 1) {
      const existing = report.duplicateIds.find((d) => d.id === id);
      if (existing) existing.files = matches;
      else report.duplicateIds.push({ id, files: matches });
    }
  }

  const indexPayload = validEntries.sort(
    (a, b) => strongsSortKey(a.strongs) - strongsSortKey(b.strongs)
  );

  writeFileSync(INDEX_PATH, `${JSON.stringify(indexPayload, null, 2)}\n`, "utf8");

  function printSection(title, items, formatter) {
    if (!items.length) {
      console.log(`✓ ${title}: none`);
      return;
    }
    console.log(`✗ ${title}: ${items.length}`);
    for (const item of items) {
      console.log(`  - ${formatter(item)}`);
    }
  }

  printSection("Invalid JSON", report.invalidJson, (i) => `${i.file}: ${i.error}`);
  printSection(
    "Missing required fields",
    report.missingRequiredFields,
    (i) => `${i.file}: ${i.fields.join(", ")}`
  );
  printSection(
    "Duplicate Strong's numbers",
    report.duplicateStrongs,
    (i) => `${i.strongs} in ${i.files.join(", ")}`
  );
  printSection(
    "Duplicate internal ids",
    report.duplicateIds,
    (i) => `${i.id} in ${i.files.join(", ")}`
  );
  printSection(
    "Missing preferredRenderings",
    report.missingPreferredRenderings,
    (i) => `${i.file}${i.id ? ` (${i.id})` : ""}`
  );
  printSection(
    "Invalid status values",
    report.invalidStatus,
    (i) => `${i.file}: "${i.status}"`
  );
  printSection(
    "Schema validation errors",
    report.schemaErrors,
    (i) => `${i.file}: ${i.error}`
  );

  console.log(`\nIndex written: ${rel(INDEX_PATH)} (${validEntries.length} lemma(s))`);

  const errorCount =
    report.invalidJson.length
    + report.missingRequiredFields.length
    + report.duplicateStrongs.length
    + report.duplicateIds.length
    + report.missingPreferredRenderings.length
    + report.invalidStatus.length
    + report.schemaErrors.length;

  if (errorCount > 0) {
    console.error(`\nValidation failed with ${errorCount} issue(s).`);
    process.exit(1);
  }

  console.log("\nDone.");
}

main();
