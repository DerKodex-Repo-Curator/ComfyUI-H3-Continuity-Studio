import test from 'node:test';
import assert from 'node:assert/strict';
import {exportedVideo, partialBadge, partialTitle} from '../../web/h3c_partial_video.mjs';

const view = (filename) => ({filename, subfolder: 'h3_sequences/seq', type: 'output', v: 'x'});
const partial = {file: view('seq_partial.mp4'), rendered: 3, boxes: 6};

test('the full video wins; the partial video plays only without one', () => {
  assert.deepEqual(exportedVideo({ok: true, full_video: view('seq_full.mp4'), partial_video: partial}),
    {file: view('seq_full.mp4'), partial: null});
  assert.deepEqual(exportedVideo({ok: true, partial_video: partial}), {file: partial.file, partial});
  assert.equal(exportedVideo({ok: true}), null);
  assert.equal(exportedVideo(null), null);
});

test('the label says how much is repainted, and the title adds what is left out', () => {
  assert.equal(partialBadge(partial), 'Partial video · 3 of 6 clips repainted, the rest from the source');
  assert.equal(partialTitle(partial), '3 of 6 clips repainted, the rest from the source.');
  assert.equal(partialTitle({...partial, note: 'Bridges and replacements are left out.'}),
    '3 of 6 clips repainted, the rest from the source. Bridges and replacements are left out.');
});
