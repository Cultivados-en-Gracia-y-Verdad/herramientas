import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

const EMPTY_STORE = { schemaVersion: 1, articles: [], collectionRuns: [] };
const MAX_FEED_BYTES = 5 * 1024 * 1024;

function decodeXml(value = '') {
  const named = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
  return value.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1').replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (match, entity) => {
    if (entity[0] !== '#') return named[entity.toLowerCase()] ?? match;
    const code = entity[1].toLowerCase() === 'x' ? Number.parseInt(entity.slice(2), 16) : Number.parseInt(entity.slice(1), 10);
    return Number.isInteger(code) && code >= 0 && code <= 0x10ffff ? String.fromCodePoint(code) : match;
  });
}

function plainText(value = '') {
  return decodeXml(value).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function tag(block, names) {
  for (const name of names) {
    const match = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${name}>`, 'i'));
    if (match) return match[1].trim();
  }
  return '';
}

function entryLink(block) {
  const atomLinks = [...block.matchAll(/<link\b([^>]*)\/?>(?:[\s\S]*?<\/link>)?/gi)];
  for (const match of atomLinks) {
    const attributes = match[1];
    const href = attributes.match(/\bhref\s*=\s*["']([^"']+)["']/i)?.[1];
    const rel = attributes.match(/\brel\s*=\s*["']([^"']+)["']/i)?.[1];
    if (href && (!rel || rel.toLowerCase() === 'alternate')) return decodeXml(href.trim());
  }
  return plainText(tag(block, ['link']));
}

function safeHttpUrl(value, base) {
  if (!value) return '';
  try {
    const url = new URL(value, base);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}

function isoDate(value) {
  if (!value) return null;
  const date = new Date(plainText(value));
  return Number.isNaN(date.valueOf()) ? null : date.toISOString();
}

export function parseFeed(xml, source) {
  if (typeof xml !== 'string' || !/<(?:rss|feed|rdf:RDF)\b/i.test(xml)) throw new Error('Response is not an RSS or Atom feed.');
  const blocks = [...xml.matchAll(/<(item|entry)\b[^>]*>([\s\S]*?)<\/\1>/gi)].map(match => match[2]);
  if (!blocks.length) throw new Error('Feed contains no article entries.');
  return blocks.map(block => {
    const title = plainText(tag(block, ['title'])) || 'Untitled item';
    const link = safeHttpUrl(entryLink(block), source.url);
    const guid = plainText(tag(block, ['guid', 'id']));
    const publishedAt = isoDate(tag(block, ['pubDate', 'published', 'updated', 'dc:date']));
    const summary = plainText(tag(block, ['description', 'summary', 'content:encoded', 'content'])).slice(0, 2000);
    const identity = guid || link || `${title}\n${publishedAt ?? ''}`;
    const id = createHash('sha256').update(`${source.url}\n${identity}`).digest('hex');
    return {
      id,
      sourceName: source.name,
      sourceUrl: source.url,
      title,
      link,
      publishedAt,
      summary,
      reviewState: 'unreviewed'
    };
  });
}

export function createStore(file) {
  return {
    async read() {
      try {
        const value = JSON.parse(await readFile(file, 'utf8'));
        if (value?.schemaVersion !== 1 || !Array.isArray(value.articles) || !Array.isArray(value.collectionRuns)) {
          throw new Error('Unsupported local data format.');
        }
        return value;
      } catch (error) {
        if (error.code === 'ENOENT') return structuredClone(EMPTY_STORE);
        throw error;
      }
    },
    async write(value) {
      await mkdir(dirname(file), { recursive: true });
      const temporary = `${file}.${process.pid}.tmp`;
      await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
      await rename(temporary, file);
    }
  };
}

export async function collectFeeds(sources, { store, fetchImpl = fetch, now = () => new Date() }) {
  const data = await store.read();
  const known = new Set(data.articles.map(article => article.id));
  const startedAt = now().toISOString();
  const results = [];
  let added = 0;

  for (const source of sources) {
    const result = { sourceName: source.name, sourceUrl: source.url, status: 'failed', found: 0, added: 0, error: null };
    try {
      const response = await fetchImpl(source.url, {
        headers: { Accept: 'application/atom+xml, application/rss+xml, application/xml, text/xml;q=0.9' },
        redirect: 'follow',
        signal: AbortSignal.timeout(15_000)
      });
      if (!response.ok) throw new Error(`Feed returned HTTP ${response.status}.`);
      const declaredLength = Number(response.headers?.get?.('content-length'));
      if (declaredLength > MAX_FEED_BYTES) throw new Error('Feed is larger than 5 MB.');
      const xml = await response.text();
      if (Buffer.byteLength(xml) > MAX_FEED_BYTES) throw new Error('Feed is larger than 5 MB.');
      const articles = parseFeed(xml, source);
      result.found = articles.length;
      for (const article of articles) {
        if (known.has(article.id)) continue;
        known.add(article.id);
        data.articles.push({ ...article, collectedAt: now().toISOString() });
        result.added += 1;
        added += 1;
      }
      result.status = 'succeeded';
    } catch (error) {
      result.error = error.name === 'TimeoutError' ? 'Feed request timed out.' : error.message;
    }
    results.push(result);
  }

  const run = { id: createHash('sha256').update(`${startedAt}\n${Math.random()}`).digest('hex').slice(0, 16), startedAt, finishedAt: now().toISOString(), added, results };
  data.collectionRuns.unshift(run);
  data.collectionRuns = data.collectionRuns.slice(0, 50);
  data.articles.sort((a, b) => (b.publishedAt ?? b.collectedAt).localeCompare(a.publishedAt ?? a.collectedAt));
  await store.write(data);
  return { run, articles: data.articles };
}
