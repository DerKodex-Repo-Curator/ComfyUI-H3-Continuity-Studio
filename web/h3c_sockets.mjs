// Guided mode hides the H3 Timeline's unconnected sockets that belong to features not in use; Full shows all of them.
// The engine never sees this: removed optional inputs are simply absent from the prompt, and ComfyUI restores every
// socket from the node definition when a workflow loads (spike V1-S1), so saved files keep the full socket list.

// Always on the face in Guided mode. `story` stays so H3 Story can be wired by hand.
const CORE = new Set(['clip', 'vae', 'project', 'images.image1', 'story']);
const FEATURE_SOCKETS = {
  references: ['images.', 'videos.', 'still_recipe'],
  sound: ['audio_vae', 'audios.', 'video_audios.'],
};

export function socketShown(name, mode, features) {
  if (mode !== 'guided' || CORE.has(name)) return true;
  return Object.entries(FEATURE_SOCKETS).some(([feature, names]) => features.has(feature)
    && names.some((item) => item.endsWith('.') ? name.startsWith(item) : name === item));
}

// The definition's own sockets, to put back the ones Guided removed: [{name, type, ...extra}].
export function socketSpecs(node) {
  return (node.inputs ?? []).filter((input) => !input.widget)
    .map(({name, type, shape, tooltip, localized_name, label}) => ({name, type, shape, tooltip, localized_name, label}));
}

// Makes `node`'s sockets match the mode: removes hidden unconnected ones and puts back missing shown ones.
// Linked inputs are never removed. Returns whether anything changed.
export function syncSockets(node, specs, mode, features) {
  let changed = false;
  for (let index = (node.inputs?.length ?? 0) - 1; index >= 0; index--) {
    const input = node.inputs[index];
    if (input.widget || input.link != null || socketShown(input.name, mode, features)) continue;
    node.removeInput(index);
    changed = true;
  }
  for (const spec of specs) {
    if (!socketShown(spec.name, mode, features) || node.inputs?.some((input) => input.name === spec.name)) continue;
    const {name, type, ...extra} = spec;
    // ComfyUI keeps links by slot index, so the socket goes where addInput puts it (after the sockets already there,
    // before the widget inputs) and is never moved: moving a slot would leave its neighbours' links behind.
    node.addInput(name, type, Object.fromEntries(Object.entries(extra).filter(([, value]) => value != null)));
    changed = true;
  }
  return changed;
}
