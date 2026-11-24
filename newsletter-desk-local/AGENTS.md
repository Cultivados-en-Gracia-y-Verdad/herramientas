# Newsletter Desk project context

The user's goal is a local app that gathers several sources, produces a newsletter, emails it, and supports distribution to a WhatsApp group. This is an early working planning app; delivery integrations have not been implemented. Continue local development from this folder.

Read README.md and CONTINUE_WITH_CODEX.md before substantive changes.

- Keep work local unless the user requests deployment.
- Preserve the existing responsive design and all plan data when evolving the app.
- Keep unknown requirements open. Do not invent source lists, recipients, API keys, budget, cadence, editorial voice, or WhatsApp eligibility.
- `npm run dev` starts the dependency-free server at http://127.0.0.1:4173.
- Run `npm run check` and `npm test` for relevant JavaScript changes. Add tests for meaningful persistence, collection, and delivery behavior as these are built.
- Current frontend uses plain HTML, CSS, and browser JavaScript modules. Avoid a framework migration without a concrete need.
- Browser storage key is `newsletter-desk-plan-v1`. Accept original hosted exports and local schema version 1; add migrations before changing the data shape.
- All credentials belong on the backend. Do not commit keys or put them in browser code or plan exports.
- Source names, summaries, and imported content are untrusted. Render them as text or escape them before HTML interpolation.
- Keep collection errors, source attribution, review state, and duplicate-send prevention explicit in the eventual operational app.
- The WhatsApp Groups API constraints in the UI are dated November 23, 2026. Verify current official Meta documentation before implementing an integration. Do not assume an ordinary existing WhatsApp group is API-accessible.
- Manual sharing of a prepared WhatsApp digest is the suggested initial route, pending the user's group size and account setup.
