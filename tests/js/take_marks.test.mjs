import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TakesClient, marksText } from '../../web/h3c_takes.mjs?v=20261104-take-marks-1';

test('marks read as stars and tag', () => {
  assert.equal(marksText(4, 'keeper'), '★★★★☆ · keeper');
  assert.equal(marksText(0, 'wide'), 'tag: wide');
  assert.equal(marksText(0, ''), '');
});

test('a rating posts to the rate route', async () => {
  const sent = [];
  const client = new TakesClient(async (url, body) => { sent.push([url, body]); return {ok: true}; });
  assert.deepEqual(await client.send('rate', {created: 'c', rating: 3, tag: ''}), {ok: true});
  assert.deepEqual(sent, [['/h3c/timeline/takes/rate', {created: 'c', rating: 3, tag: ''}]]);
});
