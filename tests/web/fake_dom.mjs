// Just enough of the DOM for the Studio's plain-DOM panels to build, render and handle clicks under node --test.
class FakeElement {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.childNodes = [];
    this.parentNode = null;
    this.attributes = new Map();
    this.listeners = new Map();
    this.style = {};
    this.dataset = {};
    Object.assign(this, {hidden: false, disabled: false, checked: false, open: false, value: '', title: '', className: '',
      id: '', text: ''});
  }

  get children() { return this.childNodes.filter((node) => node.tagName !== '#TEXT'); }
  get firstElementChild() { return this.children[0] ?? null; }
  get options() { return this.children.filter((node) => node.tagName === 'OPTION'); }

  get classList() {
    const node = this, names = () => node.className.split(/\s+/).filter(Boolean);
    const list = {
      contains: (name) => names().includes(name),
      add: (...added) => { node.className = [...new Set([...names(), ...added])].join(' '); },
      remove: (...removed) => { node.className = names().filter((name) => !removed.includes(name)).join(' '); },
      toggle: (name, force = !names().includes(name)) => { (force ? list.add : list.remove)(name); return force; },
    };
    return list;
  }

  append(...nodes) {
    for (const node of nodes) {
      if (node == null) continue;
      const child = typeof node === 'string' ? Object.assign(new FakeElement('#text'), {text: node}) : node;
      child.parentNode?.removeChild(child);
      child.parentNode = this;
      this.childNodes.push(child);
    }
  }

  prepend(...nodes) {
    const rest = this.childNodes;
    this.childNodes = [];
    this.append(...nodes);
    this.childNodes.push(...rest);
  }

  removeChild(child) {
    this.childNodes = this.childNodes.filter((node) => node !== child);
    child.parentNode = null;
  }

  remove() { this.parentNode?.removeChild(this); }

  replaceChildren(...nodes) {
    for (const node of [...this.childNodes]) this.removeChild(node);
    this.append(...nodes);
  }

  get textContent() { return this.text + this.childNodes.map((node) => node.textContent).join(''); }
  set textContent(value) {
    for (const node of [...this.childNodes]) this.removeChild(node);
    this.text = value == null ? '' : String(value);
  }

  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }

  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(listener);
  }

  removeEventListener(type, listener) {
    this.listeners.set(type, (this.listeners.get(type) ?? []).filter((item) => item !== listener));
  }

  dispatchEvent(event) {
    for (let node = this; node; node = event.bubbles ? node.parentNode : null) {
      for (const listener of [...(node.listeners.get(event.type) ?? [])]) listener(event);
    }
    return true;
  }

  contains(other) {
    for (let node = other; node; node = node.parentNode) if (node === this) return true;
    return false;
  }

  click() {
    if (!this.disabled) this.dispatchEvent({type: 'click', bubbles: true, button: 0, preventDefault() {}, stopPropagation() {}});
  }

  // The event a user's edit of a field sends.
  fire(type) {
    this.dispatchEvent({type, bubbles: true, preventDefault() {}});
  }
}

export function installDom() {
  const head = new FakeElement('head');
  const find = (node, id) => node.id === id ? node : node.children.map((child) => find(child, id)).find(Boolean) ?? null;
  globalThis.document = {head, activeElement: null, createElement: (tag) => new FakeElement(tag),
    getElementById: (id) => find(head, id)};
}

// Every element under `root` that `test` accepts, in document order.
export function findAll(root, test) {
  return [...(test(root) ? [root] : []), ...root.children.flatMap((child) => findAll(child, test))];
}

export function buttonNamed(root, label) {
  const found = findAll(root, (node) => node.tagName === 'BUTTON' && node.textContent === label);
  if (!found.length) throw new Error(`no ${label} button`);
  return found[0];
}
