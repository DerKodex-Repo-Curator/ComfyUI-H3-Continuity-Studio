// Split a clip at an accepted mid-clip guide. The guide becomes the left clip's Last and the right clip's First, and
// the right clip continues the left one, so H3 generates toward the guide and onward from it instead of inserting it.
// Coordinates follow timeline.frame_guides: on a continuing clip, local frame 0 is the shared boundary.
import { promptShots } from './h3c_prompt_sections.mjs?v=20261010-reference-workspace-1';
import {
  FPS, isFresh, limits, newId, newSeed, mentions, assemblePrompt, effectiveRefmods, activeAudioClips, referenceEnabled,
} from './h3c_timeline_model.mjs?v=20261013-node-settings-1';
import { frameTargets, acceptedGuideFrames } from './h3c_shot_preview.mjs?v=20261012-still-prompts-1';
import { halfPrompt, roundUp, number, start } from './h3c_shot_split.mjs?v=20261103-guide-split-1';

const canonical = (target) => target?.kind === 'shot' && target.shot === 1 ? { kind: 'first' } : target;
const sameTarget = (a, b) => a?.kind === b?.kind && a?.shot === b?.shot;
const sameFile = (a, b) => !!a && !!b && ['filename', 'subfolder', 'type'].every((key) => a[key] === b[key]);
const seconds = (frames) => `${(frames / FPS).toFixed(2)} s`;

// The local frame a saved record guides: targets follow the current timing, legacy records keep their frame.
function recordFrame(targets, item) {
  if (!item.target) return Number.isInteger(item.frame) ? item.frame : null;
  const target = canonical(item.target);
  return targets.find((p) => sameTarget(p.target, target))?.frame ?? null;
}

export function guideSplitTiming(state, index, preview, context) {
  const box = state.boxes[index];
  if (!box || !(box.previews ?? []).includes(preview)) throw new Error('This guide was removed from the clip.');
  if (!preview.guide) throw new Error('Use an image as this marker’s guide before splitting at it.');
  const fresh = isFresh(state, index), carry = fresh ? 0 : context;
  const frame = recordFrame(frameTargets(state, index, context), preview);
  const last = box.frames - (fresh ? 1 : 0);
  if (frame == null) throw new Error('This guide’s shot has no readable time, so there is no frame to split at.');
  if (frame <= 0) throw new Error('This guide is already the clip’s First frame.');
  if (frame >= last) throw new Error('This guide is already the clip’s Last frame.');
  // The left clip ends on the guide; the right clip continues from it and plays the rest.
  const needLeft = fresh ? frame + 1 : frame, needRight = last - frame;
  // A continued clip must not drop frames, so the left half is always on the grid; an exact right half stays exact.
  const left = roundUp(needLeft, fresh, context);
  const right = box.exact ? needRight : roundUp(needRight, false, context);
  if (left > limits(fresh, context).max || right > limits(false, context).max) {
    throw new Error('Splitting at this guide cannot fit both clips within H3’s clip limit.');
  }
  if (fresh && left < context) {
    throw new Error(`This guide is too close to the start: the first clip would play ${left} frames, `
      + `fewer than the ${context} the second clip carries.`);
  }
  const generated = frame + (carry ? carry - 1 : 0);
  return {
    frame, left, right, needLeft, needRight, fresh, carry, generated,
    // The guide becomes the right clip's generated frame context - 1: later timestamps move by this many frames.
    offset: generated - (context - 1),
    moved: left - needLeft, added: left - needLeft + right - needRight,
  };
}

// The shots each half keeps. A guide on a shot's start splits before that shot; a guide inside a shot puts it in both.
function divideShots(parsed, generated) {
  const shots = parsed.shots;
  if (!shots.length) return null;
  if (new Set(shots.map(number)).size !== shots.length) throw new Error('Give each shot a unique number before splitting.');
  const starts = shots.map((shot, i) => {
    if (i === 0) return 0;
    const ms = start(shot);
    return ms == null ? null : Math.round(ms * FPS / 1000);
  });
  if (starts.some((t, i) => t == null || (i && t <= starts[i - 1]))) {
    throw new Error('Every later shot needs an increasing cut timestamp (“At MM:SS.mmm,”) before splitting at a guide.');
  }
  let k = 0;
  while (k + 1 < shots.length && starts[k + 1] <= generated) k++;
  const onStart = k > 0 && starts[k] === generated;
  return { left: shots.slice(0, onStart ? k : k + 1), right: shots.slice(k), shot: number(shots[k]), mid: !onStart };
}

function placeRecord(item, shots, nextOrphan) {
  const saved = structuredClone(item);
  if (saved.target?.kind === 'shot') {
    const shot = shots.get(saved.target.shot);
    if (shot != null) saved.target = shot === 1 ? { kind: 'first' } : { kind: 'shot', shot };
  } else if (!saved.target) {
    // Legacy records are keyed by unique shot numbers; Shot 1 means First, so only frame 0 may take it.
    const shot = shots.get(saved.shot);
    saved.shot = shot != null && (shot !== 1 || saved.frame === 0) ? shot : nextOrphan();
  }
  return saved;
}

export function splitAtGuide(state, index, preview, context) {
  const timing = guideSplitTiming(state, index, preview, context);
  const original = state.boxes[index], parsed = promptShots(original.prompt);
  const { frame, fresh, carry } = timing;
  const shots = divideShots(parsed, timing.generated);

  const left = { ...structuredClone(original), frames: timing.left, last: '' };
  const right = { ...structuredClone(original), id: newId(state), seed: newSeed(), frames: timing.right, cut: false, first: '' };
  delete right.new_scene;
  delete right.join;
  // Each half has new prompt text, so the Story source and its <Subject N> cast no longer describe it.
  for (const half of [left, right]) {
    delete half.cast;
    delete half.source;
    delete half.previews;
    delete half.plate_changes;
    delete half.plate_edits;
  }

  if (shots) {
    left.prompt = halfPrompt(parsed, shots.left, state.prompt, 0, carry ? '' : original.first, '',
      (timing.left + carry) / FPS, { stripFirst: false, endpoint: true });
    right.prompt = halfPrompt(parsed, shots.right, state.prompt, Math.round(timing.offset * 1000 / FPS), '',
      original.last, (timing.right + context) / FPS, { stripFirst: true });
  }

  // Guide records: the same PNG closes the left clip and opens the right one, as a paired continuous boundary.
  const { guide, images = [], ...settings } = structuredClone(preview);
  delete settings.target;
  delete settings.shot;
  delete settings.frame;
  const closing = { target: { kind: 'last' }, frame: timing.left - (fresh ? 1 : 0), guide: structuredClone(guide) };
  const leftPreviews = [];
  const opening = { ...settings, target: { kind: 'first' }, frame: 0, guide };
  const rightPreviews = [opening];
  const leftShots = new Map((shots?.left ?? []).map((s, i) => [number(s), i + 1]));
  const rightShots = new Map((shots?.right ?? []).map((s, i) => [number(s), i + 1]));
  let leftOrphan = leftShots.size, rightOrphan = rightShots.size;
  const targets = frameTargets(state, index, context);
  for (const item of original.previews ?? []) {
    if (item === preview) continue;
    const at = recordFrame(targets, item);
    if (at == null) {
      leftPreviews.push(structuredClone(item)); // Listed as removed in the Shots tab, where it can be deleted.
    } else if (at < frame) {
      leftPreviews.push(placeRecord(item, leftShots, () => ++leftOrphan));
    } else if (at > frame) {
      const saved = placeRecord(item, rightShots, () => ++rightOrphan);
      saved.frame = canonical(saved.target)?.kind === 'last' ? timing.right : at - frame;
      rightPreviews.push(saved);
    } else {
      if (item.guide && !sameFile(item.guide, guide)) {
        throw new Error('Another accepted guide owns this frame. Remove one of them first.');
      }
      images.push(...structuredClone(item.images ?? []));
    }
  }
  if (images.length) opening.images = images;
  left.previews = [...leftPreviews, closing];
  right.previews = rightPreviews;

  // Appearance changes from the guide onward belong to the right clip.
  for (const key of ['plate_changes', 'plate_edits']) {
    if (!original[key]) continue;
    const before = original[key].filter((p) => p.frame < frame).map((p) => structuredClone(p));
    const after = original[key].filter((p) => p.frame >= frame).map((p) => ({ ...structuredClone(p), frame: p.frame - frame }));
    if (before.length) left[key] = before;
    if (after.length) right[key] = after;
  }

  // Played-frame references past the guide (pins, other clips' chosen memories) now point into the right clip.
  const move = (item) => {
    if (item?.box !== original.id || !Number.isInteger(item.frame) || item.frame < timing.needLeft) return;
    item.box = right.id;
    item.frame = Math.min(item.frame - timing.needLeft, timing.right - 1);
  };
  for (const entity of Array.isArray(state.bible?.entities) ? state.bible.entities : []) {
    for (const pin of Array.isArray(entity?.pins) ? entity.pins : []) move(pin);
  }
  for (const box of state.boxes) if (box !== original) for (const memory of box.memories ?? []) move(memory);

  state.boxes.splice(index, 1, left, right);

  // References keep a half FLF2VA only through cached RefMods (timeline.box_slots): raw audio or video still makes it
  // REF2VA, and so does a fresh clip with neither a First image nor a First guide.
  const mods = new Set(effectiveRefmods(state).map((ref) => ref.slot));
  const refmods = [], raw = [], noFirst = [];
  for (const at of [index, index + 1]) {
    const box = state.boxes[at], freshHalf = isFresh(state, at);
    const keyframes = [freshHalf ? box.first : '', box.last].filter(Boolean);
    const found = mentions(assemblePrompt(state, at));
    const usesRefs = found.some((m) => m.kind === 'image' && (mods.has(m.name) || !keyframes.includes(m.name)));
    const usesRaw = found.some((m) => m.kind === 'video' || m.kind === 'video_audio'
      || (m.kind === 'audio' && !mods.has(m.name))) || activeAudioClips(state, at).some((clip) => !mods.has(clip.slot));
    const opens = !freshHalf || (box.first && referenceEnabled(state, box.first))
      || acceptedGuideFrames(state, at, context).includes(0);
    if (usesRaw) raw.push(at);
    else if (usesRefs && !opens) noFirst.push(at);
    else if (usesRefs && !box.flf_refmods) {
      box.flf_refmods = true;
      refmods.push(at);
    }
  }
  return { ...timing, index, mid: !!shots?.mid, shot: shots?.shot ?? null, refmods, raw, noFirst };
}

// The Split at guide button's tooltip, before the split.
export function describeGuideSplitTiming(timing, index) {
  return `Make Clip ${index + 1} end on this guide (${seconds(timing.left)}) and a new Clip ${index + 2} continue from it `
    + `(${seconds(timing.right)}), so H3 generates toward the guide instead of inserting it.`
    + (timing.added ? ` Adds ${seconds(timing.added)} for H3’s frame grid` + (timing.moved ? `; the guide lands ${seconds(timing.moved)} later.` : '.') : '');
}

const clips = (list) => list.map((at) => `Clip ${at + 1}`).join(' and ');

// The note shown after a split: what changed, what moved, and what still needs the user.
export function describeGuideSplit(result) {
  const { index } = result;
  const parts = [`Clip ${index + 1} now ends on the guide (${seconds(result.left)}) and Clip ${index + 2} continues `
    + `from it (${seconds(result.right)}).`];
  if (result.added) {
    parts.push(`H3’s frame grid adds ${seconds(result.added)}`
      + (result.moved ? `; the guide lands ${seconds(result.moved)} later.` : '.'));
  }
  if (result.mid && result.shot != null) {
    parts.push(`The guide fell inside Shot ${result.shot}, so both clips keep its text: edit each to end at, or start from, the guide.`);
  }
  if (result.refmods.length) {
    parts.push(`FLF2VA + cached RefMods is now on for ${clips(result.refmods)}, so references don’t turn the guide into an insert. `
      + 'It needs H3’s VAE loaded from a file (VAELoader).');
  }
  if (result.raw.length) {
    parts.push(`${clips(result.raw)} uses raw audio or video references, so it still runs as REF2VA and the guide stays an insert there.`);
  }
  if (result.noFirst.length) {
    parts.push(`${clips(result.noFirst)} has references but no First frame, so it still runs as REF2VA. `
      + 'Add a First guide to make it FLF2VA with cached RefMods.');
  }
  return parts.join(' ');
}
