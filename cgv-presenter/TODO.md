# CGV Presenter — TODO

Backlog for the `cgv-presenter` app. Current release: **1.2.7**.

## Distribution

- [ ] **macOS notarization** — Signed builds still trigger “app is damaged” on first open for many users. Notarize with Apple and staple the ticket so Gatekeeper accepts normal double-click launch.
- [ ] **Attach Windows build automatically** — CI builds the `.exe` on tag push, but uploading it to the GitHub release is still manual. Wire the workflow to attach `CGV.Presenter-*-Setup.exe` when a release is published.
- [x] **Windows Firewall LAN rule** — Squirrel install/update adds inbound TCP 3000 (`CGV Presenter LAN`); uninstall removes it. View menu has a manual “Allow Windows Firewall access…” recovery action.

## Stability & performance

- [ ] **App restarts** — Investigate unexpected restarts during long sessions (memory, uncaught errors, Electron lifecycle).
- [ ] **Large course load** — Profile slow loads with big slide decks and many images; confirm compression/socket tuning holds under real classroom use.

## Presentation

- [x] **Markdown chain animation** — List lines like `* *A* → *B* → *C*` or `* *A* ↓ *B* ↓ *C*` reveal one term per advance (horizontal/vertical); plain manuals stay readable.
- [ ] **Projector drawing alignment** — Viewport sync improved in 1.1.x; verify stroke position on projector vs tablet across fullscreen, extended display, and different aspect ratios.
- [ ] **S Pen side button** — Automatic detection was disabled as unreliable; revisit a stable toggle for eraser mode if needed on target devices.
- [ ] **Stage view design** — Deferred; refine from real use rather than a redesign pass now.

## Courses & content

- [ ] **Bundled starter courses** — Only Romanos is bundled today. Decide which courses ship in the installer vs download-only from `cgv-data` `main`.
- [ ] **Catalog path aliases** — Romanos uses `Romanos/` locally and `Romanos1-8` on GitHub; confirm alias logic covers future renames without manual manifest edits.
- [ ] **Course update flow** — Test download → update → reload for courses published from `en-borrador` (manifest + slides + PDFs).

## Controller & songs

- [x] **Song search** — Accent-insensitive match (`senor` → señor), keep numbered/folder copies (no title-only dedupe), keep search query when changing library filter.
- [x] **Device / Esc+Enter** — Esc (blank) and Enter (send live) work even while song search is focused; selecting a song blurs search so arrows work. On phones: tap song twice = Enter; tap a background = digit+Esc; Blank/Send Live stay fixed at the bottom.
- [x] **Phone controller UX** — Fullscreen, 16:9 preview, title-only screen chips, 0–9 live backgrounds, default blank, teaching-mode preview, return-to-teaching cleanup.
- [x] **Backgrounds on key press** — Keys/buttons 1–9 and 0 switch live backgrounds without blanking lyrics (accepted as-is).
- [x] **Director on devices** — Preview text stays in-bounds; song search matches controller (accents + library filter); one-verse popups sync across views.
- [x] **Director session lag** — Avoid full font re-fit every step (binary search + reuse prior size); skip fit when content unchanged; defer song catalog load; share state payloads across non-audience sockets.
- [x] **Startup layout preference** — Settings → Startup: Presenter+projector, Controller+projector, or Projector only (output on second display when available).
- [x] **Controller desktop preview** — Windowed and fullscreen preview fill correctly without crushing verse thumbnails; phones unchanged.
- [ ] **Song library UX** — Review remaining edge cases (nested folders, empty libraries).
- [ ] **Song repository config** — Allow per-library defaults or clearer UI when multiple GitHub song folders are in use.
- [x] **Song background contrast** — Darken the media scrim while lyrics are live; remove it on Esc/blank so the default background shows clean.
- [x] **Teaching titles in songs** — Clear the editorial H2/H3 folio when song/blank output is on the projector so teaching titles do not leak over lyrics.

## Bible references

- [x] **One-verse popups** — Show a single verse at a time with ‹ › controls; sync by `verseIndex` across presenter, director, projector, and audience (replaces fragile scroll sync).
- [ ] **Popup markup** — Spot-check director, stage, and projector views for remaining layout quirks on long single verses.
- [x] **Greek word popups** — Click Greek → Spanish gloss, morphology, and same-morphology NT examples (lazy `/greek/usage`); connectors keep pedagogical footnotes; `(λέγων)[^P]` splits usage + participle note.
- [x] **Hebrew word popups** — Click Hebrew → Spanish gloss, OSHB morphology, and same-morphology OT examples (lazy `/hebrew/usage`); same header layout as Greek (`Spanish — Hebrew (lemma)` + Uso + version under verse).

## Docs & process

- [ ] **App README** — Add a short `README.md` (dev setup, `npm start`, `npm run make:mac`, release tag format `CGV-Presenter-v*`.
- [ ] **Release checklist** — Document: bump version → commit → tag → push → CI → verify both assets on GitHub release.

## Done (1.2.2)

- [x] Markdown chain animation (`→` / `↓` list lines reveal term-by-term)
- [x] Song background contrast: darker media scrim with lyrics; clean image on Esc/blank
- [x] Teaching titles cleared from projector when songs / blank are live

## Done (1.2.1)

- [x] Projector text fit uses the current reveal step only (not lookahead across the whole blank-line slide)

- [x] Import teaching markdown for one-off speaking engagements
- [x] Course cover image uses full slide area (`cover-slide`)
- [x] Default scripture text color is yellow on H4/italics (commentary unchanged)
- [x] Definition boxes with readable contrast on presenter and projector
- [x] Scripture popup centered on screen (presenter, projector, audience)

## Done (1.1.14)

- [x] Bible reference popup showing verse text inline in slides
- [x] Controller song library dropdown filtering
- [x] Romanos “not downloaded” when installed from bundled library
- [x] macOS zip + GUI installer in release bundle
- [x] GitHub Actions build for macOS and Windows
