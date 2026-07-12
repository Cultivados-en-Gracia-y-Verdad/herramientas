import { createServer } from "vite";
import { readFileSync } from "fs";

const bundle = JSON.parse(readFileSync(process.argv[2], "utf8"));
const data = bundle.data ?? bundle;

const spans = data["the-reader:spanish-clause-builder:titus:v3"];
const observations = data["the-reader:spanish-clause-builder:titus:statement-command-review:v1"];

const server = await createServer({ server: { middlewareMode: true }, root: process.cwd() });
const clauseTree = await server.ssrLoadModule("/src/clause-tree.ts");

function orderOf(id) {
  const [c, v, i] = id.split(":").map(Number);
  return c * 100000 + v * 1000 + i;
}

const clauses = Object.entries(spans).map(([finiteVerbId, span]) => ({
  finiteVerbId,
  reference: finiteVerbId,
  spanText: "",
  wordIds: span.selectedSpan,
  order: orderOf(finiteVerbId)
})).sort((a, b) => a.order - b.order);

const skeleton = clauseTree.deriveSkeleton(clauses, observations);
const outline = clauseTree.deriveOutline(clauses, observations);

console.log(`Total classified clauses (with spans): ${clauses.length}`);
console.log(`Total observations recorded: ${Object.keys(observations).length}`);

const unclassified = clauses.filter(c => !observations[c.finiteVerbId]);
console.log(`\nClauses with a span but NO observation recorded (${unclassified.length}):`);
for (const c of unclassified) console.log(`  ${c.finiteVerbId}`);

function printNode(node, depth) {
  const indent = "  ".repeat(depth);
  const rel = node.relation ?? "UNCLASSIFIED-PLACEHOLDER";
  const frame = node.frameType ? ` [${node.frameType}]` : "";
  console.log(`${indent}${node.finiteVerbId} — ${rel}${frame}`);
  for (const child of node.children) printNode(child, depth + 1);
}

console.log(`\n=== SKELETON: ${skeleton.roots.length} root (independent) clause(s) ===`);
for (const root of skeleton.roots) printNode(root, 0);

console.log(`\n=== PARKED clauses (describesNoun=yes but owner not found): ${skeleton.parked.length} ===`);
for (const p of skeleton.parked) {
  console.log(`  ${p.finiteVerbId} — describedNounSpan: ${JSON.stringify(p.describedNounSpan)}`);
}

// cross-check: any observation referencing a parent id that isn't itself a classified clause
console.log(`\n=== Dangling parent references (parent id not in spans) ===`);
for (const [id, obs] of Object.entries(observations)) {
  const parentId = obs.expressedParentClauseId || obs.whenIfParentClauseId;
  if (parentId && !spans[parentId]) {
    console.log(`  ${id} points to parent ${parentId}, which has no span/clause entry`);
  }
}

await server.close();
