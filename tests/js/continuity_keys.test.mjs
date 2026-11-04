import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseState, serialize } from '../../web/h3c_timeline_model.mjs?v=20261104-continuity-keys-1';

const boxes = [{id: 'a', frames: 124, prompt: 'p'}];

test('the Studio keeps context_noise and continuation_guide through an edit', () => {
  const saved = JSON.parse(serialize(parseState(JSON.stringify({version: 1, boxes, context_noise: true, continuation_guide: false}))));
  assert.equal(saved.context_noise, true);
  assert.equal(saved.continuation_guide, false);
});

test('defaults are not written', () => {
  const saved = JSON.parse(serialize(parseState(JSON.stringify({version: 1, boxes, context_noise: false, continuation_guide: true}))));
  assert.equal('context_noise' in saved, false);
  assert.equal('continuation_guide' in saved, false);
});
