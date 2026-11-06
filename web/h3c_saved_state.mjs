// Save Timeline and Story together so a restart cannot restore prompts without their matching recovery state.
const sessions = new Map();
const restorers = new WeakMap();
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export const AUTOSAVE_SETTING = 'H3Continuity.Autosave';
export const autosaveEnabled = app => app.ui?.settings?.getSettingValue?.(AUTOSAVE_SETTING) !== false;

export class SavedState {
  constructor({ read, apply, request, status, identity, enabled = () => true, session = {} }) {
    Object.assign(this, { read, apply, request, status, identity, enabled, session });
  }

  get conflict() { return this.session.conflict; }
  set conflict(value) { this.session.conflict = value; }

  async sync(force = false) {
    if (!force && !this.enabled()) {this.status('Autosave off — save a checkpoint to keep your edits.'); return;}
    const session=this.session;
    if (this.gone||session.suspended) return;
    while (session.pending) await session.pending;
    if (this.gone||this.session!==session||session.suspended) return;
    if (!force && !this.enabled()) return;
    const pending = this.exchange(force);
    session.pending = pending;
    try { await pending; } finally {
      if (session.pending === pending) session.pending = null;
    }
  }

  async suspend() {
    const session=this.session;
    session.suspended=(session.suspended??0)+1;
    const resume=()=>{session.suspended--;};
    try {while(session.pending)await session.pending;}catch(error){resume();throw error;}
    return resume;
  }

  async exchange(force = false) {
    const local = this.read();
    const session = this.session;
    const identity=this.identity?.();
    const active=()=>!this.gone&&this.session===session&&!session.suspended&&this.identity?.()===identity&&(force||this.enabled());
    try {
      if (this.conflict) return this.disagree(this.conflict);
      if (session.revision === undefined) {
        this.status('Loading saved state…');
        const saved = await this.request();
        if (!active()) return;
        const now = this.read();
        if (!equal(local, now)) {
          // A workflow that finishes loading changes the widgets too, so only a saved state matching neither reading
          // disagrees.
          session.base = saved.value && equal(saved.value, now) ? now : local;
          session.revision = saved.revision;
          if (saved.value && !equal(saved.value, local) && !equal(saved.value, now)) return this.disagree(saved);
        } else {
          session.revision = saved.revision;
          if (saved.value && this.enabled()) this.apply(saved.value);
          session.base = saved.value && this.enabled() ? this.read() : saved.value;
        }
      }
      const value = this.read();
      if (!equal(value, session.base)) {
        this.status('Saving…');
        const saved = await this.request({ revision: session.revision, value });
        if (!active()) return;
        if (saved.conflict) {
          if (equal(saved.value, value)) {
            session.revision = saved.revision;
            session.base = value;
          } else return this.disagree(saved);
        } else {
          session.revision = saved.revision;
          session.base = value;
        }
      } else {
        const saved = await this.request(undefined, session.revision);
        if (!active()) return;
        if (saved.revision !== session.revision) {
          if (!equal(value, this.read())) return this.disagree(saved);
          if (saved.value) this.apply(saved.value);
          session.revision = saved.revision;
          session.base = this.read();
        }
      }
      if (active()) this.status(equal(this.read(), session.base) ? 'Saved on this ComfyUI server' : 'Changes pending…');
    } catch (error) {
      if(!active())return;
      this.status(`Not saved: ${error.message}`);
      throw error;
    }
  }

  disagree(saved) {
    this.conflict = saved;
    this.status('Changed in another browser. Choose which edits to keep.', true);
  }

  async resolve(useSaved) {
    const saved = this.conflict;
    if (!saved) return;
    this.session.revision = saved.revision;
    this.session.base = saved.value;
    if (useSaved) { this.apply(saved.value); this.session.base = this.read(); }
    this.conflict = null;
    await this.sync(true);
  }

  async flush() {
    await this.sync(true);
    if (this.conflict) throw new Error('Resolve the saved-state conflict before writing a Story.');
    if (!equal(this.read(), this.session.base)) await this.sync(true);
    if (this.conflict || !equal(this.read(), this.session.base)) throw new Error('H3 edits are not saved yet. Try again.');
  }
}

export function mountSavedState(node, root, { app, api, loaded }) {
  restorers.set(node, loaded);
  const bar = document.createElement('div');
  bar.style.cssText = 'font-size:11px;padding:4px 0;display:flex;gap:6px;align-items:center;flex-wrap:wrap';
  const label = document.createElement('span');
  const choices = document.createElement('span');
  bar.append(label, choices);
  root.append(bar);
  let sync;
  for (const [title, useSaved] of [['Load saved edits', true], ['Keep my edits', false]]) {
    const button = document.createElement('button');
    button.textContent = title;
    button.onclick = () => sync.resolve(useSaved).catch(() => {});
    choices.append(button);
  }
  choices.hidden = true;
  const nodes = () => (node.graph?._nodes ?? [])
    .filter(n => ['H3C_Timeline', 'H3C_Story'].includes(n.type) && n.properties?.h3c_project?.mode !== 'attached')
    .sort((a, b) => String(a.id).localeCompare(String(b.id)));
  const keyOf = (n, w) => `${n.id}/${n.type}/${w.name}`;
  const read = () => Object.fromEntries(nodes().flatMap(n => (n.widgets ?? [])
    .filter(w => w.name && w.serialize !== false && w.options?.serialize !== false
      && ['string', 'number', 'boolean'].includes(typeof w.value))
    .map(w => [keyOf(n, w), w.value])));
  sync = new SavedState({
    read,
    enabled: () => autosaveEnabled(app),
    identity: () => String(node.graph?.extra?.h3c_story_id ?? node.graph?.id ?? ''),
    apply(value) {
      for (const n of nodes()) {
        for (const widget of n.widgets ?? []) {
          const key = keyOf(n, widget);
          if (Object.hasOwn(value, key)) widget.value = value[key];
        }
      }
      for (const n of nodes()) restorers.get(n)?.();
      node.setDirtyCanvas?.(true, true);
      app.extensionManager?.workflow?.activeWorkflow?.changeTracker?.checkState?.();
    },
    status(message, conflict = false) { label.textContent = message; choices.hidden = !conflict; },
    // With a known `revision`, an unchanged state answers with the revision alone.
    async request(body, revision) {
      const identity = { kind: 'workflow', graph: String(node.graph?.extra?.h3c_story_id ?? node.graph?.id ?? ''), node: 'workflow' };
      if (!identity.graph || Number(node.id) < 0) throw new Error('Waiting for the workflow to load.');
      const query = new URLSearchParams(revision === undefined ? identity : { ...identity, revision });
      const response = await api.fetchApi(body ? '/h3c/state' : `/h3c/state?${query}`,
        body ? { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...identity, ...body }) } : undefined);
      const record = await response.json();
      if (!response.ok && response.status !== 409) throw new Error(record.error ?? 'ComfyUI is unavailable.');
      return record;
    },
  });
  const tick = () => {
    if (node.properties?.h3c_project?.mode === 'attached') return Promise.resolve();
    if (!node.graph?.id || node.graph !== (app.rootGraph ?? app.graph)) return Promise.resolve();
    const key = String(node.graph.extra?.h3c_story_id ?? node.graph.id);
    if (!sessions.has(key)) sessions.set(key, {});
    sync.session = sessions.get(key);
    return sync.sync().finally(() => { sync.session.synced = Date.now(); });
  };
  // Polling also catches widget edits, Undo and programmatic changes without patching ComfyUI's workflow manager.
  // Every H3 node of a graph shares one session, so one of them polling each second is enough.
  const timer = setInterval(() => {
    if (!document.hidden && Date.now() - (sync.session.synced ?? 0) >= 900) tick().catch(() => {});
  }, 1000);
  const ready = new Promise(resolve => setTimeout(resolve, 0)).then(tick).catch(() => {});
  const wake = () => tick().catch(() => {});
  window.addEventListener('focus', wake);
  document.addEventListener('visibilitychange', wake);
  let editTimer;
  return {
    bar,
    ready,
    get revision() { return sync.session.revision; },
    async suspend() {
      const key=String(node.graph?.extra?.h3c_story_id??node.graph?.id??'');
      if(!sessions.has(key))sessions.set(key,{});
      sync.session=sessions.get(key);
      return sync.suspend();
    },
    async flush() { await ready; await tick(); await sync.flush(); },
    changed() {
      if (!sync.conflict) sync.status('Changes pending…');
      clearTimeout(editTimer);
      editTimer = setTimeout(wake, 250);
    },
    destroy() {
      sync.gone = true; restorers.delete(node); clearInterval(timer); clearTimeout(editTimer);
      window.removeEventListener('focus', wake); document.removeEventListener('visibilitychange', wake); bar.remove();
    },
  };
}
