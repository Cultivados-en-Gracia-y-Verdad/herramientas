import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parsePlan } from '../public/plan-data.js';
import { makeServer } from './dev.mjs';

test('an original hosted export preserves sources, drafts, and schedule settings', () => {
  const plan = {
    sources: [{ name: 'Example', url: 'https://example.com/feed', type: 'RSS feed', topic: 'Research' }],
    checks: [0, 2],
    fields: { subject: 'This week', body: 'Opening\n\nA story.', whatsapp: 'A short digest.', cadence: 'Weekly', zone: 'America/Toronto', groupSize: '12' }
  };
  assert.deepEqual(parsePlan(JSON.stringify({ title: 'Hosted export', ...plan })), plan);
  assert.deepEqual(parsePlan(JSON.stringify({ schemaVersion: 1, ...plan })), plan);
});

test('invalid or unsafe imports are rejected before replacing a plan', () => {
  const empty = { sources: [], checks: [], fields: {} };
  assert.throws(() => parsePlan('{'), /valid/);
  assert.throws(() => parsePlan('{}'), /not a Newsletter/);
  assert.throws(() => parsePlan(JSON.stringify({ ...empty, schemaVersion: 2 })), /newer format/);
  assert.throws(() => parsePlan(JSON.stringify({ ...empty, sources: [{ name: 'Unsafe', url: 'javascript:alert(1)' }] })), /http/);
  assert.throws(() => parsePlan(JSON.stringify({ ...empty, fields: { body: 42 } })), /text/);
  assert.throws(() => parsePlan(JSON.stringify({ ...empty, checks: [8] })), /checklist/);
});

test('local server serves app assets and does not expose project files', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'newsletter-desk-server-'));
  const server = makeServer({
    dataFile: join(directory, 'collection.json'),
    fetchImpl: async () => new Response('<rss><channel><item><title>Collected story</title><link>https://example.com/story</link><guid>one</guid></item></channel></rss>', { status: 200 })
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  try {
    const origin = `http://127.0.0.1:${server.address().port}`;
    for (const route of ['/', '/styles.css', '/app.js', '/plan-data.js']) {
      const response = await fetch(origin + route);
      assert.equal(response.status, 200, route);
      assert.ok((await response.text()).length > 100, route);
    }
    assert.equal((await fetch(origin + '/package.json')).status, 404);
    assert.equal((await fetch(origin + '/.env')).status, 404);
    assert.equal((await fetch(origin, { method: 'POST' })).status, 405);
    const collection = await fetch(origin + '/api/collection');
    assert.equal(collection.status, 200);
    assert.deepEqual(await collection.json(), { schemaVersion: 1, articles: [], collectionRuns: [] });
    const collected = await fetch(origin + '/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sources: [{ name: 'Example', url: 'https://example.com/feed' }] })
    });
    assert.equal(collected.status, 200);
    const result = await collected.json();
    assert.equal(result.run.added, 1);
    assert.equal(result.articles[0].title, 'Collected story');
    assert.equal(result.articles[0].sourceName, 'Example');
    const head = await fetch(origin, { method: 'HEAD' });
    assert.equal(head.status, 200);
    assert.equal(await head.text(), '');
  } finally {
    await new Promise(resolve => { server.close(resolve); server.closeAllConnections(); });
  }
});
