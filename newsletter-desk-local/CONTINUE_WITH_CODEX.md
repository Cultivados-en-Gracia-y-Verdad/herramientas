# Continue development

## Paste this into your next local Codex session

> Continue this local Newsletter Desk project. Read AGENTS.md and README.md, inspect the code, and run the existing checks. The goal is to evolve this planning workspace into an app that gathers selected sources, drafts a newsletter with original links, supports review, sends email, and prepares a WhatsApp group digest. Keep work local. The initial local JSON persistence and on-demand RSS/Atom/iCalendar collection pipeline are implemented with attribution, errors, item records, and duplicate detection. Apple Calendar `webcal://` links are accepted. Ask me for real feed URLs to validate collection. Next, add item selection and explicit editorial review state while keeping the existing UI and plan import compatible. Do not add AI summaries or live sending until the relevant provider, editorial expectations, recipients, and email provider are configured. Keep manual WhatsApp sharing as the initial route unless current official API eligibility and group limits fit my setup.

This is a suggested next task, not a record of features already implemented or of a selected database/provider.

## Current state

The frontend runs locally with a built-in Node HTTP server. Browser storage holds the compatible schema-version-1 plan. JSON import supports moving data from the original hosted site. The UI provides source management, on-demand RSS/Atom/iCalendar collection, collected article and event records, email/WhatsApp editing and preview, scheduling preferences, delivery choices, and unresolved decisions.

The server stores collected items and the latest 50 collection runs in ignored local file `data/newsletter-desk.json`. Collection keeps attribution, dates, unreviewed state, explicit per-source errors, and stable duplicate detection. It fetches sources marked `RSS feed` or `Calendar feed` when the user clicks Collect sources; `webcal://` is converted to HTTPS only for fetching. No AI service, editorial selection state, mailing list, background scheduler, email sender, or WhatsApp integration exists yet. `Build an outline` still produces placeholders from planned source labels and URLs.

## Proposed implementation order

1. **Local persistence (initial slice complete):** collected articles and run history use a local JSON store; the browser plan and hosted import remain compatible. Before broadening operational data, decide whether the file store remains sufficient or needs SQLite.
2. **Collection (initial slice complete):** selected RSS/Atom and iCalendar feeds retain source URLs and dates, report errors, and deduplicate items. Next, test with the user's real feed URLs and decide separately how permitted websites, newsletters, and documents are acquired.
3. **Editorial workflow (next):** allow article selection, preserve original links, track draft/approved states, and create evidence-based summaries through a configurable AI provider only if desired.
4. **Email:** configure the chosen provider, sender, opted-in recipients, unsubscribe handling, test sends, logs, and idempotency before real distribution.
5. **Scheduling:** implement collection/review/release timing and time zones after cadence is chosen. A local scheduler requires the machine and process to remain running; discuss hosting only if unattended availability is needed.
6. **WhatsApp:** keep copy-and-share as the initial implementation. Assess official group automation against current Meta documentation and the user's actual group/account. Do not equate the Business app with Groups API eligibility.

## Open requirements

- Actual source URLs and access permissions
- Newsletter audience, topics, language, voice, length, and archive location
- Collection window, schedule, time zone, and review owner
- AI provider and summarization preferences, if any
- Email service, sender domain, subscriber count, and subscriber management
- WhatsApp group size, existing/new group, account status, and delivery preference
- Budget and whether the local machine will remain online for scheduled work

## Handoff validation

Run `npm run check` and `npm test`. The tests exercise plan compatibility, invalid import rejection, asset serving, and project-file isolation. Browser layout and interactive clicks need local visual verification.
