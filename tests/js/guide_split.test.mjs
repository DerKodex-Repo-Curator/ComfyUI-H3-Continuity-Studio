import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseState, serialize } from '../../web/h3c_timeline_model.mjs?v=20261103-replacement-bridges-1';
import { guideSplitTiming, splitAtGuide, describeGuideSplit } from '../../web/h3c_guide_split.mjs?v=20261103-bridges-guide-split-1';
import { CONTEXT, guideFile, shotGuideTimeline, continuingTimeline, noFirstTimeline } from './guide_split_fixtures.mjs';

const load = (timeline) => parseState(JSON.stringify(timeline));
const plain = (frames, previews, extra = {}) => load({
  prompt: '', boxes: [{ id: 'a', frames, prompt: 'A slow pan across the harbour.', seed: 1, cut: false, first: '', last: '', previews, ...extra }],
});

test('timing: a fresh clip ends on the guide and the right clip continues on the grid', () => {
  const state = load(shotGuideTimeline());
  const timing = guideSplitTiming(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.deepEqual({ ...timing }, {
    frame: 96, left: 107, right: 102, needLeft: 97, needRight: 95, fresh: true, carry: 0, generated: 96,
    offset: 58, moved: 10, added: 17,
  });
});

test('timing: a continuing clip counts local frame 0 as the shared boundary', () => {
  const state = load(continuingTimeline());
  const timing = guideSplitTiming(state, 1, state.boxes[1].previews[0], CONTEXT);
  assert.equal(timing.left, 85);
  assert.equal(timing.right, 136);
  assert.equal(timing.generated, 118);
  assert.equal(timing.offset, 80);
  assert.equal(timing.added, 17);
});

test('timing: an exact clip keeps its right half exact and puts the left half on the grid', () => {
  const state = plain(100, [{ shot: 4, frame: 60, guide: guideFile() }], { exact: true });
  const result = splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.equal(result.left, 73);
  assert.equal(result.right, 39);
  assert.equal(result.added, 12);
  assert.equal(state.boxes[1].exact, true);
  assert.equal(state.boxes[1].frames, 39);
});

test('refusals: endpoints, candidates, too close to the start, past the clip limit', () => {
  const first = plain(192, [{ target: { kind: 'first' }, frame: 0, guide: guideFile() }]);
  assert.throws(() => guideSplitTiming(first, 0, first.boxes[0].previews[0], CONTEXT), /already the clip’s First/);
  const last = plain(192, [{ target: { kind: 'last' }, frame: 191, guide: guideFile() }]);
  assert.throws(() => guideSplitTiming(last, 0, last.boxes[0].previews[0], CONTEXT), /already the clip’s Last/);
  const candidate = plain(192, [{ shot: 2, frame: 90, images: [{ file: guideFile() }] }]);
  assert.throws(() => guideSplitTiming(candidate, 0, candidate.boxes[0].previews[0], CONTEXT), /Use an image as this marker’s guide/);
  const early = plain(192, [{ shot: 2, frame: 10, guide: guideFile() }]);
  assert.throws(() => guideSplitTiming(early, 0, early.boxes[0].previews[0], 60), /too close to the start.*22 frames.*60/);
  const long = plain(362, [{ shot: 2, frame: 30, guide: guideFile() }]);
  assert.throws(() => guideSplitTiming(long, 0, long.boxes[0].previews[0], CONTEXT), /clip limit/);
  const removed = plain(192, [{ shot: 2, frame: 90, guide: guideFile() }]);
  assert.throws(() => guideSplitTiming(removed, 0, { ...removed.boxes[0].previews[0] }, CONTEXT), /removed/);
});

test('a refused split leaves the timeline untouched', () => {
  const state = load(shotGuideTimeline());
  state.boxes[0].prompt = state.boxes[0].prompt.replace('At 00:06.000, ', '');
  const before = serialize(state);
  assert.throws(() => splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT), /increasing cut timestamp/);
  assert.equal(serialize(state), before);
});

test('prompt: a guide on a shot start splits before that shot and re-bases later times', () => {
  const state = load(shotGuideTimeline());
  const result = splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.equal(result.mid, false);
  assert.equal(state.boxes[0].prompt, '[Shot 1] A woman walks along the pier.');
  assert.equal(state.boxes[1].prompt, '[Shot 1] a close-up of her face.\n[Shot 2] At 00:03.583, the camera cuts to the sea.');
});

test('prompt: a guide inside a shot keeps that shot in both halves', () => {
  const state = load(continuingTimeline());
  const result = splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  assert.equal(result.mid, true);
  assert.equal(result.shot, 1);
  const [left, right] = [state.boxes[1].prompt, state.boxes[2].prompt];
  assert.match(left, /summary: \[reference generation \+ keyframe completion\] 1 shot featuring <Subject 1>\./);
  assert.match(left, /\[Shot 1\] <Subject 1> walks along the pier, then stops at the railing\.\n\noverall_soundscape: Waves\./);
  assert.match(right, /\[Shot 1\] <Subject 1> walks along the pier, then stops at the railing\.\n\[Shot 2\] At 00:02\.667, the camera cuts to <Subject 1>/);
  assert.match(right, /<Subject 1> is the woman from @image1\./);
});

test('prompt: a prompt without shot markers is kept by both halves', () => {
  const state = plain(192, [{ shot: 2, frame: 90, guide: guideFile() }]);
  splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.equal(state.boxes[0].prompt, 'A slow pan across the harbour.');
  assert.equal(state.boxes[1].prompt, 'A slow pan across the harbour.');
});

test('boxes: the left keeps identity and First; the right is a new continuing clip with the Last', () => {
  const timeline = shotGuideTimeline();
  Object.assign(timeline.boxes[0], { first: 'image2', last: 'image3', cut: true, new_scene: true,
    join: { kind: 'new_scene', note: 'dawn' }, cast: { '<Subject 1>': 'e1' }, source: { frame: {} } });
  timeline.boxes = [{ id: 'z', frames: 107, prompt: 'Before.', seed: 3, cut: false, first: '', last: '' }, ...timeline.boxes];
  const state = load(timeline);
  splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  const [left, right] = [state.boxes[1], state.boxes[2]];
  assert.deepEqual([left.id, left.seed, left.first, left.last, left.cut, left.new_scene, left.join?.note], ['a', 7, 'image2', '', true, true, 'dawn']);
  assert.notEqual(right.id, 'a');
  assert.deepEqual([right.first, right.last, right.cut, right.new_scene, right.join], ['', 'image3', false, undefined, undefined]);
  for (const half of [left, right]) assert.deepEqual([half.cast, half.source], [undefined, undefined]);
});

test('previews: the guide closes the left and opens the right; later targets are renumbered', () => {
  const state = load(shotGuideTimeline());
  splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.deepEqual(state.boxes[0].previews, [{ target: { kind: 'last' }, frame: 106, guide: guideFile() }]);
  assert.deepEqual(state.boxes[1].previews, [
    { still_prompt: 'Close-up of her face.', target: { kind: 'first' }, frame: 0, guide: guideFile(),
      images: [{ file: guideFile('cand_b') }] },
    { target: { kind: 'shot', shot: 2 }, frame: 48, guide: guideFile('guide_c') },
  ]);
});

test('previews, plates and dependants after the guide move to the right clip', () => {
  const state = load(continuingTimeline());
  splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  const [left, right, after] = state.boxes.slice(1);
  assert.deepEqual(left.previews, [{ target: { kind: 'last' }, frame: 85, guide: guideFile() }]);
  assert.deepEqual(right.previews.map((p) => [p.target, p.frame, !!p.guide]),
    [[{ kind: 'first' }, 0, true], [{ kind: 'last' }, 136, false]]);
  assert.deepEqual(left.plate_changes.map((p) => p.frame), [20]);
  assert.deepEqual(right.plate_changes.map((p) => p.frame), [70]);
  assert.deepEqual(state.bible.entities[0].pins, [{ box: right.id, frame: 20 }, { box: 'b', frame: 10 }]);
  assert.deepEqual(after.memories, [{ box: right.id, frame: 40, label: 'the railing' }]);
});

test('legacy records never take Shot 1 (the First) away from the opening guide', () => {
  const state = load(continuingTimeline());
  state.boxes[1].previews.push({ shot: 1, frame: 120, images: [{ file: guideFile('late') }] });
  splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  const legacy = state.boxes[2].previews.find((p) => !p.target);
  assert.deepEqual([legacy.shot, legacy.frame], [3, 40]);
});

test('references: cached RefMods keep both halves FLF2VA when they open on a frame', () => {
  const state = load(continuingTimeline());
  const result = splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  assert.deepEqual([result.refmods, result.raw, result.noFirst], [[1, 2], [], []]);
  assert.equal(state.boxes[1].flf_refmods, true);
  assert.equal(state.boxes[2].flf_refmods, true);
});

test('references: a fresh half without a First, or with raw audio, is reported instead', () => {
  let state = load(noFirstTimeline());
  let result = splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.deepEqual([result.refmods, result.raw, result.noFirst], [[], [], [0]]);
  assert.equal(state.boxes[0].flf_refmods, undefined);
  assert.match(describeGuideSplit(result), /Clip 1 has references but no First frame/);

  const opened = noFirstTimeline();
  opened.boxes[0].previews.unshift({ target: { kind: 'first' }, frame: 0, guide: guideFile('opening') });
  state = load(opened);
  result = splitAtGuide(state, 0, state.boxes[0].previews[1], CONTEXT);
  assert.deepEqual(result.refmods, [0]);
  assert.equal(state.boxes[0].previews[0].target.kind, 'first');

  const voiced = shotGuideTimeline();
  voiced.boxes[0].prompt = voiced.boxes[0].prompt.replace('the sea.', 'the sea while @audio1 plays.');
  state = load(voiced);
  result = splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.deepEqual(result.raw, [1]);
  assert.match(describeGuideSplit(result), /Clip 2 uses raw audio or video references/);
});

test('the original choice of cached RefMods is inherited by both halves', () => {
  const timeline = shotGuideTimeline();
  timeline.boxes[0].flf_refmods = true;
  const state = load(timeline);
  const result = splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.deepEqual(result.refmods, []);
  assert.deepEqual(state.boxes.map((box) => box.flf_refmods), [true, true]);
});

test('the split state survives a save and reload unchanged', () => {
  const state = load(continuingTimeline());
  splitAtGuide(state, 1, state.boxes[1].previews[0], CONTEXT);
  const saved = serialize(state);
  assert.equal(serialize(parseState(saved)), saved);
});

test('the note says what changed and what moved', () => {
  const state = load(shotGuideTimeline());
  const note = describeGuideSplit(splitAtGuide(state, 0, state.boxes[0].previews[0], CONTEXT));
  assert.equal(note, 'Clip 1 now ends on the guide (4.46 s) and Clip 2 continues from it (4.25 s). '
    + 'H3’s frame grid adds 0.71 s; the guide lands 0.42 s later.');
});
