# CGV Translator

CGV Translator is a future translation workspace for producing faithful Bible translations from the biblical languages.

This repository currently exists to document the workflow, specifications, and feature candidates discovered while translating Titus for La Biblia Fiel.

Translator does not replace the translator.

Translator exposes evidence, records decisions, manages history, and assists the human translator in remaining accountable to the biblical text.

## Run the Investigation View Prototype

From this folder:

```sh
npm start
```

Then open:

```text
http://127.0.0.1:1424/
```

### AI phrase suggestions (Ollama)

With no cloud API keys, the prototype uses local [Ollama](https://ollama.com) by default.

```sh
# Install Ollama, then:
ollama pull llama3.2
```

Optional overrides go in `.env` (see `.env.example`). You can also set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` instead.

### Translation pipeline (per-gate)

1. **Analyze phrase** — mechanical Gates 1–5 + grammar skeleton
2. **Propose Spanish** — AI (default `qwen2.5:7b`) drafts modern Spanish under those constraints
3. **Use draft** — copies into working Spanish for human edit/approval

Grammar checks still reject illegal readings (e.g. “fe elegida”). If AI fails checks, the mechanical skeleton is shown instead.

Default local model: `qwen2.5:7b` (set in `.env`). `llama3.2` is too weak for this task.

AI translation discipline lives in:

```text
src/ai/lbf-translation-rules.md
```

The prototype reads and writes plain Markdown files in `investigations/`. During this stage, those Markdown files remain the source of truth.
Investigation Stop Rule

Begin an investigation only when the translation decision cannot be made responsibly from existing project policy.

If an existing policy already answers the question, apply the policy and continue translating.

Investigations exist to establish policy.

Not to repeatedly justify established policy.