import fs from 'node:fs';
import path from 'node:path';
import * as XLSX from 'xlsx';
import type { DatabaseSync } from 'node:sqlite';

export interface ImportReport { totalRows: number; imported: number; updated: number; skipped: number; errors: string[]; missingFields: string[] }
type Row = Record<string, unknown>;

const aliases = {
  id: ['id', 'record id', 'source id', 'source_id', 'number', 'no', '#', 'prophecy id', 'prophecy_id'],
  reference: ['scripture reference', 'scripture_reference', 'reference', 'bible reference', 'passage', 'scripture'],
  url: ['url', 'source url', 'source_url', 'study url', 'study link', 'link'],
  classification: ['classification', 'category', 'type', 'source classification', 'topic category — source', 'topic category - source'],
  fulfillment: ['fulfillment', 'fulfilment', 'fulfilled', 'fulfillment claim', 'source fulfillment', 'fulfillment status — source', 'fulfillment status - source'],
  payne: ['payne', 'payne mapping', 'payne_mapping', 'payne mapping — source', 'payne mapping - source']
} as const;

function normalizeKey(value: string) { return value.trim().toLowerCase().replace(/[._-]+/g, ' ').replace(/\s+/g, ' '); }
function pick(row: Row, names: readonly string[]) {
  const entries = new Map(Object.entries(row).map(([key, value]) => [normalizeKey(key), value]));
  for (const name of names) {
    const value = entries.get(normalizeKey(name));
    if (value !== undefined && value !== null && String(value).trim() !== '') return String(value).trim();
  }
  return '';
}

export function parseCsv(input: string): Row[] {
  const rows: string[][] = [];
  let row: string[] = [], field = '', quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (quoted) {
      if (char === '"' && input[i + 1] === '"') { field += '"'; i++; }
      else if (char === '"') quoted = false;
      else field += char;
    } else if (char === '"') quoted = true;
    else if (char === ',') { row.push(field); field = ''; }
    else if (char === '\n') { row.push(field.replace(/\r$/, '')); rows.push(row); row = []; field = ''; }
    else field += char;
  }
  if (field || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
  const [headers = [], ...data] = rows.filter((r) => r.some((cell) => cell.trim()));
  return data.map((cells) => Object.fromEntries(headers.map((header, index) => [header.trim(), cells[index] ?? ''])));
}

function rowsFromFile(filename: string): Row[] {
  const extension = path.extname(filename).toLowerCase();
  if (extension === '.csv') return parseCsv(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/, ''));
  if (extension === '.xlsx' || extension === '.xls') {
    const workbook = XLSX.readFile(filename);
    const first = workbook.SheetNames[0];
    if (!first) return [];
    return XLSX.utils.sheet_to_json(workbook.Sheets[first], { defval: '', raw: false });
  }
  throw new Error(`Unsupported input format: ${extension || '(none)'}. Use CSV, XLSX, or XLS.`);
}

function bookFrom(reference: string) {
  const match = reference.match(/^\s*((?:[1-3]\s*)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\d/);
  return match?.[1]?.trim() || null;
}

export function importRows(db: DatabaseSync, rows: Row[], sourceName: string): ImportReport {
  const report: ImportReport = { totalRows: rows.length, imported: 0, updated: 0, skipped: 0, errors: [], missingFields: [] };
  const upsertSource = db.prepare(`INSERT INTO source_records
    (source_name, original_source_id, scripture_reference, original_source_url, original_classification, original_fulfillment_claim, payne_mapping, imported_metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source_name, original_source_id) DO UPDATE SET
      scripture_reference=excluded.scripture_reference, original_source_url=excluded.original_source_url,
      original_classification=excluded.original_classification, original_fulfillment_claim=excluded.original_fulfillment_claim,
      payne_mapping=excluded.payne_mapping, imported_metadata=excluded.imported_metadata, imported_at=CURRENT_TIMESTAMP`);
  const find = db.prepare('SELECT id FROM source_records WHERE source_name = ? AND original_source_id = ?');
  const insertPassage = db.prepare(`INSERT OR IGNORE INTO passages
    (source_record_id, book, original_reference, normalized_reference) VALUES (?, ?, ?, ?)`);

  db.exec('BEGIN');
  try {
    rows.forEach((row, index) => {
      const id = pick(row, aliases.id);
      const reference = pick(row, aliases.reference);
      const missing = [...(!id ? ['source ID'] : []), ...(!reference ? ['Scripture reference'] : [])];
      if (missing.length) {
        report.skipped++;
        report.errors.push(`Row ${index + 2}: missing ${missing.join(' and ')}`);
        missing.forEach((field) => { if (!report.missingFields.includes(field)) report.missingFields.push(field); });
        return;
      }
      const existed = Boolean(find.get(sourceName, id));
      upsertSource.run(sourceName, id, reference, pick(row, aliases.url) || null, pick(row, aliases.classification) || null,
        pick(row, aliases.fulfillment) || null, pick(row, aliases.payne) || null, JSON.stringify(row));
      const source = find.get(sourceName, id) as { id: number };
      insertPassage.run(source.id, bookFrom(reference), reference, reference.trim().replace(/\s+/g, ' '));
      existed ? report.updated++ : report.imported++;
    });
    db.exec('COMMIT');
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
  return report;
}

export function importCatalog(db: DatabaseSync, filename: string, sourceName = path.basename(filename, path.extname(filename))) {
  if (!fs.existsSync(filename)) throw new Error(`Input file not found: ${filename}`);
  return importRows(db, rowsFromFile(filename), sourceName);
}
