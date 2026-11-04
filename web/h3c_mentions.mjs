// Mention highlights for the H3 Timeline's text boxes: a layer behind a textarea repeats its text with each @image
// and @audio mention marked, and a card shows which reference the mention under the pointer is. Plain DOM without
// ComfyUI imports.
import { mentionParts } from './h3c_timeline_model.mjs?v=20261104-flf-audio-1';

const STYLE_ID = 'h3cm-style';
const SHOW_DELAY_MS = 150;
const GAP = 6;
// What decides where the textarea's lines wrap. The layer fills the same box, and with the overflow settings copied
// as well it grows the same scrollbar, so its lines wrap at the same width.
const COPIED = ['overflowX', 'overflowY', 'scrollbarWidth', 'scrollbarGutter', 'fontFamily', 'fontSize', 'fontStyle',
  'fontVariant', 'fontWeight', 'fontStretch', 'lineHeight', 'letterSpacing', 'wordSpacing', 'textIndent',
  'textTransform', 'textAlign', 'tabSize', 'whiteSpace', 'wordBreak', 'overflowWrap', 'direction', 'paddingTop',
  'paddingRight', 'paddingBottom', 'paddingLeft', 'borderTopWidth', 'borderRightWidth', 'borderBottomWidth',
  'borderLeftWidth', 'borderTopLeftRadius', 'borderTopRightRadius', 'borderBottomRightRadius',
  'borderBottomLeftRadius'];
const CSS = `
.h3cm-wrap { position: relative; }
.h3cm-wrap > textarea { position: relative; display: block; margin: 0; }
.h3cm-layer { position: absolute; inset: 0; margin: 0; border-style: solid; border-color: transparent;
  color: transparent; white-space: pre-wrap; overflow-wrap: break-word; pointer-events: none; user-select: none; }
.h3cm-mark { border-radius: 3px; background: rgba(91, 143, 232, .35); }
.h3cm-mark.missing { background: rgba(224, 96, 90, .35); }
.h3cm-card { position: fixed; z-index: 10000; display: flex; flex-direction: column; gap: 3px; max-width: 280px;
  padding: 6px 8px; font: 13px/1.45 system-ui, sans-serif; color: #ddd; background: #1d2029;
  border: 1px solid #3a414d; border-radius: 6px; box-shadow: 0 4px 14px rgba(0, 0, 0, .45); pointer-events: none; }
.h3cm-card.problem { border-color: #e0605a; }
.h3cm-card img { display: block; max-width: 160px; max-height: 120px; object-fit: contain; border-radius: 3px; }
.h3cm-card [hidden] { display: none; }
.h3cm-title { font-weight: 600; overflow-wrap: anywhere; }
.h3cm-detail { color: #aab1bd; overflow-wrap: anywhere; }
`;

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = el('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.append(style);
}

function inside(rect, x, y) {
  return x >= rect.left && x < rect.right && y >= rect.top && y < rect.bottom;
}

export class MentionLayer {
  // area: a textarea that fills the width it's given, as the editor's do. hooks: live() -> Set of the names whose
  // reference delivers a value, onHover(part, rect) when the pointer comes onto a mention, onLeave() when it leaves it.
  constructor(area, { live, onHover, onLeave }) {
    injectStyle();
    this.area = area;
    this.live = live;
    this.onHover = onHover;
    this.onLeave = onLeave;
    this.marks = [];
    this.hovered = null;
    this.painted = false;
    this.layer = el('div', 'h3cm-layer');
    this.layer.setAttribute('aria-hidden', 'true');
    this.root = el('div', 'h3cm-wrap');
    this.root.append(this.layer, area);
    area.addEventListener('input', () => this.render());
    area.addEventListener('scroll', () => {
      this.leave();
      this.follow();
    });
    area.addEventListener('pointermove', (event) => this.hover(event.clientX, event.clientY));
    area.addEventListener('pointerleave', () => this.leave());
    area.addEventListener('blur', () => this.leave());
    if (typeof ResizeObserver === 'function') {
      this.observer = new ResizeObserver(() => this.follow());
      this.observer.observe(area);
    }
  }

  destroy() {
    this.observer?.disconnect();
    this.leave();
  }

  render() {
    this.leave();
    const live = this.live();
    this.marks = [];
    this.layer.textContent = '';
    for (const part of mentionParts(this.area.value)) {
      if (!part.name) {
        this.layer.append(part.text);
        continue;
      }
      const mark = el('span', live.has(part.name) ? 'h3cm-mark' : 'h3cm-mark missing');
      mark.textContent = part.text;
      this.layer.append(mark);
      this.marks.push({ part, mark });
    }
    // a textarea shows a line after a final newline; a div only when that line holds something
    if (this.area.value.endsWith('\n')) this.layer.append(' ');
    this.follow();
  }

  follow() {
    const area = this.area;
    if (!area.isConnected) return;
    const style = getComputedStyle(area);
    if (!this.painted) {
      this.painted = true;
      this.layer.style.backgroundColor = style.backgroundColor;
      area.style.backgroundColor = 'transparent';
    }
    for (const name of COPIED) this.layer.style[name] = style[name];
    this.layer.scrollTop = area.scrollTop;
    this.layer.scrollLeft = area.scrollLeft;
  }

  hover(x, y) {
    const found = this.marks.find(({ mark }) => [...mark.getClientRects()].some((rect) => inside(rect, x, y))) ?? null;
    if (found === this.hovered) return;
    this.leave();
    if (!found) return;
    this.hovered = found;
    this.onHover(found.part, found.mark.getBoundingClientRect());
  }

  leave() {
    if (!this.hovered) return;
    this.hovered = null;
    this.onLeave();
  }
}

export class MentionCard {
  constructor() {
    injectStyle();
    this.timer = null;
    this.rect = null;
    this.failed = false;
    this.root = el('div', 'h3cm-card');
    this.image = el('img');
    this.image.alt = '';
    this.image.addEventListener('load', () => this.place());
    this.image.addEventListener('error', () => {
      this.failed = true;
      this.image.hidden = true;
      this.place();
    });
    this.titleEl = el('div', 'h3cm-title');
    this.detailEl = el('div', 'h3cm-detail');
    this.root.append(this.image, this.titleEl, this.detailEl);
  }

  // info: {problem, title, detail, preview} from describeMention; rect: where the mention is on the screen.
  show(info, rect) {
    this.hide();
    this.timer = setTimeout(() => {
      this.timer = null;
      this.fill(info);
      this.rect = rect;
      document.body.append(this.root);
      this.place();
    }, SHOW_DELAY_MS);
  }

  fill(info) {
    this.root.classList.toggle('problem', info.problem);
    this.titleEl.textContent = info.title;
    this.detailEl.textContent = info.detail ?? '';
    this.detailEl.hidden = !info.detail;
    const preview = info.preview ?? '';
    if (preview && this.image.getAttribute('src') !== preview) {
      this.failed = false;
      this.image.src = preview;
    }
    this.image.hidden = !preview || this.failed;
  }

  place() {
    if (!this.root.isConnected || !this.rect) return;
    const card = this.root.getBoundingClientRect();
    let top = this.rect.bottom + GAP;
    if (top + card.height > window.innerHeight - GAP) top = Math.max(GAP, this.rect.top - card.height - GAP);
    const left = Math.max(GAP, Math.min(this.rect.left, window.innerWidth - card.width - GAP));
    this.root.style.left = `${left}px`;
    this.root.style.top = `${top}px`;
  }

  hide() {
    clearTimeout(this.timer);
    this.timer = null;
    this.root.remove();
  }
}
