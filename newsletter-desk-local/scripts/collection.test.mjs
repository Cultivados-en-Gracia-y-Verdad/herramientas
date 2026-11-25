import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { collectFeeds, createStore, parseCalendar, parseFeed } from './collection.mjs';

const source = { name: 'Example feed', url: 'https://example.com/feed.xml' };
const rss = `<?xml version="1.0"?><rss version="2.0"><channel><title>Example</title>
  <item><title>First &amp; useful</title><link>https://example.com/first</link><guid>story-1</guid><pubDate>Sun, 22 Nov 2026 12:00:00 GMT</pubDate><description><![CDATA[<p>A short <b>summary</b>.</p>]]></description></item>
  <item><title>Second</title><link>https://example.com/second</link><guid>story-2</guid></item>
</channel></rss>`;
const ical = `BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:event-one@example.com\r
DTSTART:20261128T190000Z\r
SUMMARY:Community concert\r
DESCRIPTION:An evening of local music.\r
LOCATION:Town Hall\r
URL:https://example.com/concert\r
END:VEVENT\r
END:VCALENDAR\r
`;

test('RSS and Atom entries retain attribution while removing markup', () => {
  const items = parseFeed(rss, source);
  assert.equal(items.length, 2);
  assert.equal(items[0].title, 'First & useful');
  assert.equal(items[0].summary, 'A short summary .');
  assert.equal(items[0].sourceName, source.name);
  assert.equal(items[0].publishedAt, '2026-11-22T12:00:00.000Z');
  assert.equal(items[0].reviewState, 'unreviewed');

  const atom = `<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom story</title><id>tag:example,1</id><link rel="alternate" href="/atom-story"/><updated>2026-11-23T10:30:00Z</updated><summary>News &amp; context</summary></entry></feed>`;
  const [entry] = parseFeed(atom, source);
  assert.equal(entry.link, 'https://example.com/atom-story');
  assert.equal(entry.summary, 'News & context');
});

test('collection persists articles, records errors, and does not add duplicates', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'newsletter-desk-'));
  const file = join(directory, 'collection.json');
  const store = createStore(file);
  const fetchImpl = async url => url === source.url
    ? new Response(rss, { status: 200, headers: { 'content-type': 'application/rss+xml' } })
    : new Response('no', { status: 503 });
  let tick = 0;
  const now = () => new Date(Date.parse('2026-11-23T10:00:00Z') + tick++ * 1000);
  const sources = [source, { name: 'Broken feed', url: 'https://bad.example/feed' }];

  const first = await collectFeeds(sources, { store, fetchImpl, now });
  assert.equal(first.run.added, 2);
  assert.equal(first.run.results[0].status, 'succeeded');
  assert.equal(first.run.results[1].status, 'failed');
  assert.match(first.run.results[1].error, /503/);

  const second = await collectFeeds([source], { store, fetchImpl, now });
  assert.equal(second.run.added, 0);
  assert.equal(second.articles.length, 2);
  const onDisk = JSON.parse(await readFile(file, 'utf8'));
  assert.equal(onDisk.collectionRuns.length, 2);
  assert.equal(onDisk.articles.length, 2);
});

test('non-feed content is rejected explicitly', () => {
  assert.throws(() => parseFeed('<html><title>Website</title></html>', source), /not an RSS or Atom feed/);
});

test('iCalendar events are collected from webcal URLs and deduplicated', async () => {
  const calendar = { name: 'Events', url: 'webcal://example.com/calendar.ics', type: 'Calendar feed' };
  const [event] = parseCalendar(ical, calendar);
  assert.equal(event.title, 'Community concert');
  assert.equal(event.link, 'https://example.com/concert');
  assert.equal(event.summary, 'An evening of local music.\nLocation: Town Hall');
  assert.equal(event.publishedAt, '2026-11-28T19:00:00.000Z');
  assert.equal(event.itemType, 'event');

  const directory = await mkdtemp(join(tmpdir(), 'newsletter-calendar-'));
  const store = createStore(join(directory, 'collection.json'));
  const requested = [];
  const fetchImpl = async url => {
    requested.push(url);
    return new Response(ical, { status: 200, headers: { 'content-type': 'text/calendar' } });
  };
  const first = await collectFeeds([calendar], { store, fetchImpl });
  const second = await collectFeeds([calendar], { store, fetchImpl });
  assert.deepEqual(requested, ['https://example.com/calendar.ics', 'https://example.com/calendar.ics']);
  assert.equal(first.run.added, 1);
  assert.equal(second.run.added, 0);
  assert.equal(second.articles.length, 1);
});
