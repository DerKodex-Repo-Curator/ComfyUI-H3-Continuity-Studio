import * as model from './h3c_timeline_model.mjs?v=20261103-replacement-bridges-1';
import { importWhisper, validateTimedText, setTextSync, textClock, projectTimedText } from './h3c_timed_text.mjs?v=20261011-reference-preparation-1';

const node = (tag, cls, text) => {
  const item = document.createElement(tag);
  if (cls) item.className = cls;
  if (text != null) item.textContent = text;
  return item;
};
const button = (text, action) => {
  const item = node('button', 'h3ct-button', text);
  item.type = 'button'; item.addEventListener('click', action);
  return item;
};
// A lane clip takes one of the node's wired audio slots; the Timeline refuses any other, such as a voice clip's.
const LANE_SLOTS = Array.from({length: model.MAX_REF_AUDIOS}, (_, i) => `audio${i + 1}`);

export class AudioLanes {
  constructor(editor) {
    this.editor = editor;
    this.root = node('div', 'h3ct-audio');
    this.header = node('div', 'h3ct-row h3ct-audio-lane');
    this.header.style.height = 'auto'; this.header.style.minHeight = '40px';
    this.header.setAttribute('aria-label', 'Audio lane');
    this.upload = node('input');
    this.upload.type = 'file'; this.upload.accept = 'audio/*,.wav,.mp3,.flac,.ogg,.m4a,.aac,.opus,.aiff'; this.upload.hidden = true;
    this.upload.addEventListener('change', () => {
      const file = this.upload.files?.[0]; this.upload.value = '';
      if (file) this.addFile(file);
    });
    this.addButton = button('+ Audio', () => this.upload.click());
    this.addButton.title = 'Upload an audio file, or choose a connected source beside this button';
    this.connectedSelect = node('select', 'h3ct-select');
    this.connectedSelect.setAttribute('aria-label', 'Add connected audio to a lane');
    this.connectedSelect.addEventListener('change', () => {
      const ref = editor.host.connected().audios.find(ref => ref.name === this.connectedSelect.value);
      if (ref) this.addConnected(ref);
    });
    this.message = node('span', 'h3ct-hint');
    this.textUpload = node('input'); this.textUpload.type = 'file'; this.textUpload.accept = '.json,application/json'; this.textUpload.hidden = true;
    this.textUpload.addEventListener('change', () => {
      const file = this.textUpload.files?.[0]; this.textUpload.value = '';
      if (file) this.importText(file);
    });
    this.textButton = button('+ Text', () => this.textUpload.click());
    this.textButton.title = 'Import timed text from Whisper JSON';
    this.textMessage = node('span', 'h3ct-hint'); this.textMessage.setAttribute('role', 'status');
    this.header.append(node('span', 'h3ct-label', 'Audio'), this.addButton, this.connectedSelect, this.upload, this.message);
    this.textHeader = node('div', 'h3ct-row');
    this.textSelect = button('Timed text', () => this.selectText());
    this.textSelect.setAttribute('aria-label', 'Edit timed text');
    this.textHeader.append(node('span', 'h3ct-label', 'Text'), this.textSelect, this.textButton, this.textUpload, this.textMessage);
    this.lanes = node('div', 'h3ct-audio-lanes');
    this.textLane = node('div', 'h3ct-audio-lane h3ct-text-lane');
    this.textLane.style.height = 'auto'; this.textLane.style.minHeight = '40px';
    this.textLane.setAttribute('aria-label', 'Text lane');
    this.textLane.append(this.textHeader);
    this.settings = node('details', 'h3ct-audio-settings');
    this.textSettings = node('details', 'h3ct-audio-settings');
    this.textSummary = node('pre', 'h3ct-hint'); this.textSummary.style.whiteSpace = 'pre-wrap';
    this.root.append(this.lanes, this.header, this.textLane, this.textSettings);
    this.root.addEventListener('dragover', event => {
      if (event.dataTransfer?.types.includes('Files')) { event.preventDefault(); event.stopPropagation(); }
    });
    this.root.addEventListener('drop', event => {
      const file = event.dataTransfer?.files?.[0];
      if (file) {
        event.preventDefault(); event.stopPropagation();
        if (this.textLane.contains(event.target) && /\.json$/i.test(file.name)) this.importText(file);
        else this.addFile(file);
      }
    });
  }

  get clips() { return this.editor.state.audio_clips ?? []; }

  selectAudio(slot) {
    if (!this.clips.some(clip => clip.slot === slot)) return;
    this.selected = slot; this.settings.open = true;
    this.renderSettings();
    this.editor.inspect({kind: 'audio', slot});
  }

  selectText() {
    if (!this.editor.state.timed_text) return;
    this.textSettings.open = true;
    this.editor.inspect({kind: 'text'});
  }

  async importText(file) {
    this.textButton.disabled = true; this.textMessage.textContent = 'Reading text…';
    try {
      const bytes = await file.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
      const value = importWhisper(JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes)), file.name, hash);
      await this.editor.host.uploadWhisper?.(file, hash);
      this.editor.state.timed_text = value;
      this.textSettings.open = true; this.textMessage.textContent = '';
      this.editor.commit();
      this.selectText();
    } catch (error) { this.textMessage.textContent = error.message; }
    finally { this.textButton.disabled = false; }
  }

  renderText() {
    const state = this.editor.state, value = state.timed_text;
    this.textSettings.hidden = !value;
    this.textSelect.hidden = !value;
    const signature = JSON.stringify([value, this.clips]);
    const sameState = this.textState === state && this.textValue === value;
    const typing = sameState && this.textSettings.contains(document.activeElement) && document.activeElement.tagName === 'TEXTAREA';
    if ((!sameState || this.textKey !== signature) && !typing) {
      this.textKey = signature; this.textState = state; this.textValue = value;
      this.textSettings.replaceChildren(node('summary', null, 'Timed text · Whisper JSON'), button('Remove text', () => {
        delete state.timed_text; this.textMessage.textContent = ''; this.editor.commit(); this.editor.inspectClip();
      }));
      if (value) {
        this.textSettings.append(node('div', 'h3ct-hint', `${value.source_name ?? 'Text'} · SHA-256 ${value.source_sha256 ?? 'missing'}`));
        try {
          validateTimedText(value);
          const row = node('div', 'h3ct-row');
          for (const [key, label] of [['enabled', 'Enable timed text'], ['sync_audio', 'Sync text to audio']]) {
            const field = node('label', 'h3ct-field', label), input = node('input'); input.type = 'checkbox'; input.checked = value[key];
            input.setAttribute('aria-label', label);
            input.addEventListener('change', () => {
              if (key === 'sync_audio') setTextSync(state, input.checked); else value.enabled = input.checked;
              this.editor.commit();
            });
            field.append(input); row.append(field);
          }
          const lane = node('select', 'h3ct-select'); lane.setAttribute('aria-label', 'Text audio lane');
          for (const slot of ['audio1','audio2','audio3']) {
            const clip = this.clips.find(clip => clip.slot === slot);
            const option = node('option', null, `@${slot}${clip ? ` · ${clip.title ?? 'Audio'}` : ' (missing lane)'}`); option.value = slot; lane.append(option);
          }
          lane.value = value.audio_slot;
          lane.addEventListener('change', () => { setTextSync(state, value.sync_audio, lane.value); this.editor.commit(); });
          row.append(lane); this.textSettings.append(row);
          const timing = node('div', 'h3ct-row'), clock = textClock(value, this.clips);
          for (const [key, label] of [['start','Text video start (s)'],['source_start','Text source in (s)'],['duration','Text length (s)']]) {
            const field = node('label', 'h3ct-field', label), input = node('input', 'h3ct-number');
            input.type = 'number'; input.min = key === 'duration' ? .001 : 0; input.step = 'any'; input.required = true;
            input.value = clock[key]; input.disabled = value.sync_audio; input.setAttribute('aria-label', label);
            input.addEventListener('change', () => {
              const number = Number(input.value);
              if (!input.value || !Number.isFinite(number) || number < 0 || (key === 'duration' && number === 0)) { input.value = value[key]; return; }
              value[key] = number; this.editor.commit();
            });
            field.append(input); timing.append(field);
          }
          const direction = node('textarea', 'h3ct-text'); direction.rows = 2; direction.value = value.direction;
          direction.setAttribute('aria-label', 'Text direction'); direction.placeholder = 'Describe how these exact words appear: placement, typography, motion…';
          direction.addEventListener('input', () => { value.direction = direction.value; this.editor.commit(false); });
          direction.addEventListener('change', () => { value.direction = direction.value; this.editor.commit(false); });
          const treatment = node('label', 'h3ct-field', 'Text visual direction'); treatment.append(direction);
          this.textSettings.append(timing, treatment);
        } catch { /* The removable attachment's precise error is displayed below. */ }
      }
      this.textSettings.append(this.textSummary);
    }
    if (!value) { this.textSummary.textContent = ''; return; }
    try {
      validateTimedText(value);
      const clock = textClock(value, this.clips);
      if (!clock.resolved) { this.textSummary.textContent = `@${value.audio_slot} lane is missing. Select a lane or turn sync off.`; return; }
      if (!value.enabled) { this.textSummary.textContent = 'Timed text is disabled.'; return; }
      const index = this.editor.selected, box = state.boxes[index];
      const start = state.boxes.slice(0, index).reduce((sum, box) => sum + box.frames, 0) / model.FPS;
      const window = projectTimedText(value, this.clips, start, box?.frames ?? model.totalFrames(state),
        box && !model.isFresh(state, index) ? this.editor.host.context() : 0);
      this.textSummary.textContent = `Movie ${clock.start} s · source ${clock.source_start}–${clock.source_start + clock.duration} s`
        + `\nClip ${index + 1} source ${window.source_start ?? '—'}–${window.source_end ?? '—'} s · replay ${window.replay_end_ms} ms`
        + `${window.direction ? `\nDirection: ${window.direction}` : ''}`
        + (window.cues.length ? window.cues.map(cue => `\n${cue.start_ms}–${cue.end_ms} ms${cue.continuing ? ' · continuing' : ''}${cue.replay_only ? ' · replay only' : ''}\n${cue.text}`).join('') : '\nNo active phrases in this clip.');
    } catch (error) { this.textSummary.textContent = error.message; }
  }

  async addFile(file) {
    if (this.busy) return;
    const occupied = new Set([...this.editor.referenceOptions().map(ref => ref.name), ...this.clips.map(clip => clip.slot)]);
    const slot = LANE_SLOTS.find(slot => !occupied.has(slot));
    if (!slot) { this.message.textContent = 'All three audio slots are in use. Remove a clip or disconnect a reference.'; return; }
    await this.add(slot, () => this.editor.host.uploadAudio(file), true);
  }

  async addConnected(ref) {
    if (this.busy) return;
    if (!ref.mediaFile) { this.message.textContent = 'For a draggable lane, use Load Audio or upload the source file here.'; return; }
    await this.add(ref.name, async () => ({title: ref.title || ref.file,
      ...await this.editor.host.audioInfo(ref.mediaFile)}), false);
  }

  async add(slot, read, uploaded) {
    this.busy = true; this.addButton.disabled = true; this.message.textContent = 'Reading audio…';
    try {
      const source = await read();
      if (!Number.isFinite(source.duration) || source.duration <= 0) throw new Error('This file has no playable audio.');
      if (this.clips.some(clip => clip.slot === slot)) throw new Error(`${slot} is already in use.`);
      const video = model.totalFrames(this.editor.state) / model.FPS;
      this.editor.state.audio_clips ??= [];
      this.clips.push({slot, ...(uploaded ? {file: source.file} : {}), title: source.title,
        start: 0, source_start: 0, duration: video ? Math.min(video, source.duration) : source.duration,
        source_duration: source.duration, peaks: source.peaks, layer: 'music', description: ''});
      this.editor.state.disabled_refs = (this.editor.state.disabled_refs ?? []).filter(name => name !== slot);
      this.selected = slot; this.settings.open = true; this.message.textContent = '';
      this.editor.commit();
      this.selectAudio(slot);
    } catch (error) { this.message.textContent = error.message; }
    finally { this.busy = false; this.addButton.disabled = false; }
  }

  render(span) {
    this.span = span;
    this.renderLanes();
    const connected = this.editor.host.connected().audios.filter(ref => !ref.refmod && LANE_SLOTS.includes(ref.name)
      && !this.clips.some(clip => clip.slot === ref.name));
    this.connectedSelect.replaceChildren(node('option', null, 'Add connected audio…'));
    this.connectedSelect.firstChild.value = '';
    for (const ref of connected) {
      const option = node('option', null, `@${ref.name} · ${ref.title || ref.name}`);
      option.value = ref.name; this.connectedSelect.append(option);
    }
    this.connectedSelect.hidden = !connected.length;
    this.renderSettings();
  }

  renderLanes() {
    this.renderText();
    if (this.header.parentNode === this.lanes) this.lanes.after(this.header);
    this.lanes.replaceChildren();
    if (!this.clips.length) {
      this.lanes.append(this.header);
    }
    for (const clip of this.clips) {
      const reference = this.editor.host.connected().audios.find(ref => ref.name === clip.slot);
      const title = reference?.replaced ? reference.title || 'Replacement unavailable' : clip.title || 'Audio';
      const lane = node('div', 'h3ct-audio-lane');
      lane.setAttribute('aria-label', `Audio lane @${clip.slot}`);
      const video = node('div', 'h3ct-audio-video');
      video.style.width = `${100 * model.totalFrames(this.editor.state) / this.span}%`;
      lane.append(video);
      const item = node('div', 'h3ct-audio-clip');
      item.style.left = `${100 * clip.start * model.FPS / this.span}%`;
      item.style.width = `${100 * clip.duration * model.FPS / this.span}%`;
      item.classList.toggle('disabled', !model.referenceEnabled(this.editor.state, clip.slot));
      item.tabIndex = 0; item.setAttribute('role', 'button');
      const inFullVideo = clip.in_full_video === true && !!clip.file;
      item.setAttribute('aria-label', `Edit @${clip.slot} audio clip${inFullVideo ? ', in the full video' : ''}`);
      item.title = `${title} · ${clip.duration.toFixed(3)} s · original speed\nDrag to move · edges trim · Shift-drag selects a different source window`
        + (inFullVideo ? '\nIn the full video' : '');
      if (!reference?.replaced) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 256 36'); svg.setAttribute('preserveAspectRatio', 'none');
        svg.setAttribute('aria-hidden', 'true');
        const peaks = clip.peaks ?? [];
        const max = Math.max(.001, ...peaks);
        for (let i = 0; i < 128; i++) {
          const source = clip.source_start + (i + .5) / 128 * clip.duration;
          const peak = peaks[Math.min(peaks.length - 1, Math.floor(source / clip.source_duration * peaks.length))] ?? 0;
          const rect = document.createElementNS(svg.namespaceURI, 'rect');
          const height = Math.max(1, 32 * peak / max);
          for (const [key, value] of Object.entries({x: i * 2, y: (36 - height) / 2, width: 1, height})) rect.setAttribute(key, value);
          svg.append(rect);
        }
        item.append(svg);
      }
      item.append(node('span', 'h3ct-audio-label', `@${clip.slot} · ${title} · ${clip.duration.toFixed(2)} s${reference?.replaced ? ' · Replaced source' : ''}${clip.locked === true && clip.file ? ' · locked' : ''}`));
      for (const edge of ['left', 'right']) {
        const handle = node('div', `h3ct-audio-handle ${edge}`);
        handle.title = `Drag to trim the ${edge} edge`;
        handle.addEventListener('pointerdown', event => this.drag(event, clip, edge));
        item.append(handle);
      }
      item.addEventListener('pointerdown', event => this.drag(event, clip, event.shiftKey ? 'source' : 'move'));
      item.addEventListener('click', () => this.selectAudio(clip.slot));
      item.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); item.click(); }
        if (['ArrowLeft', 'ArrowRight'].includes(event.key)) {
          event.preventDefault(); Object.assign(clip, model.editAudioClip(clip, 'move', (event.key === 'ArrowLeft' ? -1 : 1) / model.FPS));
          this.editor.commit();
        }
      });
      lane.append(item); this.lanes.append(lane);
    }
  }

  drag(event, clip, mode) {
    if (event.button !== 0 || (event.pointerType === 'touch' && !['left', 'right'].includes(mode)
      && getComputedStyle(this.root).touchAction.includes('pan-x'))) return;
    event.preventDefault(); event.stopPropagation();
    const before = {...clip}, x = event.clientX, id = event.pointerId;
    const perPixel = this.span / model.FPS / (this.lanes.getBoundingClientRect().width || 1);
    this.selectAudio(clip.slot);
    try { this.root.setPointerCapture(id); } catch { /* synthetic test pointers */ }
    const move = e => {
      if (e.pointerId !== id) return;
      const delta = Math.round((e.clientX - x) * perPixel * model.FPS) / model.FPS;
      if (mode === 'source') clip.source_start = Math.max(0, Math.min(before.source_start + delta, clip.source_duration - clip.duration));
      else Object.assign(clip, model.editAudioClip(before, mode, delta));
      this.renderLanes();
    };
    const end = e => {
      if (e.pointerId !== id) return;
      this.root.removeEventListener('pointermove', move);
      this.root.removeEventListener('pointerup', end);
      this.root.removeEventListener('pointercancel', end);
      if (e.type === 'pointercancel') Object.assign(clip, before);
      this.editor.commit();
    };
    this.root.addEventListener('pointermove', move);
    this.root.addEventListener('pointerup', end);
    this.root.addEventListener('pointercancel', end);
  }

  renderSettings() {
    const clip = this.clips.find(clip => clip.slot === this.selected) ?? this.clips[0];
    const reference = this.editor.host.connected().audios.find(ref => ref.name === clip?.slot);
    const file = reference?.problem || (reference?.replaced && !reference.mediaFile) ? null : reference?.mediaFile ?? clip?.file;
    const signature = JSON.stringify([this.clips, clip?.slot, model.totalFrames(this.editor.state), file, reference?.replaced]);
    const typing = this.settingsClip === clip && this.settingsState === this.editor.state
      && this.settings.contains(document.activeElement) && document.activeElement.tagName === 'TEXTAREA';
    if (typing) { this.renderPlayer(file, clip); return; }
    if (this.settingsKey === signature && this.settingsClip === clip) return;
    this.settingsState = this.editor.state;
    this.settingsKey = signature; this.settingsClip = clip;
    this.settings.replaceChildren(node('summary', null, 'Audio settings · move clips and trim their edges above the clips'));
    this.settings.hidden = !this.clips.length;
    if (!clip) return;
    const row = node('div', 'h3ct-row');
    const choose = node('select', 'h3ct-select'); choose.setAttribute('aria-label', 'Selected audio clip');
    for (const c of this.clips) { const option = node('option', null, `@${c.slot} · ${c.title}`); option.value = c.slot; choose.append(option); }
    choose.value = clip.slot;
    choose.addEventListener('change', () => this.selectAudio(choose.value));
    row.append(choose, button('Fit to video', () => {
      const duration = model.totalFrames(this.editor.state) / model.FPS;
      if (!duration) { this.message.textContent = 'Add video clips first.'; return; }
      clip.start = 0; clip.duration = Math.min(duration, clip.source_duration - clip.source_start);
      this.editor.commit();
    }), button('Remove audio', () => {
      this.editor.state.audio_clips = this.clips.filter(c => c !== clip);
      if (clip.file) this.editor.state.disabled_refs = [...new Set([...this.editor.state.disabled_refs ?? [], clip.slot])];
      this.selected = this.clips[0]?.slot;
      this.editor.commit();
      if (this.selected) this.selectAudio(this.selected); else this.editor.inspectClip();
    }));
    if (clip.file) {
      const field = node('label', 'h3ct-field', 'In the full video'), input = node('input');
      input.type = 'checkbox'; input.checked = clip.in_full_video === true;
      input.setAttribute('aria-label', 'In the full video');
      field.title = 'Play this clip in the full video instead of H3’s audio';
      input.addEventListener('change', () => {
        if (input.checked) clip.in_full_video = true; else delete clip.in_full_video;
        this.editor.commit();
      });
      field.append(input); row.append(field);
      const lock = node('label', 'h3ct-field', 'Locked to the sequence clock'), locked = node('input');
      locked.type = 'checkbox'; locked.checked = clip.locked === true;
      locked.setAttribute('aria-label', 'Locked to the sequence clock');
      lock.title = 'Keep this recording at its place in the full video: a bridge across a cut inside it replaces '
        + 'footage instead of adding time, so its dialogue stays in sync';
      locked.addEventListener('change', () => {
        if (locked.checked) clip.locked = true; else delete clip.locked;
        this.editor.commit();
      });
      lock.append(locked); row.append(lock);
    } else row.append(node('span', 'h3ct-hint', 'Upload this audio’s file to play it in the full video.'));
    this.settings.append(row);
    const timing = node('div', 'h3ct-row');
    for (const [key, label] of [['start', 'Video start (s)'], ['source_start', 'Source in (s)'], ['duration', 'Length (s)']]) {
      const field = node('label', 'h3ct-field', label);
      const input = node('input', 'h3ct-number'); input.type = 'number'; input.min = key === 'duration' ? .001 : 0; input.step = '0.001';
      input.value = Number(clip[key].toFixed(6)); input.setAttribute('aria-label', label);
      input.addEventListener('change', () => {
        const value = Number(input.value);
        if (!Number.isFinite(value) || value < 0 || (key === 'duration' && value === 0)) { input.value = clip[key]; return; }
        if (key === 'source_start') { clip.source_start = Math.min(value, Math.max(0, clip.source_duration - clip.duration)); }
        else if (key === 'duration') clip.duration = Math.min(value, clip.source_duration - clip.source_start);
        else clip.start = value;
        this.editor.commit();
      });
      field.append(input); timing.append(field);
    }
    const layer = node('select', 'h3ct-select'); layer.setAttribute('aria-label', 'Audio description layer');
    for (const [value, label] of [['music', 'Music'], ['soundscape', 'Overall soundscape'], ['shot', 'Shot audio / voice']]) {
      const option = node('option', null, label); option.value = value; layer.append(option);
    }
    layer.value = clip.layer ?? 'music'; layer.addEventListener('change', () => { clip.layer = layer.value; this.editor.commit(); });
    timing.append(layer); this.settings.append(timing);
    const description = node('textarea', 'h3ct-text'); description.rows = 2;
    description.setAttribute('aria-label', `Audio description for @${clip.slot}`);
    description.placeholder = `Describe @${clip.slot} for H3 Story: instruments, mood, rhythm, ambience or voice. Story Text descriptions can override this.`;
    description.value = clip.description ?? '';
    description.addEventListener('input', () => { clip.description = description.value; this.editor.commit(false); });
    this.settings.append(description);
    this.renderPlayer(file, clip);
    const video = model.totalFrames(this.editor.state) / model.FPS;
    this.settings.append(node('div', 'h3ct-hint', (reference?.replaced ? 'Replaced source · current clip timing preserved. ' : `${clip.source_duration.toFixed(3)} s source · original playback speed. `)
      + 'Shift-drag the clip to change its source window. '
      + (clip.start > 0 || clip.start + clip.duration < video ? 'Uncovered time uses silence in this reference.' : '')));
  }

  renderPlayer(file, clip) {
    let player = this.settings.querySelector('audio');
    if (!file) { player?.pause(); player?.remove(); return; }
    if (!player) {
      player = node('audio'); player.controls = true; player.preload = 'none';
      player.addEventListener('play', () => {
        if (player.currentTime < clip.source_start || player.currentTime >= clip.source_start + clip.duration) player.currentTime = clip.source_start;
      });
      player.addEventListener('timeupdate', () => { if (player.currentTime >= clip.source_start + clip.duration) player.pause(); });
      this.settings.append(player);
    }
    const key = JSON.stringify(file);
    if (player.dataset.source !== key) {
      player.pause(); player.src = this.editor.host.viewUrl(file); player.dataset.source = key;
    }
  }
}
