// Which H3 features a Timeline node has turned on, read from the graph alone. UI only: the engine never calls this.
// Guided mode shows what is connected; Full mode (0.12.x workflows, no h3c_ui property) shows everything.

export const FEATURES = ['references', 'sound', 'continuity', 'story', 'long'];
export const ADD_ONS = {H3C_PlusReferences: 'references', H3C_PlusSound: 'sound', H3C_PlusContinuity: 'continuity'};
// The Timeline widgets each add-on owns; a connected add-on's value replaces the Timeline's.
export const OWNED = {H3C_PlusReferences: ['ref_image_size'], H3C_PlusSound: ['carry_audio', 'audio_context_frames']};
const LONG = new Set(['H3C_ContextWindows', 'H3C_JoinChain']);
const MUTED = 2;
const BYPASSED = 4;

function linkOf(graph, id) {
  return graph?.links?.get?.(id) ?? graph?.links?.[id] ?? null;
}

// The node feeding `node`'s input `name`, through legacy Reroute nodes.
function origin(graph, node, name, depth = 0) {
  const id = node?.inputs?.find((slot) => slot.name === name)?.link;
  const link = id == null ? null : linkOf(graph, id);
  const from = link ? graph?.getNodeById?.(link.origin_id) ?? null : null;
  return from?.type === 'Reroute' && depth < 32 ? origin(graph, from, from.inputs?.[0]?.name, depth + 1) : from;
}

// The add-ons that deliver into `node`'s project input, nearest first, as ComfyUI runs the prompt: a muted add-on
// sends nothing (so nothing before it arrives) and a bypassed one passes its own input on without adding to it.
export function activeAddOns(graph, node) {
  const found = [], seen = new Set();
  for (let current = origin(graph, node, 'project'); current && !seen.has(current.id);
    current = origin(graph, current, 'project')) {
    seen.add(current.id);
    if (!(current.type in ADD_ONS) || current.mode === MUTED) break;
    if (current.mode !== BYPASSED) found.push(current);
  }
  return found;
}

export function connectedFeatures(graph, node) {
  const features = new Set(activeAddOns(graph, node).map((addOn) => ADD_ONS[addOn.type]));
  const story = origin(graph, node, 'story');
  if (story && story.mode !== MUTED && story.mode !== BYPASSED) features.add('story');
  const nodes = graph?._nodes ?? graph?.nodes ?? [];
  if (nodes.some((other) => LONG.has(other.type) && other.mode !== MUTED && other.mode !== BYPASSED)) features.add('long');
  return features;
}

// {widget name: value} of the Timeline settings that connected add-ons replace.
export function ownedSettings(graph, node) {
  const settings = {};
  for (const addOn of activeAddOns(graph, node)) {
    for (const name of OWNED[addOn.type] ?? []) {
      const widget = addOn.widgets?.find((item) => item.name === name);
      if (widget && !(name in settings)) settings[name] = widget.value;
    }
  }
  return settings;
}

// What to write to the Timeline's widgets so a connected add-on's setting replaces its own, and the Timeline's own
// values to keep (in properties.h3c_own_settings) for when the add-on goes. `current` reads a widget's value.
export function mirrorPlan(owned, current, own = {}) {
  const writes = {}, kept = {...own};
  for (const [name, value] of Object.entries(owned)) {
    if (current(name) === undefined || current(name) === value) continue;
    if (!(name in kept)) kept[name] = current(name);
    writes[name] = value;
  }
  for (const name of Object.keys(kept)) {
    if (name in owned) continue;
    if (current(name) !== undefined && current(name) !== kept[name]) writes[name] = kept[name];
    delete kept[name];
  }
  return {writes, own: kept};
}

export function uiMode(node) {
  return node?.properties?.h3c_ui === 'guided' ? 'guided' : 'full';
}

export function setUiMode(node, mode) {
  node.properties ??= {};
  node.properties.h3c_ui = mode === 'guided' ? 'guided' : 'full';
}
