# The Newsletter Desk — local edition

A local, editable version of the newsletter planning site, packaged for continued development with Codex.

## Run locally

Install Node.js 22 or newer, unzip the project, and open a terminal in the `newsletter-desk-local` folder:

```sh
npm run dev
```

Open **http://127.0.0.1:4173**. Stop with **Ctrl+C**. There are no dependencies to install and no build step. Refresh the browser after editing files. The server listens only on this computer.

Always use the same address and port: browser data belongs to that origin. `localhost` and `127.0.0.1` have separate storage. If 4173 is occupied, stop the other process or set the `PORT` environment variable before running the command.

## Bring your existing plan over

1. In the hosted planning site, click **Export plan** in the browser where you made your edits.
2. Start this local app and click **Import plan**.
3. Select the exported `newsletter-plan.json` file.

Importing replaces the local browser plan after confirmation when it contains data. Export the current plan first if you need a backup. Hosted browser data is not included in this source package and cannot transfer automatically between origins.

## Continue with Codex

Open this extracted folder in your local coding environment with Codex. If using the Codex CLI, run `codex` from this folder. Read `CONTINUE_WITH_CODEX.md` for a ready-to-use continuation prompt and development roadmap. `AGENTS.md` captures project context for the next agent.

Current official references:

- Codex CLI: https://learn.chatgpt.com/docs/codex/cli
- Project instructions: https://learn.chatgpt.com/docs/agent-configuration/agents-md

## What works today

- Manage planned sources, with names, URLs, types, and topics.
- Collect RSS, Atom, and public iCalendar feeds on demand into a local JSON store.
- Accept Apple Calendar `webcal://` links as calendar sources.
- Keep source attribution, dates, collection errors, and deduplicated article or event records.
- Write email and WhatsApp drafts, preview them, and copy text.
- Build a placeholder outline from source names and links.
- Record schedule preferences, delivery options, and unresolved requirements.
- Save in browser storage; export and import the plan as JSON.

This is an early working app. Collection is manual and supports sources explicitly marked `RSS feed` or `Calendar feed`; it does not discover feeds from ordinary websites. Calendar sources may use `webcal://`, `http://`, or `https://`. It does not yet select items for an issue, summarize with AI, run a background schedule, manage subscribers, send email, or post to WhatsApp. No API keys are needed for the current version.

Collected articles and the latest 50 collection runs are stored in `data/newsletter-desk.json`. The `data/` directory is ignored by Git. Plan import/export remains schema version 1 and intentionally does not include collected content.

## Project layout

| File | Purpose |
| --- | --- |
| `public/index.html` | Workspace markup and views |
| `public/styles.css` | Responsive visual design |
| `public/app.js` | Navigation, editing, source management, import/export |
| `public/plan-data.js` | Portable plan validation |
| `scripts/dev.mjs` | Dependency-free local HTTP server |
| `scripts/collection.mjs` | RSS/Atom/iCalendar parsing, deduplication, and local persistence |
| `scripts/plan-data.test.mjs` | Migration and local-server checks |
| `scripts/collection.test.mjs` | Feed parsing, errors, persistence, and duplicate checks |
| `CONTINUE_WITH_CODEX.md` | Current status and suggested next steps |
| `AGENTS.md` | Project guidance for coding agents |

## Check changes

```sh
npm run check
npm test
```

The automated checks cover JavaScript syntax, compatibility with the hosted plan export, rejection of invalid imports, RSS/Atom/iCalendar parsing, `webcal` fetching, attribution, persistence, duplicate detection, collection errors, and the local HTTP API. Verify the responsive layout and click through the workflow in a browser after interface changes.

## Privacy and future integrations

The current app stores edits in browser storage. Keep exported backups. Clearing browser data removes the local plan. Source links and documentation links open external sites when clicked.

When adding integrations, store credentials in server-side environment variables, not frontend JavaScript or exported plans. Preserve explicit review and delivery status, source attribution, and duplicate-send protection.

WhatsApp guidance in the app was checked against Meta's documentation on November 23, 2026. The documented Groups API requires an Official Business Account and eligible Cloud API number, uses API-created invite-only groups, and has a maximum of eight participants. Recheck before implementation:

- https://developers.facebook.com/documentation/business-messaging/whatsapp/groups
- https://developers.facebook.com/documentation/business-messaging/whatsapp/groups/get-started

This local project is independent of Sites hosting and contains no hosting credentials or linked deployment configuration.
