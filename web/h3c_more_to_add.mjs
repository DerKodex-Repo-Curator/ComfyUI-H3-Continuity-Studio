// The optional H3 nodes a Timeline can grow into, and how to add one next to it. UI only.
import {ADD_ONS as ADD_ON_FEATURES, connectedFeatures} from './h3c_features.mjs?v=20261105-v1-1';

// One plain sentence per node about what it does for the user's video. `wire` names how it joins the Timeline.
export const ADD_ONS = [
  {type: 'H3C_PlusReferences', feature: 'references', title: 'H3 + References', wire: 'project',
    benefit: 'Use pictures as references and pick first and last frames, so people and places look the same.'},
  {type: 'H3C_PlusSound', feature: 'sound', title: 'H3 + Sound', wire: 'project',
    benefit: 'Add audio lanes, dialogue and timed text that H3 hears and carries across joins.'},
  {type: 'H3C_PlusContinuity', feature: 'continuity', title: 'H3 + Continuity tools', wire: 'project',
    benefit: 'Compare takes, bridge cuts with new frames, and let a clip remember earlier clips.'},
  {type: 'H3C_Story', feature: 'story', title: 'H3 Story', wire: 'story',
    benefit: 'Write every clip prompt from one idea with a language model you connect.'},
  {type: 'H3C_ContextWindows', feature: 'long', title: 'H3 Context Windows', wire: null,
    benefit: 'Render one clip longer than H3’s 362 frames. Place it between your model loader and sampler.'},
];

export function missingAddOns(features) {
  return ADD_ONS.filter((item) => !features.has(item.feature));
}

function linkOf(graph, id) {
  return graph?.links?.get?.(id) ?? graph?.links?.[id] ?? null;
}

// The node whose project input is the open end of `core`'s chain of add-ons: `core` itself when nothing feeds it.
function chainEnd(graph, core) {
  const seen = new Set();
  let end = core;
  for (;;) {
    const id = end.inputs?.find((slot) => slot.name === 'project')?.link;
    const link = id == null ? null : linkOf(graph, id);
    const from = link ? graph.getNodeById?.(link.origin_id) : null;
    if (!from || !(from.type in ADD_ON_FEATURES) || seen.has(from.id)) return end;
    seen.add(from.id);
    end = from;
  }
}

// Adds the node of `type` left of `core` (behind the last add-on already feeding it) and links it in.
export function addAddOn(graph, core, type, create) {
  const item = ADD_ONS.find((entry) => entry.type === type);
  if (!item) throw new Error(`H3 Timeline: unknown add-on ${type}`);
  const node = create(type);
  if (!node) throw new Error(`H3 Timeline: ComfyUI could not create ${item.title}; is the node pack up to date?`);
  const target = item.wire === 'project' ? chainEnd(graph, core) : core;
  const width = node.size?.[0] ?? 300;
  const [x, y] = target.pos ?? [0, 0];
  const below = item.wire === 'project' ? 0 : (core.size?.[1] ?? 200) + 40;
  node.pos = item.wire === 'project' ? [x - width - 40, y] : [x, y + below];
  graph.add(node);
  if (item.wire) {
    const input = target.inputs?.findIndex((slot) => slot.name === item.wire);
    const output = Math.max(0, node.outputs?.findIndex((slot) => slot.type === (item.wire === 'project' ? 'H3C_PROJECT' : 'H3C_STORY')) ?? 0);
    if (input >= 0) node.connect(output, target, input);
  }
  return node;
}

export {connectedFeatures};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// "More you can add": one quiet row of the optional nodes that are not in use yet. Empty when all are.
export function moreRow(features, onAdd) {
  const root = el('section', 'h3cx-more');
  root.setAttribute('aria-label', 'More you can add');
  const missing = missingAddOns(features);
  root.hidden = !missing.length;
  if (!missing.length) return root;
  root.append(el('span', 'h3cx-more-title', 'More you can add'));
  for (const item of missing) {
    const add = el('button', 'h3ct-button h3cx-more-add', `+ ${item.title}`);
    add.type = 'button';
    add.title = item.benefit;
    add.setAttribute('aria-label', `Add ${item.title}: ${item.benefit}`);
    add.addEventListener('click', (event) => { event.preventDefault?.(); onAdd(item); });
    root.append(add);
  }
  return root;
}
