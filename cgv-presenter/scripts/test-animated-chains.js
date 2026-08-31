#!/usr/bin/env node
/**
 * Smoke-test animated →/↓ chains against a real manual.
 *
 * Usage:
 *   node scripts/test-animated-chains.js
 *   node scripts/test-animated-chains.js "/path/to/manual.md"
 */
const fs = require("fs");
const path = require("path");

const DEFAULT_MANUAL = "/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/20.1Juan/1juan.1.32.md";
const animatedChainMarker = "::roots-animated-chain::";

function stripMarkdownEmphasis(value) {
  return String(value || "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/_([^_]+)_/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

function parseAnimatedChain(markdown) {
  const raw = String(markdown || "").trim();
  if (!raw) return null;

  const body = raw.replace(/^(?:[-*]|>)\s*/, "").trim();
  const hasDown = body.includes("↓");
  const hasRight = body.includes("→");
  if (!hasDown && !hasRight) return null;
  if (/[:：]/.test(body) || /\[\^[^\]]+\]/.test(body)) return null;

  const parts = body
    .split(/([→↓])/)
    .map(part => part.trim())
    .filter(Boolean);

  const items = [];
  const connectors = [];
  let expectItem = true;

  for (const part of parts) {
    if (part === "→" || part === "↓") {
      if (expectItem || connectors.length >= items.length) return null;
      connectors.push(part);
      expectItem = true;
      continue;
    }

    if (!expectItem) return null;
    items.push(stripMarkdownEmphasis(part));
    expectItem = false;
  }

  if (expectItem) return null;
  if (items.length < 2 || connectors.length !== items.length - 1) return null;
  if (items.some(item => /[*_`]/.test(item))) return null;
  if (items.some(item => item.length > 80)) return null;

  const direction = hasDown && hasRight
    ? "mixed"
    : hasDown
      ? "vertical"
      : "horizontal";

  return { direction, items, connectors };
}

function buildAnimatedChainReveals(line) {
  const chain = parseAnimatedChain(line);
  return chain ? buildAnimatedChainRevealsFromChain(chain) : null;
}

function buildAnimatedChainRevealsFromChain(chain) {
  const id = `chain-${chain.items.join("-").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, "")}-${chain.direction}`;
  return chain.items.map((_, index) =>
    `${animatedChainMarker}${JSON.stringify({
      id,
      direction: chain.direction,
      items: chain.items.slice(0, index + 1),
      connectors: (chain.connectors || []).slice(0, index)
    })}`
  );
}

function parseMultilineAnimatedChain(lines, startIndex) {
  const first = parseAnimatedChain(lines[startIndex]);
  if (!first || first.direction !== "horizontal") return null;

  const items = [...first.items];
  const connectors = [...first.connectors];
  let index = startIndex + 1;
  let consumed = 1;
  let sawDown = false;
  let expectNextRow = false;

  while (index < lines.length) {
    const raw = String(lines[index] || "").trim();
    if (!raw) break;

    if (raw === "↓") {
      if (expectNextRow) return null;
      connectors.push("↓");
      sawDown = true;
      expectNextRow = true;
      index += 1;
      consumed += 1;
      continue;
    }

    if (expectNextRow) {
      const next = parseAnimatedChain(raw);
      if (next && next.direction === "horizontal") {
        items.push(...next.items);
        connectors.push(...next.connectors);
        expectNextRow = false;
        index += 1;
        consumed += 1;
        continue;
      }

      if (!/[→↓]/.test(raw) && !/^[-*#>]/.test(raw)) {
        items.push(stripMarkdownEmphasis(raw));
        expectNextRow = false;
        index += 1;
        consumed += 1;
        continue;
      }
    }

    break;
  }

  if (expectNextRow) return null;
  if (!sawDown || consumed < 3) return null;
  if (items.length < 3 || connectors.length !== items.length - 1) return null;
  if (items.some(item => !item || item.length > 80 || /[*_`]/.test(item))) return null;

  return {
    chain: {
      direction: "mixed",
      items,
      connectors
    },
    consumed
  };
}

function groupRevealLines(lines) {
  const revealLines = [];
  for (let index = 0; index < lines.length; index++) {
    const multiline = parseMultilineAnimatedChain(lines, index);
    if (multiline) {
      revealLines.push(...buildAnimatedChainRevealsFromChain(multiline.chain));
      index += multiline.consumed - 1;
      continue;
    }

    const line = lines[index];
    const animated = buildAnimatedChainReveals(line);
    if (animated) {
      revealLines.push(...animated);
      continue;
    }
    revealLines.push(line);
  }
  return revealLines;
}

function parseFrontMatter(markdown) {
  if (!markdown.startsWith("---\n")) return { body: markdown };
  const closing = markdown.indexOf("\n---", 4);
  if (closing === -1) return { body: markdown };
  return { body: markdown.slice(closing + 4).trim() };
}

const manualPath = path.resolve(process.argv[2] || DEFAULT_MANUAL);
if (!fs.existsSync(manualPath)) {
  console.error(`Manual not found: ${manualPath}`);
  process.exit(1);
}

const { body } = parseFrontMatter(fs.readFileSync(manualPath, "utf8"));
const slideBlocks = body
  .split(/\n\s*\n/)
  .map(block => block.split("\n").map(line => line.trim()).filter(Boolean))
  .filter(slide => slide.length > 0);

let chainSlides = 0;
let chainSteps = 0;
const samples = [];
const missed = [];

for (const block of slideBlocks) {
  for (let index = 0; index < block.length; index++) {
    const multiline = parseMultilineAnimatedChain(block, index);
    if (multiline) {
      index += multiline.consumed - 1;
      continue;
    }

    const line = block[index];
    if (/→|↓/.test(line) && !parseAnimatedChain(line) && !/[:：]|\[\^/.test(line)) {
      missed.push(line);
    }
  }

  const reveals = groupRevealLines(block);
  const chainReveals = reveals.filter(line => String(line).startsWith(animatedChainMarker));
  if (!chainReveals.length) continue;

  chainSlides += 1;
  chainSteps += chainReveals.length;
  if (samples.length < 10) {
    const payloads = chainReveals.map(line => JSON.parse(line.slice(animatedChainMarker.length)));
    samples.push({
      source: block.find(line => /→|↓/.test(line)),
      steps: payloads.map(payload => {
        const items = payload.items || [];
        const connectors = payload.connectors || [];
        return items.map((item, index) =>
          index === 0 ? item : `${connectors[index - 1] || "→"} ${item}`
        ).join(" ");
      })
    });
  }
}

console.log(`Manual: ${manualPath}`);
console.log(`Slides: ${slideBlocks.length}`);
console.log(`Slides with animated chains: ${chainSlides}`);
console.log(`Total chain reveal steps: ${chainSteps}`);
console.log("\nSamples:");
for (const sample of samples) {
  console.log(`  ${sample.source}`);
  console.log(`    → ${sample.steps.length} steps: ${sample.steps.join(" | ")}`);
}

if (missed.length) {
  console.log(`\nWARNING: ${missed.length} arrow lines not parsed as chains:`);
  for (const line of missed.slice(0, 10)) console.log(`  ${line}`);
}

if (chainSlides < 1) {
  console.error("\nFAIL: no animated chains found.");
  process.exit(1);
}

console.log("\nPASS");
