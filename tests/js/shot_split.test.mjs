import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseState } from '../../web/h3c_timeline_model.mjs?v=20261103-replacement-bridges-1';
import { splitBox } from '../../web/h3c_shot_split.mjs?v=20261103-bridges-guide-split-1';
import { syncTargets, acceptedGuideFrames } from '../../web/h3c_shot_preview.mjs?v=20261012-still-prompts-1';
import { CONTEXT, guideFile, shotGuideTimeline } from './guide_split_fixtures.mjs';

test('Split before Shot N keeps a targeted Shot guide with its shot', () => {
  const state = parseState(JSON.stringify(shotGuideTimeline()));
  splitBox(state, 0, 2, CONTEXT);
  syncTargets(state, CONTEXT);
  const right = state.boxes[1];
  // Shot 2 opens the right half; Shot 3 becomes its Shot 2 and still guides that shot's frame.
  assert.deepEqual(right.previews.map((p) => [p.target, p.frame, p.guide.filename]),
    [[{ kind: 'first' }, 0, 'guide_a.png'], [{ kind: 'shot', shot: 2 }, 48, 'guide_c.png']]);
  assert.ok(right.previews.every((p) => !('shot' in p)));
  assert.deepEqual(acceptedGuideFrames(state, 1, CONTEXT), [0, 48]);
});

test('Split before Shot N still renumbers legacy records by shot', () => {
  const timeline = shotGuideTimeline();
  timeline.boxes[0].previews = [{ shot: 3, frame: 144, guide: guideFile() }];
  const state = parseState(JSON.stringify(timeline));
  splitBox(state, 0, 2, CONTEXT);
  assert.deepEqual(state.boxes[1].previews.map((p) => [p.shot, p.frame]), [[2, 48]]);
});
