import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { collectFeeds, createStore } from './collection.mjs';

const root = fileURLToPath(new URL('../public/', import.meta.url));
const assets = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/plan-data.js', ['plan-data.js', 'text/javascript; charset=utf-8']]
]);

const defaultDataFile = fileURLToPath(new URL('../data/newsletter-desk.json', import.meta.url));

function sendJson(res, status, value) {
  const body = Buffer.from(JSON.stringify(value));
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': body.byteLength });
  res.end(body);
}

async function readJson(req) {
  const chunks = [];
  let length = 0;
  for await (const chunk of req) {
    length += chunk.length;
    if (length > 1024 * 1024) throw new Error('Request is larger than 1 MB.');
    chunks.push(chunk);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
  catch { throw new Error('Request body must be valid JSON.'); }
}

function collectionSources(value) {
  if (!value || !Array.isArray(value.sources) || !value.sources.length || value.sources.length > 100) {
    throw new Error('Choose between 1 and 100 RSS or Atom feeds.');
  }
  return value.sources.map(source => {
    if (!source || typeof source.name !== 'string' || !source.name.trim() || typeof source.url !== 'string') {
      throw new Error('Every feed needs a name and URL.');
    }
    const type = source.type === 'Calendar feed' ? 'Calendar feed' : source.type === 'RSS feed' ? 'RSS feed' : null;
    if (!type) throw new Error('Sources must be RSS or calendar feeds.');
    const url = new URL(source.url);
    const protocols = type === 'Calendar feed' ? ['http:', 'https:', 'webcal:'] : ['http:', 'https:'];
    if (!protocols.includes(url.protocol)) throw new Error(type === 'Calendar feed' ? 'Calendar URLs must use webcal, http, or https.' : 'Feed URLs must use http or https.');
    return { name: source.name.trim().slice(0, 150), url: url.href, type };
  });
}

export function makeServer({ dataFile = defaultDataFile, fetchImpl = fetch } = {}) {
  const store = createStore(dataFile);
  return createServer(async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Cache-Control', 'no-store');
    let pathname;
    try { pathname = new URL(req.url, 'http://localhost').pathname; }
    catch { res.writeHead(400); res.end('Bad request'); return; }
    if (pathname === '/api/collection' && req.method === 'GET') {
      try { sendJson(res, 200, await store.read()); }
      catch (error) { sendJson(res, 500, { error: error.message }); }
      return;
    }
    if (pathname === '/api/collect' && req.method === 'POST') {
      let sources;
      try {
        sources = collectionSources(await readJson(req));
      } catch (error) {
        sendJson(res, 400, { error: error.message });
        return;
      }
      try {
        sendJson(res, 200, await collectFeeds(sources, { store, fetchImpl }));
      } catch (error) {
        sendJson(res, 500, { error: error.message });
      }
      return;
    }
    if (!['GET', 'HEAD'].includes(req.method)) {
      res.writeHead(405, { Allow: 'GET, HEAD' });
      res.end('Method not allowed');
      return;
    }
    const asset = assets.get(pathname);
    if (!asset) { res.writeHead(404); res.end('Not found'); return; }
    try {
      const body = await readFile(resolve(root, asset[0]));
      res.writeHead(200, { 'Content-Type': asset[1], 'Content-Length': body.byteLength });
      res.end(req.method === 'HEAD' ? undefined : body);
    } catch (error) {
      console.error('Unable to read app asset:', error.message);
      res.writeHead(500);
      res.end('Unable to load app asset');
    }
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT ?? 4173);
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    console.error('PORT must be an integer between 0 and 65535.');
    process.exit(1);
  }
  const server = makeServer();
  server.on('error', error => {
    console.error(error.code === 'EADDRINUSE'
      ? `Port ${port} is already in use. Stop the other process or set PORT to another number.`
      : error.message);
    process.exitCode = 1;
  });
  server.listen(port, '127.0.0.1', () => {
    console.log(`Newsletter Desk: http://127.0.0.1:${server.address().port}`);
    console.log('Local only. Press Ctrl+C to stop. Refresh the browser after editing files.');
  });
}
