// Prints the guide-split fixtures, before and after the browser edit, as JSON for tests/test_guide_split_server.py.
import { parseState, serialize } from '../../web/h3c_timeline_model.mjs?v=20261103-replacement-bridges-1';
import { splitAtGuide } from '../../web/h3c_guide_split.mjs?v=20261103-bridges-guide-split-1';
import { CONTEXT, shotGuideTimeline, continuingTimeline } from './guide_split_fixtures.mjs';

function split(timeline, index, pick) {
  const state = parseState(JSON.stringify(timeline));
  const result = splitAtGuide(state, index, pick(state.boxes[index].previews), CONTEXT);
  return { before: JSON.stringify(timeline), after: serialize(state), index, result };
}

process.stdout.write(JSON.stringify({
  context: CONTEXT,
  shot: split(shotGuideTimeline(), 0, (previews) => previews[0]),
  continuing: split(continuingTimeline(), 1, (previews) => previews[0]),
}));
