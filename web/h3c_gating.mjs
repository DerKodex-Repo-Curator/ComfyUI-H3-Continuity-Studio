// What the Studio shows for a Timeline: Full shows every part as in 0.12.x; Guided shows the core and the features
// whose nodes are connected. Gating hides UI only; the Timeline JSON is never changed by it.
import {FEATURES} from './h3c_features.mjs?v=20261105-v1-1';
import {ADD_ONS} from './h3c_more_to_add.mjs?v=20261105-v1-1';

const PAGES = ['viewer', 'story', 'cast', 'pictures', 'refmods'];
const TABS = ['prompt', 'still', 'takes', 'box'];
const NEEDS = {story: 'story', cast: 'story', pictures: 'references', refmods: 'references', still: 'references',
  takes: 'continuity'};

export function hiddenFeatures(mode, features) {
  return mode === 'full' ? [] : FEATURES.filter((feature) => !features.has(feature));
}

const shown = (mode, features, names) => {
  const hidden = hiddenFeatures(mode, features);
  return names.filter((name) => !hidden.includes(NEEDS[name]));
};
export const visiblePages = (mode, features) => shown(mode, features, PAGES);
export const visibleClipTabs = (mode, features) => shown(mode, features, TABS);

const some = (value) => Array.isArray(value) ? value.length > 0 : value != null && typeof value === 'object';
// The parts of a parsed Timeline each feature edits; a hidden feature holding any of them gets a notice.
// New clips start with memory 'scene' (the default), so only a choice the user made counts.
const DATA = {
  references: (state) => some(state.pictures) || some(state.refmods) || some(state.plates)
    || state.boxes.some((box) => box.first || box.last),
  sound: (state) => some(state.audio_clips) || some(state.voice_clips) || some(state.timed_text) || some(state.dialogue),
  continuity: (state) => some(state.bridges) || state.boxes.some((box) => ['selected', 'cast'].includes(box.memory) || some(box.memories)),
  story: (state) => some(state.bible) || state.boxes.some((box) => some(box.cast)),
};

export function hiddenWithData(state, features) {
  return Object.keys(DATA).filter((feature) => !features.has(feature) && DATA[feature](state));
}

const WHAT = {references: 'pictures or first and last frames', sound: 'audio or timed text',
  continuity: 'bridges or visual memory', story: 'a Story bible or cast'};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// One line per hidden feature that holds data, each with an "Add the node" action.
export function featureNotices(features, onAdd) {
  const root = el('div', 'h3cx-gate-notices');
  root.setAttribute('role', 'status');
  root.hidden = !features.length;
  for (const feature of features) {
    const item = ADD_ONS.find((entry) => entry.feature === feature);
    const line = el('p', 'h3cx-gate-notice',
      `This project has ${WHAT[feature]}. They are kept, and still rendered. Add ${item.title} to see and edit them. `);
    const add = el('button', 'h3ct-button', 'Add the node');
    add.type = 'button';
    add.title = `Add ${item.title} to this Timeline`;
    add.addEventListener('click', (event) => { event.preventDefault?.(); onAdd(feature); });
    line.append(add);
    root.append(line);
  }
  return root;
}
