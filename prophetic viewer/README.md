# Scripture Prophecy Explorer

A local-first research application for reviewing candidate biblical prophecies while keeping textual findings, inferences, hypotheses, and imported source claims distinct.

## Current scope

Phase 1 is implemented:

- SQLite persistence with versioned migrations
- idempotent CSV/XLSX/XLS catalog importer with provenance and error reporting
- searchable and filterable candidate list
- passage review workspace with persistent statuses and notes
- zero-to-many predictive statements per passage
- hidden-by-default source classifications and fulfillment claims
- immutable review history for changed passage assessments
- normalized foundations for events, relationships, fulfillment assessments, evidence, and research topics
- integrity tests for the principal evidence rules

The supplied 873-record dataset was not present when this project was created. No substitute records were generated.

## Requirements and setup

- Node.js 22.5 or newer (the app uses Node's built-in SQLite module)

```bash
npm install
npm run migrate
```

## Importing the catalog

Place the source file anywhere convenient (the recommended location is `data/import/`, which is intentionally not required). Then run:

```bash
npm run import -- data/import/biblical_prediction_catalog_873.xlsx
```

You can give a stable source name as a second argument:

```bash
npm run import -- data/import/biblical_prediction_catalog_873.csv biblical-prediction-catalog
```

The importer recognizes common column names for source ID, Scripture reference, study URL, classification, fulfillment claim, and Payne mapping. It stores every original column in `imported_metadata`, reports rows missing an ID or Scripture reference, and uses `(source name, original source ID)` as its duplicate key. Reimport updates source metadata but never overwrites independent review fields.

After importing, confirm the JSON report says `totalRows: 873` and `skipped: 0`. Any listed error needs correction in the source file rather than fabricated replacement data.

## Running

Development mode (frontend and API with live reload):

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

Production build:

```bash
npm run build
npm start
```

Open [http://localhost:4174](http://localhost:4174). Set `DB_PATH` to use a database outside the default `data/prophecy.sqlite`, and `PORT` to change the API port.

## Tests

```bash
npm test
```

## Evidence rules

- A catalog entry is only a candidate; its imported classifications and fulfillment claims remain source metadata.
- New passages begin `unreviewed`, `undetermined`, and `not_assessed`.
- Source commentary stays hidden during the initial textual review unless a reviewer explicitly reveals it.
- `No fulfillment identified` is distinct from an assertion that something is “not yet fulfilled.”
- Unknown chronology remains unknown; canon order is never converted into a date.
- Each review change creates a history record. Reimports do not erase review work.
- Biblical text is shown only when a named text source is attached. The application does not invent or silently substitute a translation.

## Later phases

The migration contains the core tables needed for Phase 2, but complete event editing, fulfillment evidence workflows, and relationship review interfaces remain to be built. The layered timeline and partial-order events visualization are Phase 3. Original-language providers and linguistic datasets are reserved for Phase 4; there is no automated prophecy detector.
