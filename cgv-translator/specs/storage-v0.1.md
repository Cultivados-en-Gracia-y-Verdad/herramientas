# Storage v0.1

## Purpose

Translator stores investigations as plain Markdown files so the work remains readable without the app.

The app is only a manager over these files.

## Investigation Folder

Example:

cgv-translator/investigations/INV-0001/

Required files:

- README.md
- observations.md
- questions.md
- evidence.md
- research.md
- policy.md
- history.md

## Rule

Markdown files are the source of truth during prototype stage.

The app reads and writes these files.

## Future

If needed later, Translator may add a database, but the first version should remain file-based.