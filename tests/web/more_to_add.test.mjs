import test from 'node:test';
import assert from 'node:assert/strict';
import {findAll, installDom} from './fake_dom.mjs';
import {ADD_ONS, addAddOn, missingAddOns, moreRow} from '../../web/h3c_more_to_add.mjs?v=20261105-v1-1';
import {connectedFeatures} from '../../web/h3c_features.mjs?v=20261105-v1-1';

installDom();

// A LiteGraph-shaped graph whose nodes can connect, as node.connect does in ComfyUI.
function graph() {
  const nodes = new Map(), links = new Map();
  let nextId = 1, nextLink = 1;
  const g = {
    links, _nodes: [],
    getNodeById: (id) => nodes.get(id) ?? null,
    add(node) { node.id ??= nextId++; nodes.set(node.id, node); g._nodes.push(node); return node; },
  };
  g.create = (type) => {
    const inputs = type === 'H3C_Timeline' ? ['clip', 'story', 'project'] : type.startsWith('H3C_Plus') ? ['project'] : [];
    const output = type === 'H3C_Story' ? 'H3C_STORY' : type.startsWith('H3C_Plus') ? 'H3C_PROJECT' : 'MODEL';
    const node = {type, mode: 0, pos: [0, 0], size: [300, 120], inputs: inputs.map((name) => ({name, link: null})),
      outputs: [{type: output}]};
    node.connect = (slot, target, input) => {
      const id = nextLink++;
      links.set(id, {id, origin_id: node.id, origin_slot: slot, target_id: target.id});
      target.inputs[input].link = id;
    };
    return node;
  };
  return g;
}

test('missingAddOns lists only unconnected add-ons', () => {
  assert.deepEqual(missingAddOns(new Set(['sound', 'story'])).map((item) => item.feature), ['references', 'continuity', 'long']);
  assert.equal(missingAddOns(new Set(ADD_ONS.map((item) => item.feature))).length, 0);
});

test('addAddOn wires project and chains behind an existing add-on', () => {
  const g = graph(), core = g.add(Object.assign(g.create('H3C_Timeline'), {pos: [1000, 100]}));
  const sound = addAddOn(g, core, 'H3C_PlusSound', g.create);
  assert.deepEqual([...connectedFeatures(g, core)], ['sound']);
  assert.ok(sound.pos[0] < core.pos[0]);
  const refs = addAddOn(g, core, 'H3C_PlusReferences', g.create);
  assert.deepEqual([...connectedFeatures(g, core)].sort(), ['references', 'sound']);
  assert.ok(refs.pos[0] < sound.pos[0]);
  addAddOn(g, core, 'H3C_Story', g.create);
  assert.equal(connectedFeatures(g, core).has('story'), true);
  addAddOn(g, core, 'H3C_ContextWindows', g.create);
  assert.equal(connectedFeatures(g, core).has('long'), true);
});

test('row lists each missing add-on with its benefit and adds it on click', () => {
  const added = [];
  const row = moreRow(new Set(['references']), (item) => added.push(item.type));
  const buttons = findAll(row, (node) => node.tagName === 'BUTTON');
  assert.deepEqual(buttons.map((node) => node.textContent),
    ['+ H3 + Sound', '+ H3 + Continuity tools', '+ H3 Story', '+ H3 Context Windows']);
  assert.ok(buttons.every((node) => node.title.length > 20));
  buttons[0].click();
  assert.deepEqual(added, ['H3C_PlusSound']);
});

test('row is absent when everything is connected', () => {
  assert.equal(moreRow(new Set(ADD_ONS.map((item) => item.feature)), () => {}).hidden, true);
});
