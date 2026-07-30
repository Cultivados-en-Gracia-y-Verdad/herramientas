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

const DEFAULT_MANUAL = "/Users/johnwry/Nextcloud/Documents/GitHub/curriculo/20.1Juan/1-juan-manual-skeleton (6).md";
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

  const body = raw.replace(/^[-*]\s+/, "").trim();
  const hasDown = body.includes("↓");
  const hasRight = body.includes("→");
  const direction = hasDown ? "vertical" : hasRight ? "horizontal" : null;
  if (!direction) return null;
  if (hasDown && hasRight) return null;
  if (/[:：]/.test(body) || /\[\^[^\]]+\]/.test(body)) return null;

  const arrow = direction === "vertical" ? "↓" : "→";
  const parts = body
    .split(arrow)
    .map(part => part.trim())
    .filter(Boolean);

  if (parts.length < 2) return null;

  const items = parts.map(stripMarkdownEmphasis).filter(Boolean);
  if (items.length < 2 || items.length !== parts.length) return null;
  if (items.some(item => /[*_`]/.test(item))) return null;
  if (items.some(item => item.length > 80)) return null;

  return { direction, items };
}

function buildAnimatedChainReveals(line) {
  const chain = parseAnimatedChain(line);
  if (!chain) return null;
  const id = `chain-${chain.items.join("-").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, "")}-${chain.direction}`;
  return chain.items.map((_, index) =>
    `${animatedChainMarker}${JSON.stringify({
      id,
      direction: chain.direction,
      items: chain.items.slice(0, index + 1)
    })}`
  );
}

function groupRevealLines(lines) {
  const revealLines = [];
  for (const line of lines) {
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
  for (const line of block) {
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
      steps: payloads.map(payload => payload.items.join(payload.direction === "vertical" ? " ↓ " : " → "))
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
