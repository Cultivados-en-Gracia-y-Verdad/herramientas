import { afterEach, describe, expect, it } from 'vitest';
import type { DatabaseSync } from 'node:sqlite';
import { migrate, openDatabase } from '../server/db.js';
import { importRows } from '../server/importer.js';
import { findChronologyCycle } from '../server/chronology.js';

let db: DatabaseSync | undefined;
afterEach(() => { db?.close(); db = undefined; });
function setup() { db = openDatabase(':memory:'); migrate(db); return db; }
function sample(id = '17') { return { ID: id, 'Scripture Reference': 'Isaiah 7:14', Fulfillment: 'Claimed fulfilled', Classification: 'Messianic' }; }

const preparedCatalogRow = { 'Record ID': '33', 'Scripture reference': 'Isaiah 9:6', 'Payne mapping — source': 'Isa 123', 'Topic category — source': 'Messianic', 'Fulfillment status — source': 'Fulfilled', 'Study URL': 'https://example.test/study' };

describe('catalog integrity', () => {
  it('preserves all 873 records and original IDs, including gaps', () => {
    const database = setup();
    const rows = Array.from({ length: 873 }, (_, i) => sample(String(i < 400 ? i + 1 : i + 2)));
    const report = importRows(database, rows, 'test-catalog');
    expect(report.imported).toBe(873);
    expect((database.prepare('SELECT COUNT(*) count FROM source_records').get() as {count:number}).count).toBe(873);
    expect(database.prepare(`SELECT 1 FROM source_records WHERE original_source_id='402'`).get()).toBeTruthy();
    expect(database.prepare(`SELECT 1 FROM source_records WHERE original_source_id='401'`).get()).toBeFalsy();
  });

  it('reimports idempotently without overwriting independent review fields', () => {
    const database = setup(); importRows(database, [sample()], 'catalog');
    database.prepare(`UPDATE passages SET predictive_statement_status='predictive', review_notes='Textual finding'`).run();
    const report = importRows(database, [{ ...sample(), Classification: 'Changed externally' }], 'catalog');
    expect(report.updated).toBe(1);
    expect((database.prepare('SELECT COUNT(*) count FROM source_records').get() as {count:number}).count).toBe(1);
    const passage = database.prepare('SELECT predictive_statement_status, review_notes FROM passages').get() as Record<string,string>;
    expect(passage).toMatchObject({ predictive_statement_status: 'predictive', review_notes: 'Textual finding' });
  });

  it('keeps external fulfillment claims out of reviewed assessments', () => {
    const database = setup(); importRows(database, [sample()], 'catalog');
    const source = database.prepare('SELECT original_fulfillment_claim FROM source_records').get() as Record<string,string>;
    const passage = database.prepare('SELECT fulfillment_assessment_status FROM passages').get() as Record<string,string>;
    expect(source.original_fulfillment_claim).toBe('Claimed fulfilled');
    expect(passage.fulfillment_assessment_status).toBe('not_assessed');
  });

  it('maps the prepared catalog source-qualified headers', () => {
    const database = setup(); importRows(database, [preparedCatalogRow], 'catalog');
    const source = database.prepare('SELECT * FROM source_records').get() as Record<string,string>;
    expect(source).toMatchObject({ original_source_id: '33', payne_mapping: 'Isa 123', original_classification: 'Messianic', original_fulfillment_claim: 'Fulfilled', original_source_url: 'https://example.test/study' });
  });

  it('supports multiple statements per passage and many-to-many event associations', () => {
    const database = setup(); importRows(database, [sample()], 'catalog');
    const passage = (database.prepare('SELECT id FROM passages').get() as {id:number}).id;
    database.prepare('INSERT INTO predictive_statements(passage_id, description) VALUES (?, ?)').run(passage, 'Statement one');
    database.prepare('INSERT INTO predictive_statements(passage_id, description) VALUES (?, ?)').run(passage, 'Statement two');
    database.prepare(`INSERT INTO events(description) VALUES ('Event one'), ('Event two')`).run();
    database.prepare('INSERT INTO prediction_events VALUES (1, 1, ?, NULL), (1, 2, ?, NULL), (2, 1, ?, NULL)').run('proposed', 'proposed', 'proposed');
    expect((database.prepare('SELECT COUNT(*) count FROM predictive_statements').get() as {count:number}).count).toBe(2);
    expect((database.prepare('SELECT COUNT(*) count FROM prediction_events').get() as {count:number}).count).toBe(3);
  });

  it('preserves unknown dates and keeps topic tags from creating event links', () => {
    const database = setup(); importRows(database, [sample()], 'catalog');
    const passage = (database.prepare('SELECT id FROM passages').get() as {id:number}).id;
    database.prepare(`INSERT INTO predictive_statements(passage_id, description) VALUES (?, 'Unknown date')`).run(passage);
    database.prepare(`INSERT INTO research_topics(name) VALUES ('Resurrection events')`).run();
    database.prepare('INSERT INTO statement_topics VALUES (1,1)').run();
    expect((database.prepare('SELECT predicted_time FROM predictive_statements').get() as {predicted_time:null}).predicted_time).toBeNull();
    expect((database.prepare('SELECT COUNT(*) count FROM prediction_events').get() as {count:number}).count).toBe(0);
  });
});

describe('relative chronology', () => {
  it('works without absolute dates and flags contradictory cycles', () => {
    expect(findChronologyCycle([{ eventA: 1, eventB: 2, type: 'before' }])).toBeNull();
    expect(findChronologyCycle([{ eventA: 1, eventB: 2, type: 'before' }, { eventA: 2, eventB: 3, type: 'before' }, { eventA: 3, eventB: 1, type: 'before' }])).toEqual([1, 2, 3, 1]);
  });
});
