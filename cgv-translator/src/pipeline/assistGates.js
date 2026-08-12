import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { runChatCompletion, describeAiAvailability } from "../ai/suggestPhrase.js";

async function loadTranslationRules(rootDir) {
  const rulesPath = join(rootDir, "src", "ai", "lbf-translation-rules.md");
  return readFile(rulesPath, "utf8").catch(() => "");
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
    .replace(/\s+/gu, " ")
    .trim();
}

function scrubSummary(value) {
  return String(value || "")
    .replace(/esperanza de vida eterna|mandato de Dios|nuestro Salvador/gi, "[removed later-verse import]")
    .trim();
}

function buildTranslatePrompt({ analysis, rulesMarkdown, rv1909Text }) {
  const { gates, readyForSynthesis, reference, greek, mechanicalDraft } = analysis;
  const morphLines = (gates.morphology?.constraints || []).map(c =>
    `- ${c.greek} | ${c.morphology} | ${c.explanation} | ${ (c.requirements || []).join("; ") }`
  ).join("\n");
  const lemmaLines = (gates.lemma?.tokens || [])
    .filter(t => t.significant)
    .map(t =>
      `- ${t.greek} (${t.lemma}${t.strongs ? ` ${t.strongs}` : ""}): ${
        t.allowedRenderings?.length
          ? `specific approved rendering ${t.allowedRenderings.join("/")} (${t.policyScope || "scoped"})`
          : t.guidanceRendering
            ? `book-default lexical guidance: ${t.guidanceRendering}; inflect/realize according to morphology and syntax`
            : t.status === "blocked"
              ? "BLOCKED — no applicable approved decision"
              : "no applicable approved decision yet"
      }`
    )
    .join("\n");

  const verseWindow = gates.generalContext?.verseWindow || [];
  const discourseLines = [
    ...(gates.generalContext?.notes || []).map(n => `- ${n}`),
    ...verseWindow.map(v =>
      `- [${v.role}] ${v.reference}: ${v.greek}${v.rv1909 ? ` ‖ RV1909: ${v.rv1909}` : ""}`
    )
  ].join("\n");

  return `${rulesMarkdown}

---

TASK
Produce one modern Spanish rendering for this Greek phrase.
It must be faithful to Greek grammar and natural enough that a translator can usually click "Use draft".

Reference: ${reference}
Greek: ${greek}

HARD GRAMMAR CONSTRAINTS (do not violate):
${morphLines || "(none)"}

LEMMA POLICY:
${lemmaLines || "(none)"}

SYNTAX NOTES (immediate phrase):
${(gates.immediateContext?.structure?.notes || []).map(n => `- ${n}`).join("\n") || "(none)"}

GENERAL CONTEXT (verse → paragraph → book — clarify among morph-valid options only):
${discourseLines || "(none)"}
Scope: ${(gates.generalContext?.scope || []).join(" · ") || "—"}

Grammar skeleton (structure hint, not final style):
Template: ${mechanicalDraft?.template || "—"}
Mechanical: ${mechanicalDraft?.proposedSpanish || "—"}

RV1909 for THIS phrase (consultative style only — do not copy archaic wording; do not start from it):
${rv1909Text || "—"}
RV1909 flags: ${(gates.rv1909Review?.flags || []).map(f => f.note).join(" | ") || "none"}

Rules:
1. Translate FROM the Greek. RV1909 is consultative only.
2. Preserve number/case/dependency (e.g. πίστιν ἐκλεκτῶν = fe de los elegidos/escogidos, NEVER fe elegida).
3. πιστεύω in PASSIVE (ἐπιστεύθην) = "was entrusted / me fue confiada", NEVER "creí/believed".
4. Possessive genitives: αὐτοῦ/ἡμῶν → su/nuestro before the noun (su palabra, nuestro Salvador), not "de él/de nosotros".
5. τοῦ σωτῆρος ἡμῶν θεοῦ ≈ "de Dios nuestro Salvador" or "de nuestro Salvador Dios", not "Salvador de nosotros, Dios".
6. ἰδίοις with καιροῖς = "tiempos propios / sus tiempos", NEVER "tiempos escogidos".
7. Prefer readings that fit the verse/paragraph discourse above when multiple morph-valid options exist.
8. Use contemporary Spanish that flows naturally (never RV1909 spelling like "á").
9. Do not add subjects/copulas/theology absent from this phrase.
10. Articles and smooth phrasing are allowed when Spanish requires them and Greek sense remains.
11. Soft δέ: do not force "y"; "pero tú…" is fine when addressing resumes the discourse.
12. ἰδίοις ἀνδράσιν (household) → "sus propios maridos", not "varones".
13. Translate ONLY this phrase span — do not pull wording from the next Greek phrase or later RV1909 clauses.
14. If readyForSynthesis=${readyForSynthesis} is false, set proposedSpanish to null.
15. Return JSON only:

{
  "gateSummaries": {
    "lemma": "one sentence",
    "morphology": "one sentence",
    "immediateContext": "one sentence",
    "generalContext": "one sentence citing verse/paragraph",
    "rv1909Review": "one sentence"
  },
  "proposedSpanish": "modern faithful Spanish phrase",
  "rationale": ["short bullets citing Greek + discourse constraints"],
  "flags": [],
  "blockedNote": null
}`;
}

function validateDraftAgainstGates(draft, analysis) {
  const flags = [];
  const text = String(draft || "");
  const morphConstraints = analysis?.gates?.morphology?.constraints || [];

  for (const item of morphConstraints) {
    if (/ἐκλεκτ/u.test(item.lemma || "") || /ἐκλεκτ/u.test(item.greek || "")) {
      if (/\bfe elegida\b/i.test(text) || /\bfe escogida\b/i.test(text)) {
        flags.push("Rejected: ἐκλεκτῶν cannot become attributive 'fe elegida/escogida'.");
      }
      if (item.number === "plural" && (/\bel elegido\b/i.test(text) || /\bel escogido\b/i.test(text))) {
        flags.push("Rejected: ἐκλεκτῶν is plural — not 'el elegido/escogido'.");
      }
      if (item.number === "plural" && !/\b(elegidos|escogidos)\b/i.test(text)) {
        flags.push("Rejected: plural ἐκλεκτῶν must appear as elegidos/escogidos.");
      }
    }
  }

  if (/\bél es\b/i.test(text) || /\bella es\b/i.test(text)) {
    flags.push("Rejected: added subject/copula not in the Greek phrase.");
  }

  if (/salvación|camino para ser salvado|jesucristo es el elegido/i.test(text)) {
    flags.push("Rejected: theological addition beyond this phrase.");
  }

  // πιστεύω passive must not become "creer"
  const hasPistueoPassive = (analysis?.gates?.morphology?.constraints || []).some(item =>
    /πιστεύω/.test(item.lemma || "") && /passive/i.test(item.explanation || "")
  );
  if (hasPistueoPassive && /\b(creí|creyó|creído|creida|creiste)\b/i.test(text)) {
    flags.push("Rejected: πιστεύω passive means 'was entrusted', not 'believed'.");
  }

  if (/\bde nosotros\b/i.test(text) && /\b(salvador|señor|dios)\b/i.test(text)) {
    flags.push("Rejected: ἡμῶν should be possessive 'nuestro', not 'de nosotros'.");
  }

  if (/\btiempos escogidos\b/i.test(text)) {
    flags.push("Rejected: ἰδίοις means 'own/proper', not 'escogidos'.");
  }

  // RV1909 orthography bleed (preposition/article "á")
  if (/(?:^|\s)á(?:\s|$)/u.test(text) || /\sá[aeiouáéíóú]/iu.test(text)) {
    flags.push("Rejected: archaic RV1909 orthography (á); use contemporary Spanish (a, de, etc.).");
  }

  if (/\bvarones\b/i.test(text) && /ἀνήρ|ἀνδρ/u.test(JSON.stringify(analysis?.gates?.morphology?.constraints || []))) {
    // Household context: ἰδίοις ἀνδράσιν → maridos, not generic 'varones'
    const hasIdiois = (analysis?.gates?.morphology?.constraints || []).some(item =>
      /ἴδιος|ἰδίοις|ἰδίους/u.test(item.greek || "") || /ἴδιος/.test(item.lemma || "")
    );
    if (hasIdiois) {
      flags.push("Rejected: ἰδίοις ἀνδράσιν in household context → 'sus propios maridos', not 'varones'.");
    }
  }

  // Servant fidelity: πίστις + ἐνδείκνυμι / δοῦλος discourse → not bare "fe"
  const constraints = analysis?.gates?.morphology?.constraints || [];
  const hasPistis = constraints.some(item => (item.lemma || "") === "πίστις");
  const hasEndeiknumi = constraints.some(item => /ἐνδείκνυμ/.test(item.lemma || ""));
  if (hasPistis && hasEndeiknumi && /\bfe\b/i.test(text) && !/\b(fidelidad|lealtad)\b/i.test(text)) {
    flags.push("Rejected: πίστιν … ἐνδεικνυμένους in servant context → fidelidad/lealtad, not 'fe'.");
  }

  const greek = String(analysis?.greek || "");
  if (/^Ταῦτα\b/u.test(greek) && /\bEste\b/.test(text)) {
    flags.push("Rejected: Ταῦτα is neuter plural → 'Estas cosas'/'Esto', not 'Este'.");
  }
  if (/παρακάλει/u.test(greek) && /\bruega\b/i.test(text)) {
    flags.push("Rejected: παρακάλει (pastoral) → 'exhorta', not 'ruega'.");
  }
  if (/Πιστὸς\s+ὁ\s+λόγος/u.test(greek) && !/\b(fiel|fiable)\b/i.test(text)) {
    flags.push("Rejected: Πιστὸς ὁ λόγος → 'Fiel es la palabra' / 'Palabra fiel'.");
  }
  if (/Πιστὸς\s+ὁ\s+λόγος/u.test(greek) && /\bfiest/i.test(text)) {
    flags.push("Rejected: hallucinated 'fiesta' for Πιστὸς ὁ λόγος.");
  }
  if (/φιλανθρωπία/u.test(greek) && /\bhumanidad\b/i.test(text) && !/\bamor\b/i.test(text)) {
    flags.push("Rejected: φιλανθρωπία → 'amor a los hombres', not bare 'humanidad'.");
  }
  if (/Ἰησοῦ\s+Χριστοῦ/u.test(greek) && /\bJesús\b/i.test(text) && !/\bCristo\b/i.test(text)) {
    flags.push("Rejected: Greek has Ἰησοῦ Χριστοῦ — keep Jesucristo / Jesús Cristo.");
  }
  // Spillover: if this phrase is a short imperative clause, reject long multi-clause dumps
  const tokenCount = (analysis?.gates?.morphology?.constraints || []).length;
  if (tokenCount > 0 && tokenCount <= 6 && (text.match(/,/g) || []).length >= 3 && /\b(Nicópolis|Artemas|Tíquico)\b/i.test(text)) {
    const hasOnlyTravelSetup = /Ὅταν\s+πέμψω/u.test(greek);
    const hasComeImperative = /σπούδασον\s+ἐλθεῖν/u.test(greek);
    if (hasOnlyTravelSetup && /\bvenir\b/i.test(text) && /\bNicópolis\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — travel setup must not include 'venir a Nicópolis' from the next span.");
    }
    if (hasComeImperative && /\bArtemas\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — 'venir' span must not include Artemas/Tíquico from the previous span.");
    }
  }
  if (/μανθανέτωσαν/.test(greek) && /προΐστασθαι/.test(greek) && !/ἄκαρποι/u.test(greek)) {
    if (/\b(sin fruto|inútiles)\b/i.test(text)) {
      flags.push("Rejected: phrase spillover — do not pull ἵνα μὴ ὦσιν ἄκαρποι into the μανθανέτωσαν span.");
    }
  }
  if (/Ἀσπάζοντα[ίι]\s+σε/u.test(greek) && !/\bte\b/i.test(text)) {
    flags.push("Rejected: Ἀσπάζονταί σε requires object 'te'.");
  }
  if (/ἡ\s+χάρις\s+μετὰ\s+πάντων\s+ὑμῶν/u.test(greek) && !/\btodos\b/i.test(text)) {
    flags.push("Rejected: ἡ χάρις μετὰ πάντων ὑμῶν must keep 'todos'.");
  }
  if (/καλῶν\s+ἔργων\s+προΐστασθαι/u.test(greek)
    && !/\b(dedic|ocup|gobern)/i.test(text)
    && /\baprend/i.test(text)) {
    flags.push("Rejected: καλῶν ἔργων προΐστασθαι → dedicarse/ocuparse en buenas obras, not only 'aprender de'.");
  }

  return { ok: flags.length === 0, flags };
}

export async function assistPhraseGates({
  rootDir,
  analysis,
  rv1909Text = ""
}) {
  const availability = await describeAiAvailability();
  if (!availability.available) {
    const error = new Error(availability.message || "AI assist unavailable");
    error.code = "AI_NOT_CONFIGURED";
    throw error;
  }

  const mechanical = analysis.mechanicalDraft;
  const rulesMarkdown = await loadTranslationRules(rootDir);
  const prompt = buildTranslatePrompt({
    analysis,
    rulesMarkdown,
    rv1909Text: rv1909Text || analysis.gates?.rv1909Review?.rv1909Text || ""
  });

  const raw = await runChatCompletion({
    prompt,
    json: true,
    system: `You are a Bible translation assistant for La Biblia Fiel.
Produce faithful contemporary Spanish from Greek grammar constraints.
Prefer natural modern Spanish that a human can usually accept with light edits.
Never invent theology. Never violate number/case/dependency.
Return JSON only.`
  });

  const parsed = extractJsonObject(raw) || {};
  const gateSummaries = parsed.gateSummaries && typeof parsed.gateSummaries === "object"
    ? parsed.gateSummaries
    : {};
  const flags = Array.isArray(parsed.flags)
    ? parsed.flags.map(item => String(item).trim()).filter(Boolean)
    : [];

  let proposedSpanish = analysis.readyForSynthesis
    ? cleanProposal(parsed.proposedSpanish || "")
    : null;
  let draftSource = "ai";

  if (analysis.readyForSynthesis) {
    const validation = validateDraftAgainstGates(proposedSpanish, analysis);
    if (!proposedSpanish || !validation.ok) {
      flags.push(...validation.flags);
      if (mechanical?.proposedSpanish) {
        proposedSpanish = mechanical.proposedSpanish;
        draftSource = "mechanical-fallback";
        flags.push("AI draft rejected by grammar checks; showing mechanical fallback.");
      } else if (!proposedSpanish) {
        throw new Error("AI returned no Spanish draft.");
      }
    }
  }

  return {
    provider: availability.provider,
    model: availability.model,
    draftSource,
    gateSummaries: {
      lemma: scrubSummary(gateSummaries.lemma),
      morphology: scrubSummary(gateSummaries.morphology),
      immediateContext: scrubSummary(gateSummaries.immediateContext),
      generalContext: scrubSummary(gateSummaries.generalContext),
      rv1909Review: scrubSummary(gateSummaries.rv1909Review)
    },
    proposedSpanish,
    slots: mechanical?.slots || [],
    template: mechanical?.template || null,
    rationale: Array.isArray(parsed.rationale)
      ? parsed.rationale.map(item => String(item).trim()).filter(Boolean)
      : [],
    blockedNote: parsed.blockedNote ? String(parsed.blockedNote).trim() : (
      analysis.pipelineStatus === "blocked"
        ? `Gate 1 blocked on ${analysis.constraints.blockedLemma || "lemma policy"}. Open an investigation before drafting.`
        : null
    ),
    flags,
    readyForSynthesis: analysis.readyForSynthesis,
    pipelineStatus: analysis.pipelineStatus
  };
}
