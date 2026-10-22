export interface OrderedRelationship { eventA: number; eventB: number; type: 'before' | 'after' | string }

/** Returns event IDs participating in a contradictory before/after cycle. Other relationship types do not impose order. */
export function findChronologyCycle(relationships: OrderedRelationship[]): number[] | null {
  const graph = new Map<number, number[]>();
  for (const rel of relationships) {
    if (rel.type !== 'before' && rel.type !== 'after') continue;
    const from = rel.type === 'before' ? rel.eventA : rel.eventB;
    const to = rel.type === 'before' ? rel.eventB : rel.eventA;
    graph.set(from, [...(graph.get(from) || []), to]);
    if (!graph.has(to)) graph.set(to, []);
  }
  const visiting = new Set<number>(), visited = new Set<number>(), path: number[] = [];
  function visit(node: number): number[] | null {
    if (visiting.has(node)) return [...path.slice(path.indexOf(node)), node];
    if (visited.has(node)) return null;
    visiting.add(node); path.push(node);
    for (const next of graph.get(node) || []) { const cycle = visit(next); if (cycle) return cycle; }
    path.pop(); visiting.delete(node); visited.add(node); return null;
  }
  for (const node of graph.keys()) { const cycle = visit(node); if (cycle) return cycle; }
  return null;
}
