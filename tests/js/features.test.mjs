import { test } from 'node:test';
import assert from 'node:assert/strict';
import { connectedFeatures, mirrorPlan, ownedSettings, setUiMode, uiMode } from '../../web/h3c_features.mjs?v=20261105-v1-2';

// A LiteGraph-shaped graph: nodes with typed inputs, links by id.
function graph() {
  const nodes = new Map(), links = new Map();
  let nextLink = 1;
  return {
    links, _nodes: [],
    getNodeById: (id) => nodes.get(id) ?? null,
    add(id, type, {mode = 0, inputs = [], widgets = {}} = {}) {
      const node = {id, type, mode, inputs: inputs.map((name) => ({name, link: null})),
        widgets: Object.entries(widgets).map(([name, value]) => ({name, value}))};
      nodes.set(id, node);
      this._nodes.push(node);
      return node;
    },
    link(from, to, input) {
      const id = nextLink++;
      links.set(id, {id, origin_id: from.id, origin_slot: 0, target_id: to.id});
      to.inputs.find((slot) => slot.name === input).link = id;
      return id;
    },
  };
}

const timeline = (g, id = 1) => g.add(id, 'H3C_Timeline', {inputs: ['clip', 'story', 'project']});
const addOn = (g, id, type, options = {}) => g.add(id, type, {inputs: ['project'], ...options});

test('walks a chain of add-ons in any order', () => {
  const g = graph(), core = timeline(g);
  const sound = addOn(g, 2, 'H3C_PlusSound'), refs = addOn(g, 3, 'H3C_PlusReferences');
  const tools = addOn(g, 4, 'H3C_PlusContinuity');
  g.link(sound, core, 'project');
  g.link(tools, sound, 'project');
  g.link(refs, tools, 'project');
  assert.deepEqual([...connectedFeatures(g, core)].sort(), ['continuity', 'references', 'sound']);
});

test('nothing connected: no features', () => {
  const g = graph(), core = timeline(g);
  addOn(g, 2, 'H3C_PlusSound');
  assert.deepEqual([...connectedFeatures(g, core)], []);
});

test('ignores muted (mode 2) and bypassed (mode 4) add-ons', () => {
  const g = graph(), core = timeline(g);
  const bypassed = addOn(g, 2, 'H3C_PlusSound', {mode: 4}), refs = addOn(g, 3, 'H3C_PlusReferences');
  g.link(bypassed, core, 'project');
  g.link(refs, bypassed, 'project');
  // A bypassed add-on passes the chain on, as ComfyUI does when it runs the prompt.
  assert.deepEqual([...connectedFeatures(g, core)], ['references']);
  bypassed.mode = 2;
  // A muted add-on sends nothing, so nothing before it arrives either.
  assert.deepEqual([...connectedFeatures(g, core)], []);
});

test('two Timeline nodes keep separate chains', () => {
  const g = graph(), first = timeline(g, 1), second = timeline(g, 2);
  g.link(addOn(g, 3, 'H3C_PlusSound'), first, 'project');
  g.link(addOn(g, 4, 'H3C_PlusReferences'), second, 'project');
  assert.deepEqual([...connectedFeatures(g, first)], ['sound']);
  assert.deepEqual([...connectedFeatures(g, second)], ['references']);
});

test('a looping project link terminates', () => {
  const g = graph(), core = timeline(g);
  const a = addOn(g, 2, 'H3C_PlusSound'), b = addOn(g, 3, 'H3C_PlusContinuity');
  g.link(a, core, 'project');
  g.link(b, a, 'project');
  g.link(a, b, 'project');
  assert.deepEqual([...connectedFeatures(g, core)].sort(), ['continuity', 'sound']);
});

test('a dangling link id is ignored', () => {
  const g = graph(), core = timeline(g);
  core.inputs.find((slot) => slot.name === 'project').link = 99;
  assert.deepEqual([...connectedFeatures(g, core)], []);
});

test('story link gates story', () => {
  const g = graph(), core = timeline(g);
  const story = g.add(2, 'H3C_Story');
  assert.equal(connectedFeatures(g, core).has('story'), false);
  g.link(story, core, 'story');
  assert.equal(connectedFeatures(g, core).has('story'), true);
  story.mode = 4;
  assert.equal(connectedFeatures(g, core).has('story'), false);
});

test('Context Windows present and active gates long, muted does not', () => {
  const g = graph(), core = timeline(g);
  const windows = g.add(2, 'H3C_ContextWindows', {mode: 2});
  assert.equal(connectedFeatures(g, core).has('long'), false);
  windows.mode = 0;
  assert.equal(connectedFeatures(g, core).has('long'), true);
  windows.mode = 4;
  g.add(3, 'H3C_JoinChain');
  assert.equal(connectedFeatures(g, core).has('long'), true);
});

test('owned settings come from the add-on nearest the Timeline', () => {
  const g = graph(), core = timeline(g);
  const near = addOn(g, 2, 'H3C_PlusSound', {widgets: {carry_audio: false, audio_context_frames: 12}});
  const far = addOn(g, 3, 'H3C_PlusSound', {widgets: {carry_audio: true, audio_context_frames: 0}});
  const refs = addOn(g, 4, 'H3C_PlusReferences', {widgets: {ref_image_size: 'max'}});
  g.link(near, core, 'project');
  g.link(far, near, 'project');
  g.link(refs, far, 'project');
  assert.deepEqual(ownedSettings(g, core), {carry_audio: false, audio_context_frames: 12, ref_image_size: 'max'});
  near.mode = 4;
  assert.deepEqual(ownedSettings(g, core), {carry_audio: true, audio_context_frames: 0, ref_image_size: 'max'});
});

test('a legacy Reroute node passes the chain on', () => {
  const g = graph(), core = timeline(g);
  const reroute = g.add(2, 'Reroute', {inputs: ['']});
  g.link(reroute, core, 'project');
  g.link(addOn(g, 3, 'H3C_PlusSound'), reroute, '');
  assert.deepEqual([...connectedFeatures(g, core)], ['sound']);
});

test('mirroring keeps the Timeline value and puts it back when the add-on goes', () => {
  const widgets = {carry_audio: true, ref_image_size: 'match'}, read = (name) => widgets[name];
  let plan = mirrorPlan({carry_audio: false}, read);
  assert.deepEqual(plan, {writes: {carry_audio: false}, own: {carry_audio: true}});
  widgets.carry_audio = false;
  plan = mirrorPlan({carry_audio: false}, read, plan.own);
  assert.deepEqual(plan, {writes: {}, own: {carry_audio: true}});
  plan = mirrorPlan({}, read, plan.own);
  assert.deepEqual(plan, {writes: {carry_audio: true}, own: {}});
  assert.deepEqual(mirrorPlan({ref_image_size: 'match'}, read), {writes: {}, own: {}});
});

test('uiMode defaults to full when the property is absent', () => {
  assert.equal(uiMode({}), 'full');
  assert.equal(uiMode({properties: {}}), 'full');
  assert.equal(uiMode({properties: {h3c_ui: 'something else'}}), 'full');
});

test('a fresh node gets guided only through setUiMode', () => {
  const node = {};
  setUiMode(node, 'guided');
  assert.equal(uiMode(node), 'guided');
  setUiMode(node, 'full');
  assert.deepEqual(node.properties, {h3c_ui: 'full'});
});
