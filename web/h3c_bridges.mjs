// The Box page's bridge into the selected box: the Bridge field on a cut, then the panel with the bridge's length,
// seed, prompt and state, Render bridge, Play and Remove bridge. Plain DOM without ComfyUI imports; the editor's host
// queues the run, and Play asks the Studio to show the take.
import * as model from './h3c_timeline_model.mjs?v=20261013-node-settings-1';

const STYLE_ID = 'h3cb-style';
const CSS = `
.h3cb-wrap { display: flex; flex-direction: column; gap: 4px; }
.h3cb-wrap[hidden], .h3cb-wrap [hidden] { display: none; }
.h3cb-root { display: flex; flex-direction: column; gap: 5px; padding: 6px 8px; min-width: 0;
  background: rgba(0,0,0,.12); border: 1px solid #465066; border-radius: 4px; }
.h3cb-root.problem { border-color: #e0605a; }
.h3cb-head, .h3cb-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.h3cb-title { margin-right: auto; font-weight: 600; }
.h3cb-prompt { display: flex; flex-direction: column; gap: 3px; }
.h3cb-state { color: #c7cdd8; overflow-wrap: anywhere; }
.h3cb-state.problem { color: #ff8a80; }
`;
const WAIT = "Wait for the Timeline's status to catch up with the last edit.";
const RENDER = 'Render only this bridge with its saved seed, keeping both boxes';

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function button(label, title, onClick, className = '') {
  const node = el('button', `h3ct-button ${className}`.trim(), label);
  node.type = 'button';
  node.title = title;
  node.addEventListener('click', (event) => {
    event.preventDefault();
    onClick();
  });
  return node;
}

function field(label, ...controls) {
  const node = el('label', 'h3ct-field');
  node.append(el('span', 'h3ct-label', label), ...controls);
  return node;
}

function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = el('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.append(style);
}

const sentence = (note) => `${note.charAt(0).toUpperCase()}${note.slice(1)}.`;

// The panel's state line for the bridge's status `item`, undefined until the status catches up. `problem` is the
// editor's own reason the bridge can't render, and comes first.
export function bridgeLine(item, problem = '') {
  if (problem) return {text: problem, problem: true};
  if (!item) return {text: "Waiting for the Timeline's status.", problem: false};
  if (item.status === 'problem') return {text: sentence(item.note), problem: true};
  if (item.status === 'done') return {text: `Rendered, ${item.video.frames} frames.`, problem: false};
  if (item.status === 'waiting') return {text: sentence(item.note), problem: false};
  if (item.note) return {text: `Needs a render: ${item.note}.`, problem: false};
  return {text: 'Plays as a cut until it renders.', problem: false};
}

export class BridgePanel {
  // editor: the Timeline editor, whose queueBridge() renders the selected box's bridge.
  constructor(editor) {
    injectStyle();
    this.editor = editor;
    this.insertButton = button('Insert bridge', '', () => {
      model.insertBridge(editor.state, editor.selected);
      editor.commit();
    });
    this.field = el('div', 'h3ct-field');
    this.field.append(el('span', 'h3ct-label', 'Bridge'), this.insertButton);
    this.hint = el('p', 'h3ct-hint');
    this.titleEl = el('span', 'h3cb-title');
    this.renderButton = button('Render bridge', RENDER, () => editor.queueBridge(), 'h3ct-primary');
    this.playButton = button('Play', '', () => this.root.dispatchEvent(new CustomEvent('h3c-play-bridge',
      {bubbles: true, detail: {box: editor.box().id}})));
    this.removeButton = button('Remove bridge', 'Take the bridge out, so the join plays as a cut', () => {
      model.removeBridge(editor.state, editor.selected);
      editor.commit();
    });
    const head = el('div', 'h3cb-head');
    head.append(this.titleEl, this.renderButton, this.playButton, this.removeButton);
    this.lengthSelect = el('select', 'h3ct-select');
    this.lengthSelect.setAttribute('aria-label', 'Bridge length');
    for (const frames of model.BRIDGE_FRAMES) {
      const choice = el('option', null, `${frames} frames · ${model.seconds(frames)} s`);
      choice.value = String(frames);
      this.lengthSelect.append(choice);
    }
    this.lengthSelect.addEventListener('change', () => this.edit((bridge) => { bridge.frames = Number(this.lengthSelect.value); }));
    this.seedInput = el('input', 'h3ct-number');
    this.seedInput.type = 'number';
    this.seedInput.min = '0';
    this.seedInput.step = '1';
    this.seedInput.placeholder = 'auto';
    this.seedInput.setAttribute('aria-label', 'Bridge seed');
    this.seedInput.addEventListener('change', () => this.edit((bridge) => {
      const seed = Number(this.seedInput.value);
      if (this.seedInput.value !== '' && Number.isSafeInteger(seed) && seed >= 0) bridge.seed = seed;
      else delete bridge.seed;
    }));
    const roll = button('🎲', 'Choose a new seed for the next render', () => this.edit((bridge) => { bridge.seed = model.newSeed(); }));
    const row = el('div', 'h3cb-row');
    row.append(field('Length', this.lengthSelect), field('Seed', this.seedInput, roll));
    this.promptEl = el('textarea', 'h3ct-text');
    this.promptEl.rows = 3;
    this.promptEl.setAttribute('aria-label', 'Bridge prompt');
    this.promptEl.placeholder = 'How the shot moves from the box before into this one';
    this.promptEl.title = 'Sent after the shared prompt, with no pictures or sounds: a mention reads as the described subject or sound';
    this.promptEl.addEventListener('input', () => this.edit((bridge) => { bridge.prompt = this.promptEl.value; }, false));
    const prompt = el('div', 'h3cb-prompt');
    prompt.append(el('span', 'h3ct-label', 'Bridge prompt'), this.promptEl);
    this.stateEl = el('div', 'h3cb-state');
    this.stateEl.setAttribute('role', 'status');
    this.panel = el('div', 'h3cb-root');
    this.panel.setAttribute('aria-label', 'Bridge');
    this.panel.append(head, row, prompt, this.stateEl);
    this.root = el('div', 'h3cb-wrap');
    this.root.append(this.hint, this.panel);
  }

  edit(change, renderPanel = true) {
    const bridge = model.bridgeOf(this.editor.state, this.editor.selected);
    if (!bridge) return;
    change(bridge);
    this.editor.commit(renderPanel);
  }

  // Why Insert bridge is off, or '' when it is on: both boxes rendered, and the one before plays all it generates.
  insertBlocked() {
    const editor = this.editor;
    if (editor.stale || !editor.status?.ok) return WAIT;
    const index = editor.selected;
    const problem = model.bridgeProblem(editor.state, index);
    if (problem) return problem;
    const waiting = [index, index + 1].filter((n) => editor.statusOf(editor.state.boxes[n - 1])?.status !== 'done');
    return waiting.length ? `Render ${waiting.map((n) => `box ${n}`).join(' and ')} first.` : '';
  }

  render() {
    const editor = this.editor;
    const index = editor.selected;
    const box = editor.box();
    const fresh = index > 0 && !!box?.cut;
    const bridge = fresh ? model.bridgeOf(editor.state, index) : undefined;
    this.field.hidden = !fresh || !!bridge;
    this.panel.hidden = !bridge;
    const blocked = fresh && !bridge ? this.insertBlocked() : '';
    this.insertButton.disabled = !!blocked;
    this.insertButton.title = blocked || `Add new frames that move from box ${index}'s end into this box's start. `
      + 'Both boxes keep their renders, and the full video gets longer';
    this.hint.textContent = blocked;
    this.hint.hidden = !blocked;
    if (!bridge) return;
    const item = editor.stale ? undefined : editor.bridgeStatusOf(box.id);
    const problem = model.bridgeProblem(editor.state, index);
    const line = bridgeLine(item, problem);
    this.titleEl.textContent = `Bridge before box ${index + 1}`;
    this.lengthSelect.value = String(bridge.frames);
    this.seedInput.value = bridge.seed ?? '';
    if (this.promptEl.value !== (bridge.prompt ?? '')) this.promptEl.value = bridge.prompt ?? '';
    this.stateEl.textContent = line.text;
    this.stateEl.classList.toggle('problem', line.problem);
    this.panel.classList.toggle('problem', line.problem);
    const waits = item?.status === 'problem' || item?.status === 'waiting';
    const why = editor.queuing ? 'Wait until the run is queued.' : problem || (item ? (waits ? line.text : '') : WAIT);
    this.renderButton.disabled = !!why;
    this.renderButton.title = why || RENDER;
    const take = editor.bridgeStatusOf(box.id)?.video;
    this.playButton.disabled = !take;
    this.playButton.title = take ? 'Play the bridge’s take in the player' : 'The bridge has no take yet';
  }
}
