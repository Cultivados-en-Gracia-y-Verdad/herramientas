PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_records (
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  original_source_id TEXT NOT NULL,
  scripture_reference TEXT NOT NULL,
  original_source_url TEXT,
  original_classification TEXT,
  original_fulfillment_claim TEXT,
  payne_mapping TEXT,
  imported_metadata TEXT NOT NULL DEFAULT '{}',
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_name, original_source_id)
);

CREATE TABLE IF NOT EXISTS passages (
  id INTEGER PRIMARY KEY,
  source_record_id INTEGER NOT NULL UNIQUE REFERENCES source_records(id) ON DELETE RESTRICT,
  book TEXT,
  chapter_start INTEGER,
  verse_start INTEGER,
  chapter_end INTEGER,
  verse_end INTEGER,
  original_reference TEXT NOT NULL,
  normalized_reference TEXT,
  text_source TEXT,
  passage_text TEXT,
  original_language_url TEXT,
  clause_data_url TEXT,
  textual_review_status TEXT NOT NULL DEFAULT 'unreviewed' CHECK(textual_review_status IN ('unreviewed','in_progress','reviewed')),
  predictive_statement_status TEXT NOT NULL DEFAULT 'undetermined' CHECK(predictive_statement_status IN ('undetermined','predictive','not_clearly_predictive')),
  fulfillment_assessment_status TEXT NOT NULL DEFAULT 'not_assessed' CHECK(fulfillment_assessment_status IN ('not_assessed','no_fulfillment_identified','proposed_fulfillment','textually_linked_fulfillment','disputed','undetermined')),
  review_notes TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictive_statements (
  id INTEGER PRIMARY KEY,
  passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  assessment TEXT NOT NULL DEFAULT 'undetermined',
  explicitness TEXT NOT NULL DEFAULT 'undetermined' CHECK(explicitness IN ('explicit','inferred','hypothetical','undetermined')),
  conditionality TEXT,
  speaker TEXT,
  addressee TEXT,
  subject TEXT,
  predicted_action TEXT,
  temporal_expression TEXT,
  announcement_time TEXT,
  predicted_time TEXT,
  evidence_notes TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  description TEXT NOT NULL,
  participants TEXT,
  category TEXT,
  status TEXT NOT NULL DEFAULT 'undetermined',
  chronology TEXT,
  evidence_references TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS prediction_events (
  predictive_statement_id INTEGER NOT NULL REFERENCES predictive_statements(id) ON DELETE CASCADE,
  event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  association_type TEXT NOT NULL DEFAULT 'proposed',
  evidence_notes TEXT,
  PRIMARY KEY (predictive_statement_id, event_id)
);

CREATE TABLE IF NOT EXISTS event_relationships (
  id INTEGER PRIMARY KEY,
  event_a_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  event_b_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL CHECK(relationship_type IN ('before','after','during','overlaps','simultaneous','possibly_same','same_supported','undetermined')),
  evidence_level TEXT NOT NULL CHECK(evidence_level IN ('explicit','inferred','hypothetical')),
  supporting_passages TEXT,
  reasoning_notes TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft',
  CHECK(event_a_id <> event_b_id)
);

CREATE TABLE IF NOT EXISTS fulfillment_assessments (
  id INTEGER PRIMARY KEY,
  predictive_statement_id INTEGER NOT NULL REFERENCES predictive_statements(id) ON DELETE CASCADE,
  event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
  status TEXT NOT NULL CHECK(status IN ('not_assessed','no_fulfillment_identified','proposed_fulfillment','textually_linked_fulfillment','disputed','undetermined')),
  evidence_level TEXT NOT NULL DEFAULT 'hypothetical',
  evidence_notes TEXT,
  review_status TEXT NOT NULL DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS research_topics (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT);
CREATE TABLE IF NOT EXISTS statement_topics (
  statement_id INTEGER NOT NULL REFERENCES predictive_statements(id) ON DELETE CASCADE,
  topic_id INTEGER NOT NULL REFERENCES research_topics(id) ON DELETE CASCADE,
  PRIMARY KEY(statement_id, topic_id)
);

CREATE TABLE IF NOT EXISTS review_history (
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  previous_value TEXT,
  new_value TEXT,
  evidence TEXT,
  reviewer_notes TEXT,
  conclusion_level TEXT CHECK(conclusion_level IN ('explicit','inferred','hypothetical','undetermined')),
  changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_source_reference ON source_records(scripture_reference);
CREATE INDEX IF NOT EXISTS idx_passage_status ON passages(textual_review_status, predictive_statement_status);
CREATE INDEX IF NOT EXISTS idx_statement_passage ON predictive_statements(passage_id);
