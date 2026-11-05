import test from 'node:test';
import assert from 'node:assert/strict';
import {buttonNamed, installDom} from './fake_dom.mjs';
import * as model from '../../web/h3c_timeline_model.mjs';
import {featureNotices, hiddenFeatures, hiddenWithData, visibleClipTabs, visiblePages}
  from '../../web/h3c_gating.mjs?v=20261105-v1-1';
import {setUiMode, uiMode} from '../../web/h3c_features.mjs?v=20261105-v1-1';

installDom();

const PAGES_0_12 = ['viewer', 'story', 'cast', 'pictures', 'refmods'];
const TABS_0_12 = ['prompt', 'still', 'takes', 'box'];
const state = (extra = {}) => model.parseState(JSON.stringify({version: 1, prompt: '', boxes: [
  {id: 'a', frames: 107, prompt: 'One.', seed: 1}, {id: 'b', frames: 107, prompt: 'Two.', seed: 2}], ...extra}));

test('full mode returns the 0.12.x page and tab lists', () => {
  assert.deepEqual(visiblePages('full', new Set()), PAGES_0_12);
  assert.deepEqual(visibleClipTabs('full', new Set()), TABS_0_12);
  assert.deepEqual(hiddenFeatures('full', new Set()), []);
});

test('guided with no features shows only core', () => {
  assert.deepEqual(visiblePages('guided', new Set()), ['viewer']);
  assert.deepEqual(visibleClipTabs('guided', new Set()), ['prompt', 'box']);
  assert.deepEqual(hiddenFeatures('guided', new Set()), ['references', 'sound', 'continuity', 'story', 'long']);
});

test('guided with sound adds audio and text only', () => {
  const features = new Set(['sound']);
  assert.deepEqual(visiblePages('guided', features), ['viewer']);
  assert.deepEqual(visibleClipTabs('guided', features), ['prompt', 'box']);
  assert.deepEqual(hiddenFeatures('guided', features), ['references', 'continuity', 'story', 'long']);
});

test('each add-on opens its own pages and tabs', () => {
  assert.deepEqual(visiblePages('guided', new Set(['references'])), ['viewer', 'pictures', 'refmods']);
  assert.deepEqual(visibleClipTabs('guided', new Set(['references'])), ['prompt', 'still', 'box']);
  assert.deepEqual(visibleClipTabs('guided', new Set(['continuity'])), ['prompt', 'takes', 'box']);
  assert.deepEqual(visiblePages('guided', new Set(['story'])), ['viewer', 'story', 'cast']);
});

test('hidden but populated feature is listed by hiddenWithData and the notice has an Add the node button', () => {
  const full = state({audio_clips: [{slot: 'audio1', start: 0, duration: 1}], bridges: [{before: 'b', mode: 'replace'}],
    pictures: [{id: 'p1'}], bible: {characters: []}});
  assert.deepEqual(hiddenWithData(full, new Set(['continuity'])), ['references', 'sound', 'story']);
  assert.deepEqual(hiddenWithData(state(), new Set()), []);
  const memory = state({boxes: [{id: 'a', frames: 107, prompt: 'One.', memory: 'selected'}]});
  assert.deepEqual(hiddenWithData(memory, new Set()), ['continuity']);
  for (const memory of ['off', 'scene']) {
    const plain = state({boxes: [{id: 'a', frames: 107, prompt: 'One.', memory, memories: []}]});
    assert.deepEqual(hiddenWithData(plain, new Set()), [], memory);
  }
  const added = [];
  const root = featureNotices(['sound'], (feature) => added.push(feature));
  assert.match(root.textContent, /H3 \+ Sound/);
  buttonNamed(root, 'Add the node').click();
  assert.deepEqual(added, ['sound']);
});

test('toggle Guided to Full to Guided leaves the Timeline JSON byte-identical', () => {
  const json = model.serialize(state({audio_clips: [{slot: 'audio1', start: 0, duration: 1}]}));
  const node = {properties: {}, widgets: [{name: 'timeline', value: json}]};
  for (const mode of ['guided', 'full', 'guided']) setUiMode(node, mode);
  assert.equal(node.widgets[0].value, json);
  assert.deepEqual(node.properties, {h3c_ui: 'guided'});
});

test('an old workflow without h3c_ui opens full', () => {
  const node = {properties: {h3c_project: {mode: 'attached'}}};
  assert.equal(uiMode(node), 'full');
  assert.deepEqual(visiblePages(uiMode(node), new Set()), PAGES_0_12);
});
