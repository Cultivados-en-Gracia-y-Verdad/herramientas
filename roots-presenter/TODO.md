# CGV Presenter — TODO

Backlog for the `roots-presenter` app. Current release: **1.1.15** (in progress).

## Distribution

- [ ] **macOS notarization** — Signed builds still trigger “app is damaged” on first open for many users. Notarize with Apple and staple the ticket so Gatekeeper accepts normal double-click launch.
- [ ] **Attach Windows build automatically** — CI builds the `.exe` on tag push, but uploading it to the GitHub release is still manual. Wire the workflow to attach `CGV.Presenter-*-Setup.exe` when a release is published.

## Stability & performance

- [ ] **App restarts** — Investigate unexpected restarts during long sessions (memory, uncaught errors, Electron lifecycle).
- [ ] **Large course load** — Profile slow loads with big slide decks and many images; confirm compression/socket tuning holds under real classroom use.

## Presentation

- [ ] **Projector drawing alignment** — Viewport sync improved in 1.1.x; verify stroke position on projector vs tablet across fullscreen, extended display, and different aspect ratios.
- [ ] **S Pen side button** — Automatic detection was disabled as unreliable; revisit a stable toggle for eraser mode if needed on target devices.

## Courses & content

- [ ] **Bundled starter courses** — Only Romanos is bundled today. Decide which courses ship in the installer vs download-only from `curriculo` `main`.
- [ ] **Catalog path aliases** — Romanos uses `Romanos/` locally and `Romanos1-8` on GitHub; confirm alias logic covers future renames without manual manifest edits.
- [ ] **Course update flow** — Test download → update → reload for courses published from `en-borrador` (manifest + slides + PDFs).

## Controller & songs

- [ ] **Song library UX** — Library filter fixed in 1.1.14; review edge cases (nested folders, empty libraries, search + filter together).
- [ ] **Song repository config** — Allow per-library defaults or clearer UI when multiple GitHub song folders are in use.

## Bible references

- [ ] **Popup markup** — Inline verse leak fixed in 1.1.14 (`bible-popup-verse`); spot-check director, stage, and projector views for any remaining layout quirks on long passages.

## Docs & process

- [ ] **App README** — Add a short `README.md` (dev setup, `npm start`, `npm run make:mac`, release tag format `CGV-Presenter-v*`.
- [ ] **Release checklist** — Document: bump version → commit → tag → push → CI → verify both assets on GitHub release.

## Done (1.1.15)

- [x] Course cover image uses full slide area (`cover-slide`)
- [x] Default scripture text color is slightly yellow (comments unchanged)
- [x] Scripture popup centered on screen (presenter, projector, audience)

## Done (1.1.14)

- [x] Bible reference popup showing verse text inline in slides
- [x] Controller song library dropdown filtering
- [x] Romanos “not downloaded” when installed from bundled library
- [x] macOS zip + GUI installer in release bundle
- [x] GitHub Actions build for macOS and Windows
