import { test } from 'node:test';
import assert from 'node:assert/strict';
import { socketShown, socketSpecs, syncSockets } from '../../web/h3c_sockets.mjs?v=20261105-v1-1';

const SOCKETS = ['clip', 'vae', 'audio_vae', 'images.image1', 'audios.audio1', 'negative', 'still_recipe', 'story',
  'videos.video1', 'video_audios.video_audio1', 'project'];
const WIDGETS = ['name', 'width', 'timeline'];

// A LiteGraph-shaped Timeline node: sockets first, then widget inputs, links kept by slot index.
function timeline() {
  const links = new Map();
  const node = {
    graph: {links},
    inputs: [...SOCKETS.map((name) => ({name, type: 'T', shape: 7})), ...WIDGETS.map((name) => ({name, type: 'W', widget: {name}}))],
    removeInput(index) {
      node.inputs.splice(index, 1);
      for (const [slot, input] of node.inputs.entries()) if (input.link != null) links.get(input.link).target_slot = slot;
    },
    // Like ComfyUI's frontend: a new socket goes before the widget inputs. Later inputs shift, so their links do too.
    addInput(name, type, extra) {
      const at = node.inputs.findIndex((input) => input.widget);
      node.inputs.splice(at < 0 ? node.inputs.length : at, 0, {name, type, link: null, ...extra});
      for (const [slot, input] of node.inputs.entries()) if (input.link != null) links.get(input.link).target_slot = slot;
    },
    link(name, id) {
      const slot = node.inputs.findIndex((input) => input.name === name);
      node.inputs[slot].link = id;
      links.set(id, {id, target_slot: slot});
    },
  };
  return node;
}
const names = (node) => node.inputs.filter((input) => !input.widget).map((input) => input.name);

test('full mode shows every socket; guided core shows clip, vae, one picture, story and project', () => {
  assert.ok(SOCKETS.every((name) => socketShown(name, 'full', new Set())));
  assert.deepEqual(SOCKETS.filter((name) => socketShown(name, 'guided', new Set())),
    ['clip', 'vae', 'images.image1', 'story', 'project']);
  assert.deepEqual(SOCKETS.filter((name) => socketShown(name, 'guided', new Set(['sound']))),
    ['clip', 'vae', 'audio_vae', 'images.image1', 'audios.audio1', 'story', 'video_audios.video_audio1', 'project']);
  assert.ok(socketShown('images.image4', 'guided', new Set(['references'])));
  assert.ok(!socketShown('images.image2', 'guided', new Set()));
});

test('guided removes hidden unconnected sockets but keeps linked ones and their links', () => {
  const node = timeline(), specs = socketSpecs(node);
  node.link('negative', 7);
  node.link('name', 8);
  assert.equal(syncSockets(node, specs, 'guided', new Set()), true);
  assert.deepEqual(names(node), ['clip', 'vae', 'images.image1', 'negative', 'story', 'project']);
  assert.equal(node.graph.links.get(7).target_slot, 3);
  assert.equal(node.inputs[node.graph.links.get(8).target_slot].name, 'name');
  assert.equal(syncSockets(node, specs, 'guided', new Set()), false);
});

test('back to full puts every socket back and keeps links on their inputs', () => {
  const node = timeline(), specs = socketSpecs(node);
  node.link('negative', 7);
  node.link('timeline', 9);
  syncSockets(node, specs, 'guided', new Set());
  syncSockets(node, specs, 'full', new Set());
  assert.deepEqual(names(node).sort(), [...SOCKETS].sort());
  assert.deepEqual(node.inputs.slice(SOCKETS.length).map((input) => input.name), WIDGETS);
  assert.equal(node.inputs[node.graph.links.get(7).target_slot].name, 'negative');
  assert.equal(node.inputs[node.graph.links.get(9).target_slot].name, 'timeline');
  assert.equal(node.inputs.find((input) => input.name === 'audio_vae').shape, 7);
});

test('connecting an add-on brings back only its sockets', () => {
  const node = timeline(), specs = socketSpecs(node);
  syncSockets(node, specs, 'guided', new Set());
  syncSockets(node, specs, 'guided', new Set(['references']));
  assert.deepEqual(names(node), ['clip', 'vae', 'images.image1', 'story', 'project', 'still_recipe', 'videos.video1']);
});
