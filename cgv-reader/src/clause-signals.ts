import type { ClauseBeginningToken } from "./clause-data";

export type FrameType = "time" | "reason" | "condition" | "purpose";

export interface ClauseSignalInput {
  finiteVerbId: string;
  chapter: number;
  verse: number;
  finiteVerbLemma?: string;
  beginningTokens: ClauseBeginningToken[];
}

export type ClauseSignal =
  | { kind: "confident"; choice: "describes"; reason: string }
  | { kind: "confident"; choice: "content"; target: string; reason: string }
  | { kind: "confident"; choice: "frame"; frameType: FrameType; target: string; reason: string }
  | { kind: "uncertain"; reason: string }
  | { kind: "none"; reason: string };

// Robinson's/MorphGNT-style tag for relative pronouns. Verified directly against
// Titus 1:2 token 5 ("ἣν" / "la cual" — the clause the Q1 correction in the spec
// was written for): morph "RR----ASF-", lemma "ὅς".
const RELATIVE_PRONOUN_PREFIX = "RR";

// Straight from the spec's particle table — Greek lemma to frame type, the same
// lookup already used to auto-derive frameType once Q3 is "yes."
export const FRAME_PARTICLES: Record<string, FrameType> = {
  "ἵνα": "purpose",
  "ὅπως": "purpose",
  "γάρ": "reason",
  "διότι": "reason",
  "εἰ": "condition",
  "ἐάν": "condition",
  "ὅτε": "time",
  "ὡς": "time",
  "ἐπεί": "time"
};

// ὅτι genuinely introduces both content clauses ("that") and reason clauses
// ("because") in Greek, and nothing about the word itself disambiguates — it
// depends on the governing verb, which is exactly what this question is
// supposed to help a student discover. The spec is explicit: do not silently
// resolve this in code. Surface it as a real judgment call instead.
export const AMBIGUOUS_PARTICLES: Record<string, string> = {
  "ὅτι":
    "can introduce either the content of what was said/thought (“that…”) or the reason for it (“because…”), and the word alone never settles which"
};

// Verbs of saying, thinking, wanting, teaching, or reminding — genuinely present
// in Titus (λέγω, λαλέω, διδάσκω, πιστεύω, βούλομαι, ὁμολογέω, παρακαλέω,
// ἐπαγγέλλομαι, ὑπομιμνῄσκω, οἶδα all occur in the book). Used to rank which
// nearby clause is the likelier parent for a content clause, not to declare a
// yes/no on its own — Greek content clauses are marked by ὅτι, which is
// deliberately ambiguous above, so this list only strengthens candidate
// selection once the student (or the ὅτι flag) has already decided "yes."
export const CONTENT_VERB_LEMMAS = new Set([
  "λέγω",
  "λαλέω",
  "διδάσκω",
  "πιστεύω",
  "βούλομαι",
  "θέλω",
  "ὁμολογέω",
  "παρακαλέω",
  "ἐπαγγέλλομαι",
  "ὑπομιμνῄσκω",
  "οἶδα",
  "ἀρνέομαι"
]);

function stripAccentless(lemma: string): string {
  return lemma.trim();
}

function clauseOrderKey(clause: ClauseSignalInput): number {
  return clause.chapter * 1000 + clause.verse;
}

function nearestPrecedingClauseId(
  clause: ClauseSignalInput,
  allClauses: ClauseSignalInput[]
): string | null {
  const ordered = [...allClauses].sort((a, b) => clauseOrderKey(a) - clauseOrderKey(b));
  const index = ordered.findIndex(c => c.finiteVerbId === clause.finiteVerbId);
  if (index <= 0) return null;
  return ordered[index - 1].finiteVerbId;
}

// The Greek clause-boundary heuristic sometimes leaves a stray word or two from
// the *previous* clause's own trailing material (e.g. an object pronoun) at the
// front of this one's token range — a preposition-phrase complement that never
// got its own boundary marker. Particles and relative pronouns are themselves
// always clause-initial in Greek, so scanning a short window rather than
// requiring position 0 tolerates that leak without reaching into a different,
// deeper clause.
const LEADING_WINDOW = 4;

function findLeadingToken(
  tokens: ClauseBeginningToken[],
  predicate: (token: ClauseBeginningToken) => boolean
): ClauseBeginningToken | undefined {
  return tokens.slice(0, LEADING_WINDOW).find(predicate);
}

/**
 * Detects a Greek-grounded proposal for what a clause is doing, mirroring the
 * spec's three questions. The evidence is always the Greek morphology/lemma of
 * the clause's opening token(s) — never the Spanish surface text — so a
 * "proposal" is objective rather than a guess dressed up as one. Display stays
 * Spanish; only the reasoning cites the Greek.
 */
export function detectClauseSignal(
  clause: ClauseSignalInput,
  allClauses: ClauseSignalInput[]
): ClauseSignal {
  const relative = findLeadingToken(clause.beginningTokens, token => token.morph.startsWith(RELATIVE_PRONOUN_PREFIX));
  if (relative) {
    return {
      kind: "confident",
      choice: "describes",
      reason:
        `Opens with “${relative.greek}” (${relative.lemma}) — that's a relative pronoun, and a clause that ` +
        `opens with one is what makes it a relative clause. It should be describing a noun nearby; select it in the text below.`
    };
  }

  const frameToken = findLeadingToken(clause.beginningTokens, token => Boolean(FRAME_PARTICLES[stripAccentless(token.lemma)]));
  if (frameToken) {
    const frameLemma = stripAccentless(frameToken.lemma);
    const frameType = FRAME_PARTICLES[frameLemma];
    const target = nearestPrecedingClauseId(clause, allClauses);
    if (target) {
      return {
        kind: "confident",
        choice: "frame",
        frameType,
        target,
        reason:
          `Opens with “${frameToken.greek}” (${frameLemma}) — that maps straight to a ${frameType} clause, ` +
          `the same particle table a Greek grammar would use (ἵνα/ὅπως → purpose, γάρ/διότι → reason, and so on).`
      };
    }
  }

  const ambiguousToken = findLeadingToken(clause.beginningTokens, token => Boolean(AMBIGUOUS_PARTICLES[stripAccentless(token.lemma)]));
  if (ambiguousToken) {
    const ambiguousLemma = stripAccentless(ambiguousToken.lemma);
    return {
      kind: "uncertain",
      reason:
        `Opens with “${ambiguousToken.greek}” (${ambiguousLemma}) — ${AMBIGUOUS_PARTICLES[ambiguousLemma]}. ` +
        `That's a genuine judgment call, not something to guess at; it turns on which verb governs it, ` +
        `which is exactly what this question is asking you to work out.`
    };
  }

  return {
    kind: "none",
    reason:
      "No relative pronoun, no connecting particle at the front — none of the usual opening markers are here. " +
      "That absence is itself informative: clauses like this are usually independent, standing on their own."
  };
}

/**
 * Ranks candidate parent clauses for a content relation: clauses whose own
 * finite verb is a said/thought/wanted verb are the likelier parent, based on
 * the Greek lemma — not a guess, but not a forced answer either.
 */
export function isLikelyContentParent(candidate: { finiteVerbLemma?: string }): boolean {
  return Boolean(candidate.finiteVerbLemma && CONTENT_VERB_LEMMAS.has(stripAccentless(candidate.finiteVerbLemma)));
}
