import type { FrameType } from "./clause-signals";

export type ClauseRelation = "describes" | "content" | "frame" | "root";

export interface ClauseSpanInfo {
  finiteVerbId: string;
  reference: string;
  spanText: string;
  wordIds: string[];
  /** Sortable book-order position (e.g. chapter*100000 + verse*1000 + wordIndex). */
  order: number;
}

export interface ClauseObservationLike {
  describesNoun?: "yes" | "no" | "unsure";
  describedNounSpan?: string[];
  isWhatWasExpressed?: "yes" | "no" | "unsure";
  expressedParentClauseId?: string;
  tellsWhenOrIf?: "yes" | "no" | "unsure";
  whenIfParentClauseId?: string;
  frameType?: FrameType;
}

export interface ResolvedClause {
  finiteVerbId: string;
  relation: ClauseRelation | null;
  parentClauseId: string | null;
  /** true when Q1 was "yes" but the described noun doesn't fall inside any indexed clause. */
  parked: boolean;
  describedNounSpan?: string[];
  frameType?: FrameType;
}

export interface SkeletonNode {
  finiteVerbId: string;
  reference: string;
  spanText: string;
  /** null means this node is a placeholder — referenced as a parent but not yet classified itself. */
  relation: ClauseRelation | null;
  frameType?: FrameType;
  children: SkeletonNode[];
}

export interface ParkedClause {
  finiteVerbId: string;
  reference: string;
  spanText: string;
  describedNounSpan: string[];
}

export interface TelosCandidate {
  purposeClause: ClauseSpanInfo;
  lastOutlineClause: ClauseSpanInfo | null;
}

/**
 * Resolves one clause's relation per the spec's three questions, first-yes-wins.
 * Q1's noun lookup is the one place a clause's "parent" isn't a direct pick: if the
 * described noun doesn't fall inside any existing clause's word span, this clause is
 * parked rather than forced onto the nearest available row.
 */
export function resolveClause(
  clause: ClauseSpanInfo,
  observation: ClauseObservationLike | undefined,
  allClauses: ClauseSpanInfo[]
): ResolvedClause {
  if (!observation) {
    return { finiteVerbId: clause.finiteVerbId, relation: null, parentClauseId: null, parked: false };
  }

  if (observation.describesNoun === "yes") {
    const nounIds = observation.describedNounSpan ?? [];
    const owner = nounIds.length
      ? allClauses.find(
          candidate => candidate.finiteVerbId !== clause.finiteVerbId && nounIds.some(id => candidate.wordIds.includes(id))
        )
      : undefined;
    return {
      finiteVerbId: clause.finiteVerbId,
      relation: "describes",
      parentClauseId: owner ? owner.finiteVerbId : null,
      parked: !owner,
      describedNounSpan: nounIds
    };
  }

  if (observation.isWhatWasExpressed === "yes" && observation.expressedParentClauseId) {
    return {
      finiteVerbId: clause.finiteVerbId,
      relation: "content",
      parentClauseId: observation.expressedParentClauseId,
      parked: false
    };
  }

  if (observation.tellsWhenOrIf === "yes" && observation.whenIfParentClauseId) {
    return {
      finiteVerbId: clause.finiteVerbId,
      relation: "frame",
      parentClauseId: observation.whenIfParentClauseId,
      parked: false,
      frameType: observation.frameType
    };
  }

  if (observation.describesNoun === "no" && observation.isWhatWasExpressed === "no" && observation.tellsWhenOrIf === "no") {
    return { finiteVerbId: clause.finiteVerbId, relation: "root", parentClauseId: null, parked: false };
  }

  return { finiteVerbId: clause.finiteVerbId, relation: null, parentClauseId: null, parked: false };
}

function byOrder(a: ClauseSpanInfo, b: ClauseSpanInfo): number {
  return a.order - b.order;
}

/**
 * Skeleton = every resolved clause, nested under its parent at the right depth.
 * A clause that's a parent but hasn't been classified itself still gets a node
 * (as a placeholder) so its children always have a visible home — nothing a
 * student has already decided disappears while the rest is unfinished.
 */
export function deriveSkeleton(
  clauses: ClauseSpanInfo[],
  observations: Record<string, ClauseObservationLike>
): { roots: SkeletonNode[]; parked: ParkedClause[] } {
  const byId = new Map(clauses.map(clause => [clause.finiteVerbId, clause]));
  const resolvedById = new Map<string, ResolvedClause>();
  for (const clause of clauses) {
    const resolved = resolveClause(clause, observations[clause.finiteVerbId], clauses);
    if (resolved.relation) resolvedById.set(clause.finiteVerbId, resolved);
  }

  const childrenMap = new Map<string, string[]>();
  const topLevelIds = new Set<string>();

  for (const [id, resolved] of resolvedById) {
    if (resolved.relation === "root") {
      topLevelIds.add(id);
    } else if (resolved.parentClauseId) {
      const list = childrenMap.get(resolved.parentClauseId) ?? [];
      list.push(id);
      childrenMap.set(resolved.parentClauseId, list);
    }
    // Parked "describes" clauses (no owning clause found) are surfaced separately below.
  }

  for (const parentId of childrenMap.keys()) {
    if (!resolvedById.has(parentId) && byId.has(parentId)) topLevelIds.add(parentId);
  }

  function buildNode(id: string): SkeletonNode {
    const clause = byId.get(id);
    if (!clause) throw new Error(`Unknown clause id in skeleton: ${id}`);
    const resolved = resolvedById.get(id);
    const kids = (childrenMap.get(id) ?? [])
      .map(childId => byId.get(childId))
      .filter((c): c is ClauseSpanInfo => Boolean(c))
      .sort(byOrder)
      .map(c => buildNode(c.finiteVerbId));

    return {
      finiteVerbId: id,
      reference: clause.reference,
      spanText: clause.spanText,
      relation: resolved?.relation ?? null,
      frameType: resolved?.frameType,
      children: kids
    };
  }

  const roots = Array.from(topLevelIds)
    .map(id => byId.get(id))
    .filter((c): c is ClauseSpanInfo => Boolean(c))
    .sort(byOrder)
    .map(c => buildNode(c.finiteVerbId));

  const parked: ParkedClause[] = clauses
    .filter(clause => resolvedById.get(clause.finiteVerbId)?.parked)
    .map(clause => ({
      finiteVerbId: clause.finiteVerbId,
      reference: clause.reference,
      spanText: clause.spanText,
      describedNounSpan: resolvedById.get(clause.finiteVerbId)?.describedNounSpan ?? []
    }));

  return { roots, parked };
}

/** Outline = root clauses only, book order — what's left if you strip everything indented out of the skeleton. */
export function deriveOutline(
  clauses: ClauseSpanInfo[],
  observations: Record<string, ClauseObservationLike>
): ClauseSpanInfo[] {
  return clauses
    .filter(clause => resolveClause(clause, observations[clause.finiteVerbId], clauses).relation === "root")
    .sort(byOrder);
}

/**
 * Telos = the first purpose clause, in book order, shown next to the outline's
 * last root clause. The software never declares a match — just places the two
 * next to each other and leaves the judgment to the student.
 */
export function deriveTelos(
  clauses: ClauseSpanInfo[],
  observations: Record<string, ClauseObservationLike>
): TelosCandidate | null {
  const purposeClauses = clauses
    .filter(clause => {
      const resolved = resolveClause(clause, observations[clause.finiteVerbId], clauses);
      return resolved.relation === "frame" && resolved.frameType === "purpose";
    })
    .sort(byOrder);

  if (!purposeClauses.length) return null;

  const outline = deriveOutline(clauses, observations);
  return {
    purposeClause: purposeClauses[0],
    lastOutlineClause: outline.length ? outline[outline.length - 1] : null
  };
}
