import { readFile } from "node:fs/promises";
import { join } from "node:path";

const DEFAULT_OPENAI_MODEL = process.env.CGV_TRANSLATOR_OPENAI_MODEL || "gpt-4.1-mini";
const DEFAULT_ANTHROPIC_MODEL = process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || "claude-sonnet-4-5";

export async function loadTranslatorEnv(rootDir) {
  const envPath = join(rootDir, ".env");
  const content = await readFile(envPath, "utf8").catch(() => "");
  if (!content) return;

  for (const rawLine of content.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;
    const [, key, rawValue] = match;
    if (process.env[key] != null && process.env[key] !== "") continue;
    let value = rawValue.trim();
    if (
      (value.startsWith("\"") && value.endsWith("\""))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

function getAiConfig() {
  const anthropicKey = process.env.ANTHROPIC_API_KEY || process.env.CGV_ANTHROPIC_API_KEY || "";
  const openaiKey = process.env.OPENAI_API_KEY || process.env.CGV_OPENAI_API_KEY || "";

  if (anthropicKey) {
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL
    };
  }

  if (openaiKey) {
    return {
      provider: "openai",
      apiKey: openaiKey,
      model: process.env.CGV_TRANSLATOR_OPENAI_MODEL || DEFAULT_OPENAI_MODEL
    };
  }

  return null;
}

function formatTokenRows(tokenRows = []) {
  return tokenRows
    .map((row, index) => {
      const parts = [
        `${index + 1}.`,
        row.greek || "—",
        `lemma=${row.lemma || "—"}`,
        `morph=${row.rmac || row.morphology || "—"}`,
        `ble=${row.ble || "—"}`
      ];
      if (row.rv1909) parts.push(`rv1909=${row.rv1909}`);
      return parts.join(" | ");
    })
    .join("\n");
}

function buildPrompt({
  reference,
  greek,
  tokenRows,
  rv1909Text,
  bleText,
  priorLbf = []
}) {
  const priorBlock = priorLbf.length
    ? priorLbf.map(item => `- ${item.reference}: ${item.spanish}`).join("\n")
    : "(none yet)";

  return `You assist La Biblia Fiel (LBF), a fresh Spanish Bible translation.

Rules:
- Translate from the Greek phrase itself.
- Be simple, precise, and contemporary Spanish.
- Preserve meaning, grammar, and open tensions in the source.
- Do not add words absent from the Greek (for example do not insert "misericordia" if ἔλεος is not present).
- Do not copy RV1909 wording. RV1909 is consultative only.
- BLE is a mechanical gloss diagnostic, not polished Spanish.
- Prefer natural phrase flow over word-for-word stiffness.
- Divine possessives may use capitalized Su/Sus when clearly referring to God.
- Return ONLY the Spanish proposal for this phrase. No quotes, no commentary, no alternatives.

Reference: ${reference}
Greek phrase: ${greek || "—"}

Token rows:
${formatTokenRows(tokenRows) || "(none)"}

BLE mechanical (diagnostic): ${bleText || "—"}
RV1909 (consultative only): ${rv1909Text || "—"}

Already approved LBF nearby:
${priorBlock}

Spanish proposal:`;
}

async function callOpenAi({ apiKey, model, prompt }) {
  const response = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      temperature: 0.2,
      messages: [
        {
          role: "system",
          content: "You propose faithful contemporary Spanish for La Biblia Fiel. Output only the Spanish phrase."
        },
        { role: "user", content: prompt }
      ]
    })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || `OpenAI request failed (${response.status})`);
  }

  const text = body?.choices?.[0]?.message?.content;
  if (!text || !String(text).trim()) {
    throw new Error("OpenAI returned an empty suggestion.");
  }
  return String(text).trim();
}

async function callAnthropic({ apiKey, model, prompt }) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model,
      max_tokens: 300,
      temperature: 0.2,
      messages: [{ role: "user", content: prompt }]
    })
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || `Anthropic request failed (${response.status})`);
  }

  const text = (body?.content || [])
    .filter(part => part?.type === "text")
    .map(part => part.text)
    .join("")
    .trim();
  if (!text) {
    throw new Error("Anthropic returned an empty suggestion.");
  }
  return text;
}

function cleanProposal(text) {
  return String(text || "")
    .trim()
    .replace(/^["«“]|["»”]$/gu, "")
    .replace(/^Spanish proposal:\s*/iu, "")
    .replace(/\s+/gu, " ")
    .trim();
}

export function describeAiAvailability() {
  const config = getAiConfig();
  if (!config) {
    return {
      available: false,
      message: "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in cgv-translator/.env"
    };
  }
  return {
    available: true,
    provider: config.provider,
    model: config.model
  };
}

export async function suggestPhraseTranslation(input) {
  const config = getAiConfig();
  if (!config) {
    const error = new Error(
      "No AI API key configured. Add ANTHROPIC_API_KEY or OPENAI_API_KEY to cgv-translator/.env"
    );
    error.code = "AI_NOT_CONFIGURED";
    throw error;
  }

  const prompt = buildPrompt(input);
  const raw = config.provider === "anthropic"
    ? await callAnthropic({ apiKey: config.apiKey, model: config.model, prompt })
    : await callOpenAi({ apiKey: config.apiKey, model: config.model, prompt });

  return {
    proposal: cleanProposal(raw),
    provider: config.provider,
    model: config.model,
    suggestionSource: "ai-proposed"
  };
}
