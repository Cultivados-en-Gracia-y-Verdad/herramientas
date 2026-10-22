import express from 'express';
import path from 'node:path';
import { migrate, openDatabase, projectRoot } from './db.js';

const db = openDatabase();
migrate(db);
const app = express();
app.use(express.json({ limit: '1mb' }));

const allowedStatuses = {
  textual_review_status: ['unreviewed', 'in_progress', 'reviewed'],
  predictive_statement_status: ['undetermined', 'predictive', 'not_clearly_predictive'],
  fulfillment_assessment_status: ['not_assessed', 'no_fulfillment_identified', 'proposed_fulfillment', 'textually_linked_fulfillment', 'disputed', 'undetermined']
} as const;

app.get('/api/health', (_req, res) => res.json({ ok: true }));
app.get('/api/stats', (_req, res) => {
  const counts = db.prepare(`SELECT COUNT(*) total,
    SUM(textual_review_status='reviewed') reviewed,
    SUM(predictive_statement_status='predictive') predictive,
    SUM(predictive_statement_status='not_clearly_predictive') notPredictive
    FROM passages`).get();
  res.json(counts);
});

app.get('/api/passages', (req, res) => {
  const q = String(req.query.q || '').trim();
  const review = String(req.query.review || '');
  const predictive = String(req.query.predictive || '');
  const book = String(req.query.book || '');
  const params: string[] = [];
  const where = ['1=1'];
  if (q) { where.push(`(p.original_reference LIKE ? OR p.review_notes LIKE ? OR s.original_source_id LIKE ?)`); params.push(`%${q}%`, `%${q}%`, `%${q}%`); }
  if (review) { where.push('p.textual_review_status = ?'); params.push(review); }
  if (predictive) { where.push('p.predictive_statement_status = ?'); params.push(predictive); }
  if (book) { where.push('p.book = ?'); params.push(book); }
  const rows = db.prepare(`SELECT p.id, p.original_reference, p.book, p.textual_review_status,
    p.predictive_statement_status, p.fulfillment_assessment_status, p.updated_at,
    s.source_name, s.original_source_id,
    (SELECT COUNT(*) FROM predictive_statements ps WHERE ps.passage_id=p.id) statement_count
    FROM passages p JOIN source_records s ON s.id=p.source_record_id
    WHERE ${where.join(' AND ')} ORDER BY p.id LIMIT 1000`).all(...params);
  res.json(rows);
});

app.get('/api/books', (_req, res) => res.json(db.prepare('SELECT DISTINCT book FROM passages WHERE book IS NOT NULL ORDER BY book').all()));

app.get('/api/passages/:id', (req, res) => {
  const passage = db.prepare(`SELECT p.*, s.source_name, s.original_source_id, s.original_source_url,
    s.original_classification, s.original_fulfillment_claim, s.payne_mapping, s.imported_metadata
    FROM passages p JOIN source_records s ON s.id=p.source_record_id WHERE p.id=?`).get(req.params.id) as Record<string, unknown> | undefined;
  if (!passage) return res.status(404).json({ error: 'Passage not found' });
  passage.statements = db.prepare('SELECT * FROM predictive_statements WHERE passage_id=? ORDER BY id').all(req.params.id);
  passage.history = db.prepare(`SELECT * FROM review_history WHERE entity_type='passage' AND entity_id=? ORDER BY id DESC`).all(req.params.id);
  res.json(passage);
});

app.put('/api/passages/:id/review', (req, res) => {
  const id = Number(req.params.id);
  const current = db.prepare('SELECT * FROM passages WHERE id=?').get(id) as Record<string, unknown> | undefined;
  if (!current) return res.status(404).json({ error: 'Passage not found' });
  const assessmentFields = ['textual_review_status', 'predictive_statement_status', 'fulfillment_assessment_status'] as const;
  const fields = [...assessmentFields, 'review_notes'] as const;
  for (const field of assessmentFields) {
    const value = req.body[field];
    if (!(allowedStatuses[field] as readonly string[]).includes(value)) return res.status(400).json({ error: `Invalid ${field}` });
  }
  const notes = String(req.body.review_notes ?? '');
  db.exec('BEGIN');
  try {
    for (const field of fields) {
      const next = field === 'review_notes' ? notes : req.body[field];
      if (String(current[field] ?? '') !== String(next ?? '')) {
        db.prepare(`INSERT INTO review_history(entity_type, entity_id, field_name, previous_value, new_value, evidence, reviewer_notes, conclusion_level)
          VALUES ('passage', ?, ?, ?, ?, ?, ?, ?)`)
          .run(id, field, String(current[field] ?? ''), String(next ?? ''), req.body.evidence || null, req.body.change_notes || null, req.body.conclusion_level || 'undetermined');
      }
    }
    db.prepare(`UPDATE passages SET textual_review_status=?, predictive_statement_status=?, fulfillment_assessment_status=?, review_notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?`)
      .run(req.body.textual_review_status, req.body.predictive_statement_status, req.body.fulfillment_assessment_status, notes, id);
    db.exec('COMMIT');
  } catch (error) { db.exec('ROLLBACK'); throw error; }
  res.json({ ok: true });
});

app.post('/api/passages/:id/statements', (req, res) => {
  const passage = db.prepare('SELECT id FROM passages WHERE id=?').get(req.params.id);
  if (!passage) return res.status(404).json({ error: 'Passage not found' });
  const description = String(req.body.description || '').trim();
  if (!description) return res.status(400).json({ error: 'Statement description is required' });
  const result = db.prepare(`INSERT INTO predictive_statements
    (passage_id, description, explicitness, speaker, addressee, subject, predicted_action, temporal_expression, announcement_time, predicted_time, evidence_notes, review_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
    .run(req.params.id, description, req.body.explicitness || 'undetermined', req.body.speaker || null, req.body.addressee || null,
      req.body.subject || null, req.body.predicted_action || null, req.body.temporal_expression || null, req.body.announcement_time || null,
      req.body.predicted_time || null, req.body.evidence_notes || null, req.body.review_status || 'draft');
  res.status(201).json({ id: Number(result.lastInsertRowid) });
});

if (process.env.NODE_ENV === 'production') {
  app.use(express.static(path.join(projectRoot, 'dist')));
  app.use((_req, res) => res.sendFile(path.join(projectRoot, 'dist', 'index.html')));
}
const port = Number(process.env.PORT || 4174);
app.listen(port, () => console.log(`Scripture Prophecy Explorer API listening on http://localhost:${port}`));
