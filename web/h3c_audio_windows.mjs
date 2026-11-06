// Mirrors audio_windows.py; source ownership never depends on current box order.
export const AUDIO_WINDOWS_FEATURE = 'box-audio-windows-1';
const keys = ['start', 'source_start', 'duration'];
const placement = clip => Object.fromEntries(keys.map(key => [key, clip[key]]));
const stable = value => JSON.stringify(value, (_, item) => item && typeof item === 'object' && !Array.isArray(item)
  ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item);

export function validateWindows(clip, boxes, origin) {
  if (!Object.hasOwn(clip, 'box_windows')) return;
  const saved = clip.box_windows;
  if (!saved || typeof saved !== 'object' || saved.version !== 1) throw Error('Unsupported audio windows version.');
  if (stable(saved.source) !== stable(origin) || stable(saved.placement) !== stable(placement(clip))) {
    throw Error('Unlock audio windows before changing the source or placement.');
  }
  if (!saved.by_box || typeof saved.by_box !== 'object' || Array.isArray(saved.by_box)) throw Error('Audio windows need a box mapping.');
  const ids = new Set(boxes.map(box => box.id));
  for (const [id, window] of Object.entries(saved.by_box)) {
    if (!ids.has(id) || !window || typeof window !== 'object') throw Error('Audio window refers to an unknown box.');
    for (const key of ['offset', 'source_start', 'duration']) {
      if (typeof window[key] !== 'number' || !Number.isFinite(window[key]) || window[key] < 0 || (key === 'duration' && window[key] === 0)) {
        throw Error('Audio windows need finite nonnegative times and positive durations.');
      }
    }
    if (window.source_start < clip.source_start - 1e-9 || window.source_start + window.duration > clip.source_start + clip.duration + 1e-9) {
      throw Error('Audio window is outside its captured source selection.');
    }
  }
}

export function captureWindows(clip, boxes, origin) {
  const by_box = {};
  for (const box of boxes) {
    const first = Math.max(box.start, clip.start), last = Math.min(box.start + box.duration, clip.start + clip.duration);
    if (last > first) by_box[box.id] = {offset:first-box.start, source_start:clip.source_start+first-clip.start, duration:last-first};
  }
  return {version:1, source:structuredClone(origin), placement:placement(clip), by_box};
}

export function resolveWindows(clip, boxes) {
  if (!Object.hasOwn(clip, 'box_windows')) return [{box:null, offset:0, ...placement(clip)}];
  return boxes.flatMap(box => {
    const window = Object.hasOwn(clip.box_windows.by_box, box.id) ? clip.box_windows.by_box[box.id] : null;
    if (!window) return [];
    const duration = Math.min(window.duration, box.duration-window.offset);
    return duration > 0 ? [{box:box.id, ...window, start:box.start+window.offset, duration}] : [];
  });
}

export function pruneWindows(state) {
  const ids = new Set(state.boxes.map(box => box.id));
  for (const clip of state.audio_clips ?? []) if (clip.box_windows) {
    clip.box_windows.by_box = Object.fromEntries(Object.entries(clip.box_windows.by_box).filter(([id]) => ids.has(id)));
  }
}

export function splitWindows(state, oldId, leftId, rightId, cutSeconds) {
  for (const clip of state.audio_clips ?? []) {
    const map = clip.box_windows?.by_box;
    if (!map || !Object.hasOwn(map, oldId)) continue;
    const window = map[oldId], trim = Math.max(0, cutSeconds-window.offset);
    const left = Math.min(window.duration, trim), right = window.duration-trim;
    delete map[oldId];
    clip.box_windows.by_box = {...map,
      ...(leftId && left > 0 ? {[leftId]:{...window, duration:left}} : {}),
      ...(rightId && right > 0 ? {[rightId]:{offset:Math.max(0,window.offset-cutSeconds), source_start:window.source_start+trim, duration:right}} : {})};
  }
}

export function unlockWindows(clip) {
  if (!clip.box_windows) return;
  Object.assign(clip, clip.box_windows.placement);
  delete clip.box_windows;
}

export function coalesceWindows(windows) {
  const result = [];
  for (const window of [...windows].sort((a,b)=>a.start-b.start)) {
    const last = result.at(-1);
    if (last && last.slot === window.slot && ['start','source_start'].every(key=>Math.abs(last[key]+last.duration-window[key])<1e-9)) last.duration += window.duration;
    else result.push({...window});
  }
  return result;
}
