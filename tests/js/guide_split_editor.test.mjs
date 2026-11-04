// The editor's Split at guide wiring, called on a stub editor: no DOM or ComfyUI is needed.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TimelineEditor } from '../../web/h3c_timeline_editor.mjs?v=20261104-dialogue-key-1';
import { FrameImages } from '../../web/h3c_frame_images.mjs?v=20261103-bridges-guide-split-1';
import { parseState, serialize } from '../../web/h3c_timeline_model.mjs?v=20261103-replacement-bridges-1';
import { guideSplitTiming, describeGuideSplitTiming } from '../../web/h3c_guide_split.mjs?v=20261103-bridges-guide-split-1';
import { CONTEXT, shotGuideTimeline } from './guide_split_fixtures.mjs';

function stubEditor(timeline) {
  const calls = [];
  const editor = {
    state: parseState(JSON.stringify(timeline)), selected: 0, selectedShot: 2,
    statusById: new Map([['a', 'done'], ['other', 'done']]),
    host: { context: () => CONTEXT, undoStep: () => calls.push('undo') },
    commit: () => calls.push(`commit:${editor.selected}`),
    inspectClip: () => calls.push('inspect'),
    frameImages: { note: (text) => calls.push(`note:${text.slice(0, 20)}`) },
  };
  return { editor, calls };
}

test('the editor splits as one undo step and selects the clip that opens on the guide', () => {
  const { editor, calls } = stubEditor(shotGuideTimeline());
  const note = TimelineEditor.prototype.splitClipAtGuide.call(editor, 0, editor.state.boxes[0].previews[0]);
  assert.deepEqual(calls, ['undo', 'commit:1', 'undo', 'inspect', 'note:Clip 1 now ends on t']);
  assert.equal(editor.state.boxes.length, 2);
  assert.equal(editor.selectedShot, 1);
  assert.deepEqual([...editor.statusById.keys()], ['other']);
  assert.match(note, /^Clip 1 now ends on the guide/);
});

test('a refused split changes nothing but the undo checkpoint', () => {
  const { editor, calls } = stubEditor(shotGuideTimeline());
  const before = serialize(editor.state);
  const first = { ...editor.state.boxes[0].previews[0], target: { kind: 'first' }, frame: 0 };
  editor.state.boxes[0].previews.push(first);
  assert.throws(() => TimelineEditor.prototype.splitClipAtGuide.call(editor, 0, first), /First frame/);
  editor.state.boxes[0].previews.pop();
  assert.equal(serialize(editor.state), before);
  assert.deepEqual(calls, ['undo']);
});

test('the marker panel splits at its own accepted guide, read from the live timeline', () => {
  const { editor } = stubEditor(shotGuideTimeline());
  const split = [];
  editor.splitClipAtGuide = (index, preview) => split.push([index, preview.guide.filename]);
  const panel = Object.assign(Object.create(FrameImages.prototype), {
    editor, host: editor.host, boxId: 'a', target: { kind: 'shot', shot: 2 }, live: () => editor.state,
  });
  panel.splitAtGuide();
  assert.deepEqual(split, [[0, 'guide_a.png']]);
});

test('the button tooltip states both lengths and the grid adjustment', () => {
  const state = parseState(JSON.stringify(shotGuideTimeline()));
  const timing = guideSplitTiming(state, 0, state.boxes[0].previews[0], CONTEXT);
  assert.equal(describeGuideSplitTiming(timing, 0), 'Make Clip 1 end on this guide (4.46 s) and a new Clip 2 continue '
    + 'from it (4.25 s), so H3 generates toward the guide instead of inserting it. Adds 0.71 s for H3’s frame grid; '
    + 'the guide lands 0.42 s later.');
});
