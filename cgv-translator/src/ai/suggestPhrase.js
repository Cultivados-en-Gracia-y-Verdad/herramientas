import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const DEFAULT_OPENAI_MODEL = process.env.CGV_TRANSLATOR_OPENAI_MODEL || "gpt-4.1-mini";
const DEFAULT_ANTHROPIC_MODEL = process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || "claude-sonnet-4-5";
const DEFAULT_OLLAMA_MODEL = process.env.CGV_TRANSLATOR_OLLAMA_MODEL || "llama3.2";
const DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434";

const SYSTEM_PROMPT = `You are a pipeline assistant for La Biblia Fiel (LBF).
You are not the final translator.
Work only from Greek lemma, morphology, and context — never start from RV1909 or BLE.
Return valid JSON only matching the requested schema.`;

let translatorRootDir = "";

export async function loadTranslatorEnv(rootDir) {
  translatorRootDir = rootDir;
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

function resolveOllamaBaseUrl() {
  const raw = process.env.CGV_TRANSLATOR_OLLAMA_BASE_URL
    || process.env.OLLAMA_HOST
    || DEFAULT_OLLAMA_BASE_URL;
  return String(raw).replace(/\/$/, "");
}

function getAiConfig() {
  const forced = String(process.env.CGV_TRANSLATOR_PROVIDER || "").trim().toLowerCase();
  const anthropicKey = process.env.ANTHROPIC_API_KEY || process.env.CGV_ANTHROPIC_API_KEY || "";
  const openaiKey = process.env.OPENAI_API_KEY || process.env.CGV_OPENAI_API_KEY || "";
  const ollamaBaseUrl = resolveOllamaBaseUrl();
  const ollamaModel = process.env.CGV_TRANSLATOR_OLLAMA_MODEL || DEFAULT_OLLAMA_MODEL;

  if (forced === "ollama") {
    return { provider: "ollama", baseUrl: ollamaBaseUrl, model: ollamaModel };
  }
  if (forced === "anthropic") {
    if (!anthropicKey) return null;
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL
    };
  }
  if (forced === "openai") {
    if (!openaiKey) return null;
    return {
      provider: "openai",
      apiKey: openaiKey,
      model: process.env.CGV_TRANSLATOR_OPENAI_MODEL || DEFAULT_OPENAI_MODEL
    };
  }

  if (!anthropicKey && !openaiKey) {
    return { provider: "ollama", baseUrl: ollamaBaseUrl, model: ollamaModel };
  }

  if (anthropicKey) {
    return {
      provider: "anthropic",
      apiKey: anthropicKey,
      model: process.env.CGV_TRANSLATOR_ANTHROPIC_MODEL || DEFAULT_ANTHROPIC_MODEL
    };
  }

  return {
    provider: "openai",
    apiKey: openaiKey,
    model: process.env.CGV_TRANSLATOR_OPENAI_MODEL || DEFAULT_OPENAI_MODEL
  };
}

async function loadTranslationRules() {
  if (!translatorRootDir) return "";
  const rulesPath = join(translatorRootDir, "src", "ai", "lbf-translation-rules.md");
  return readFile(rulesPath, "utf8").catch(() => "");
}

function parseDecisionVersions(markdown) {
  const sections = String(markdown || "").split(/^## Version\s+/m).slice(1);
  return sections.map(section => {
    const lines = section.replace(/\r\n/g, "\n").split("\n");
    const fields = {};
    for (const line of lines) {
      const match = line.match(/^([^:]+):\s*(.*)$/);
      if (!match) continue;
      fields[match[1].trim().toLowerCase()] = match[2].trim();
    }
    const reasonMatch = section.match(/### Reason\s*\n([\s\S]*?)(?=\n### |\n## |$)/);
    return {
      status: fields.status || "",
      lemma: fields.lemma || "",
      strongs: fields["strong's"] || fields.strongs || "",
      preferredRendering: fields["preferred rendering"] || "",
      confidence: fields.confidence || "",
      reason: reasonMatch ? reasonMatch[1].trim() : ""
    };
  });
}

async function loadApprovedLemmaPolicies() {
  if (!translatorRootDir) return [];
  const investigationsDir = join(translatorRootDir, "investigations");
  const entries = await readdir(investigationsDir, { withFileTypes: true }).catch(() => []);
  const policies = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || !/^INV-\d{4}$/.test(entry.name)) continue;
    const markdown = await readFile(join(investigationsDir, entry.name, "decision.md"), "utf8").catch(() => "");
    const approved = parseDecisionVersions(markdown)
      .filter(item => /^approved$/i.test(item.status) && item.lemma && item.preferredRendering)
      .at(-1);
    if (!approved) continue;
    policies.push({
      investigationId: entry.name,
      lemma: approved.lemma,
      strongs: approved.strongs,
      preferredRendering: approved.preferredRendering,
      confidence: approved.confidence,
      reason: approved.reason
    });
  }

  return policies;
}

function policiesForTokens(tokenRows = [], policies = []) {
  const byLemma = new Map(policies.map(item => [item.lemma, item]));
  const byStrongs = new Map(
    policies.filter(item => item.strongs).map(item => [item.strongs.toUpperCase(), item])
  );
  const matched = [];
  const missing = [];

  for (const row of tokenRows) {
    const lemma = row.lemma || "";
    const strongs = String(row.strongs || "").toUpperCase();
    if (!lemma && !strongs) continue;
    // Skip light function words from "missing policy" noise when no Strong's.
    const isLight = !strongs && /^(δέ|δὲ|καί|καὶ|ὁ|ἡ|τό|τοῦ|τῆς|τῷ|τῇ|τὸν|τήν|τά|οὐ|μή)$/u.test(lemma);
    const policy = (strongs && byStrongs.get(strongs)) || (lemma && byLemma.get(lemma));
    if (policy) {
      if (!matched.some(item => item.lemma === policy.lemma && item.strongs === policy.strongs)) {
        matched.push(policy);
      }
    } else if (!isLight) {
      missing.push({
        greek: row.greek || "",
        lemma: lemma || "—",
        strongs: strongs || "—"
      });
    }
  }

  return { matched, missing };
}

function formatGreekTokenBlock(tokenRows = []) {
  if (!tokenRows.length) return "(no token rows — use the Greek phrase only)";
  return tokenRows
    .map((row, index) => {
      const lines = [
        `${index + 1}. surface: ${row.greek || "—"}`,
        `   lemma: ${row.lemma || "—"}`,
        `   strongs: ${row.strongs || "—"}`,
        `   morph code: ${row.rmac || row.morphology || "—"}`,
        `   morph note: ${row.morphology || "—"}`
      ];
      return lines.join("\n");
    })
    .join("\n");
}

function formatPolicies(matched = [], missing = []) {
  const matchedBlock = matched.length
    ? matched
      .map(item => {
        const bits = [
          `- ${item.strongs || "—"} ${item.lemma}: prefer "${item.preferredRendering}"`,
          item.confidence ? `(confidence: ${item.confidence})` : "",
          item.investigationId ? `[${item.investigationId}]` : ""
        ].filter(Boolean);
        return bits.join(" ");
      })
      .join("\n")
    : "- (none matched for this phrase)";

  const missingBlock = missing.length
    ? missing.map(item => `- ${item.strongs} ${item.lemma} (${item.greek})`).join("\n")
    : "- (none flagged)";

  return { matchedBlock, missingBlock };
}

function buildPrompt({
  reference,
  greek,
  tokenRows,
  rv1909Text,
  bleText,
  priorLbf = [],
  rulesMarkdown,
  matchedPolicies,
  missingPolicies
}) {
  const priorBlock = priorLbf.length
    ? priorLbf.map(item => `- ${item.reference}: ${item.spanish}`).join("\n")
    : "(none yet)";
  const { matchedBlock, missingBlock } = formatPolicies(matchedPolicies, missingPolicies);

  return `${rulesMarkdown || "Follow LBF Greek-first translation discipline."}

---

TASK
Propose Spanish for ONE phrase. Complete the gates in order before writing proposedSpanish.

Reference: ${reference}
Greek phrase (source of truth): ${greek || "—"}

GATE 1 — Lemma (Greek tokens only; no Spanish translations from RV1909/BLE here)
${formatGreekTokenBlock(tokenRows)}

Approved project lemma policies (authoritative when present):
${matchedBlock}

Lemmas without approved policy (do not invent policy; flag if uncertain):
${missingBlock}

GATE 2 — Morphology
Use each morph code / morph note above. Grammar may constrain Spanish form and relationships. Morphology does not redefine lemma meaning.

GATE 3 — Immediate context
Read the Greek phrase as a unit: connectors, case relationships, and clause role.

GATE 4 — Nearby LBF context (style consistency only; does not override Greek)
${priorBlock}

GATE 5 — Consult last (do NOT copy; do NOT start here)
RV1909 (consultative): ${rv1909Text || "—"}
BLE mechanical (diagnostic only): ${bleText || "—"}

SYNTHESIS
Write proposedSpanish from Gates 1–4.
Preserve every significant Greek token's contribution (including particles when Spanish can carry them).
Do not merge separate Greek words into traditional compounds just because RV1909 does.
If proposedSpanish would match RV1909 word-for-word, re-check the Greek and keep the match only if Greek independently requires those words.
Return JSON only.`;
}

function extractJsonObject(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    // continue
  }
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) {
    try {
      return JSON.parse(fenced[1].trim());
    } catch {
      // continue
    }
  }
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start >= 0 && end > start) {
    try {
      return JSON.parse(raw.slice(start, end + 1));
    } catch {
      return null;
    }
  }
  return null;
}

function cleanProposal(text) {
  return String(text || "")
    .trim()
    .replace(/^["«“]|["»”]$/gu, "")
    .replace(/^Spanish proposal:\s*/iu, "")
    .replace(/^proposedSpanish\s*:\s*/iu, "")
    .replace(/\s+/gu, " ")
    .trim();
}

function normalizeSuggestionPayload(rawText, { matchedPolicies, missingPolicies }) {
  const parsed = extractJsonObject(rawText);
  if (parsed && typeof parsed === "object") {
    const proposal = cleanProposal(
      parsed.proposedSpanish
      || parsed.spanish
      || parsed.proposal
      || ""
    );
    const flags = Array.isArray(parsed.flags)
      ? parsed.flags.map(item => String(item)).filter(Boolean)
      : [];
    if (missingPolicies.length && !flags.some(flag => /policy|lemma/i.test(flag))) {
      flags.push(
        `No approved lemma policy for: ${missingPolicies.map(item => item.lemma).join(", ")}`
      );
    }
    return {
      proposal,
      analysis: {
        lemma: String(parsed.lemma || "").trim(),
        morphology: String(parsed.morphology || parsed.morph || "").trim(),
        context: String(parsed.context || "").trim(),
        flags
      },
      matchedPolicies,
      missingPolicies
    };
  }

  return {
    proposal: cleanProposal(rawText),
    analysis: {
      lemma: "",
      morphology: "",
      context: "",
      flags: missingPolicies.length
        ? [`No approved lemma policy for: ${missingPolicies.map(item => item.lemma).join(", ")}`]
        : ["Model did not return structured gate analysis."]
    },
    matchedPolicies,
    missingPolicies
  };
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
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
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
      max_tokens: 700,
      temperature: 0.2,
      system: SYSTEM_PROMPT,
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

async function callOllama({ baseUrl, model, prompt }) {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        stream: false,
        format: "json",
        options: { temperature: 0.2 },
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: prompt }
        ]
      })
    });
  } catch (error) {
    const wrapped = new Error(
      `Ollama is not reachable at ${baseUrl}. Install from https://ollama.com, then run: ollama pull ${model}`
    );
    wrapped.code = "OLLAMA_UNREACHABLE";
    wrapped.cause = error;
    throw wrapped;
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.error || `Ollama request failed (${response.status})`;
    const error = new Error(String(detail));
    if (/not found|pull/i.test(String(detail))) {
      error.code = "OLLAMA_MODEL_MISSING";
      error.message = `${detail}. Run: ollama pull ${model}`;
    }
    throw error;
  }

  const text = body?.message?.content;
  if (!text || !String(text).trim()) {
    throw new Error("Ollama returned an empty suggestion.");
  }
  return String(text).trim();
}

async function probeOllama(baseUrl) {
  try {
    const response = await fetch(`${baseUrl}/api/tags`, {
      method: "GET",
      signal: AbortSignal.timeout(1500)
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function describeAiAvailability() {
  const config = getAiConfig();
  if (!config) {
    return {
      available: false,
      message:
        "Set CGV_TRANSLATOR_PROVIDER=ollama, or add ANTHROPIC_API_KEY / OPENAI_API_KEY in cgv-translator/.env"
    };
  }

  if (config.provider === "ollama") {
    const reachable = await probeOllama(config.baseUrl);
    if (!reachable) {
      return {
        available: false,
        provider: "ollama",
        model: config.model,
        message:
          `Ollama not running at ${config.baseUrl}. Install from https://ollama.com, then: ollama pull ${config.model}`
      };
    }
  }

  return {
    available: true,
    provider: config.provider,
    model: config.model,
    ...(config.provider === "ollama" ? { baseUrl: config.baseUrl } : {})
  };
}

async function callProvider(config, prompt) {
  if (config.provider === "ollama") {
    return callOllama({ baseUrl: config.baseUrl, model: config.model, prompt });
  }
  if (config.provider === "anthropic") {
    return callAnthropic({ apiKey: config.apiKey, model: config.model, prompt });
  }
  return callOpenAi({ apiKey: config.apiKey, model: config.model, prompt });
}

export async function suggestPhraseTranslation(input) {
  const config = getAiConfig();
  if (!config) {
    const error = new Error(
      "No AI provider configured. Use Ollama (default) or set ANTHROPIC_API_KEY / OPENAI_API_KEY in .env"
    );
    error.code = "AI_NOT_CONFIGURED";
    throw error;
  }

  const [rulesMarkdown, policies] = await Promise.all([
    loadTranslationRules(),
    loadApprovedLemmaPolicies()
  ]);
  const { matched, missing } = policiesForTokens(input.tokenRows || [], policies);
  const prompt = buildPrompt({
    ...input,
    rulesMarkdown,
    matchedPolicies: matched,
    missingPolicies: missing
  });
  const raw = await callProvider(config, prompt);
  const normalized = normalizeSuggestionPayload(raw, {
    matchedPolicies: matched,
    missingPolicies: missing
  });

  if (!normalized.proposal) {
    throw new Error("AI returned no Spanish proposal.");
  }

  return {
    proposal: normalized.proposal,
    analysis: normalized.analysis,
    matchedPolicies: matched,
    missingPolicies: missing,
    provider: config.provider,
    model: config.model,
    suggestionSource: "ai-proposed"
  };
}
