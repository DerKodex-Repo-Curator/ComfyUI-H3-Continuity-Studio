// The optional H3 nodes a Timeline can grow into, and how to add one next to it. UI only.
import {ADD_ONS as ADD_ON_FEATURES, connectedFeatures} from './h3c_features.mjs?v=20261105-v1-1';

// In the order PRODUCT.md positions them: continuity first. `benefit` is shown as text; `next` says what is left to do
// after adding it; `advanced` ones sit apart. `wire` names how the node joins the Timeline.
export const ADD_ONS = [
  {type: 'H3C_PlusContinuity', feature: 'continuity', title: 'H3 + Continuity tools', short: 'Continuity tools', wire: 'project',
    benefit: 'Keep people and places the same across cuts: takes, bridges and visual memory.',
    next: 'Takes, bridges and visual memory are now in the Studio.'},
  {type: 'H3C_PlusReferences', feature: 'references', title: 'H3 + References', short: 'References', wire: 'project',
    benefit: 'Use pictures as references and pick first and last frames.',
    next: 'Connect pictures to the Timeline’s image inputs, then mention them as @image1.'},
  {type: 'H3C_Story', feature: 'story', title: 'H3 Story', short: 'Story', wire: 'story',
    benefit: 'Write every clip prompt from one idea with a language model you connect.',
    next: 'Set its API URL and model on the node; the endpoint may cost money.'},
  {type: 'H3C_PlusSound', feature: 'sound', title: 'H3 + Sound', short: 'Sound', wire: 'project',
    benefit: 'Add audio lanes, dialogue and timed text that H3 hears and carries across joins.',
    next: 'Connect an audio VAE to the Timeline’s audio_vae input to use audio clips.'},
  {type: 'H3C_ContextWindows', feature: 'long', title: 'H3 Context Windows', short: 'Context Windows', wire: null, advanced: true,
    benefit: 'Render one clip longer than H3’s 362 frames.',
    next: 'It is not connected: place it between your model loader and the sampler.'},
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

function addButton(item, onAdd, hint) {
  const add = el('button', 'h3ct-button h3cx-more-add', `+ ${item.short}`);
  add.type = 'button';
  add.title = `Add ${item.title} to this Timeline`;
  const show = () => { hint.textContent = item.benefit; };
  add.addEventListener('mouseenter', show);
  add.addEventListener('focus', show);
  add.addEventListener('click', (event) => { event.preventDefault?.(); onAdd(item); });
  return add;
}

// "Add to this Timeline": one quiet row of the optional nodes not in use yet, with the benefit of the one under the
// pointer (or the first) as visible text. Empty when all are in use.
export function moreRow(features, onAdd) {
  const root = el('section', 'h3cx-more');
  root.setAttribute('aria-label', 'Add to this Timeline');
  const missing = missingAddOns(features);
  root.hidden = !missing.length;
  if (!missing.length) return root;
  const hint = el('span', 'h3cx-more-hint', missing[0].benefit);
  root.append(el('span', 'h3cx-more-title', 'Add to this Timeline'));
  for (const item of missing.filter((entry) => !entry.advanced)) root.append(addButton(item, onAdd, hint));
  const advanced = missing.filter((entry) => entry.advanced);
  if (advanced.length) root.append(el('span', 'h3cx-more-title h3cx-more-advanced', 'Advanced:'));
  for (const item of advanced) root.append(addButton(item, onAdd, hint));
  root.append(hint);
  return root;
}
