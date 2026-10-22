import path from 'node:path';
import { migrate, openDatabase } from './db.js';
import { importCatalog } from './importer.js';

const filename = process.argv[2];
if (!filename) {
  console.error('Usage: npm run import -- <catalog.csv|catalog.xlsx> [source-name]');
  process.exit(1);
}
const db = openDatabase();
migrate(db);
const report = importCatalog(db, path.resolve(filename), process.argv[3]);
db.close();
console.log(JSON.stringify(report, null, 2));
if (report.errors.length) process.exitCode = 2;
