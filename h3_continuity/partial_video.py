"""Playback of current rendered boxes, with source-filled gaps for video_slices when its saved source is available."""

import hashlib
import json
import os

import torch
from safetensors import safe_open
from safetensors.torch import save_file

from . import audio_tracks, media, store, timing
from . import timeline as rules
from .nodes import SEQUENCE_LOCK

SOURCE_CRF = 18
NO_FRAMES = "Partial video skipped: a rendered clip's video or audio file is missing."


def _sound_slot(slot):
    return slot.replace("video", "video_audio")


def keep_source(folder, name, slot, images, audios, width, height, digest):
    """Saves `slot`'s whole frame batch as `{name}_source.mp4`, scaled to width x height at 24 fps, and its
    same-numbered soundtrack as `{name}_source.safetensors`, unless the manifest's source already holds the same media
    at that size. `digest(slot)` hashes an input the way the boxes' media hashes do. Returns True when it wrote them."""
    sound = _sound_slot(slot)
    heard = sound in audios
    fingerprint = hashlib.sha1(json.dumps([slot, digest(slot), digest(sound) if heard else None, width, height])
                               .encode("utf-8")).hexdigest()
    with SEQUENCE_LOCK:
        record = store.load_manifest(folder).get("source") or {}
    if record.get("fingerprint") == fingerprint and os.path.isfile(os.path.join(folder, record.get("file", ""))):
        return False
    os.makedirs(folder, exist_ok=True)
    frames = images[slot]
    temporary = os.path.join(folder, f"{name}_source.mp4.tmp.mp4")
    media.write_segment_video(temporary, frames, timing.FPS, SOURCE_CRF, size=(width, height))
    written, _ = media._replace(temporary, os.path.join(folder, f"{name}_source.mp4"))
    audio_file = f"{name}_source.safetensors"
    if heard:
        waveform = audios[sound]["waveform"][0, :2].float().cpu().contiguous()
        save_file({"waveform": waveform}, os.path.join(folder, audio_file),
                  metadata={"sample_rate": str(int(audios[sound]["sample_rate"]))})
    with SEQUENCE_LOCK:
        manifest = store.load_manifest(folder)
        manifest["source"] = {"file": os.path.basename(written), "audio": audio_file if heard else None, "slot": slot,
                              "frames": int(frames.shape[0]), "width": width, "height": height,
                              "fingerprint": fingerprint}
        store.write_manifest(folder, manifest)
    return True


def _source_audio(folder, source):
    if not source.get("audio"):
        return None
    with safe_open(os.path.join(folder, source["audio"]), framework="pt") as f:
        return f.get_tensor("waveform"), int(f.metadata()["sample_rate"])


def _stamp(folder, filename):
    try:
        stat = os.stat(os.path.join(folder, filename))
    except FileNotFoundError:
        return None
    return [filename, stat.st_mtime_ns, stat.st_size]


def parts(parsed, manifest, done):
    """Each box in Timeline order as (saved entry, first frame, frames): its saved segment from its first frame when
    the box is in `done` and has saved frames, else (None, the box's first frame in the Timeline, its frames)."""
    by_index = {entry["index"]: entry for entry in manifest["segments"]}
    found, position = [], 0
    for index in range(len(parsed.boxes)):
        count = rules.played_frames(parsed, index)
        entry = by_index.get(index + 1)
        if index in done and entry is not None and entry.get("video"):
            found.append((entry, 0, store.played_frames(entry)))
        else:
            found.append((None, position, count))
        position += count
    return found


def build(folder, name, parsed, manifest, done, soundtrack, crf):
    """`{name}_partial.mp4` from current renders, filling gaps only when a split-video source is saved.
    Marked `soundtrack` clips use the original Timeline clock; otherwise use each part's own audio.
    The saved file is reused while its sources are unchanged.
    Returns (manifest record or None, why it was not built or "")."""
    source = manifest.get("source")
    if source and source.get("slot") not in parsed.video_slices:
        source = None
    found = parts(parsed, manifest, done)
    if not source:
        for index, (entry, first, count) in enumerate(found):
            if entry is not None and not os.path.isfile(os.path.join(folder, entry["video"]["file"])):
                found[index] = (None, first, count)
    rendered = [entry for entry, _, _ in found if entry is not None]
    gaps = [first + count for entry, first, count in found if entry is None]
    if not rendered or (source and not gaps):
        return None, ""
    needed = max(gaps, default=0)
    if source and source["frames"] < needed:
        return None, (f"Partial video skipped: {source['slot']} has {source['frames']} frames, but the Timeline needs "
                      f"{needed}.")
    sources = ([_stamp(folder, source["file"]), _stamp(folder, source["audio"]) if source.get("audio") else []]
               if source else [])
    if None in sources:
        return None, ""
    items = [["source", source, sources], ["mux_audio", parsed.mux_audio]]
    for entry, first, count in found:
        if entry is None:
            items.append([None, first, count])
            continue
        files = [entry["video"]["file"], *([entry["stem"] + ".safetensors"] if entry.get("audio_sample_rate") else [])]
        stamps = [_stamp(folder, filename) for filename in files]
        if None in stamps:
            return None, NO_FRAMES
        items.append([entry, stamps, first, count])
    if soundtrack:
        items.append(["soundtrack", audio_tracks.soundtrack_sources(soundtrack)])
    fingerprint = hashlib.sha1(json.dumps(items, sort_keys=True).encode("utf-8")).hexdigest()
    record = manifest.get("partial_video")
    if (record and record.get("sources") == fingerprint and os.path.basename(record["file"]) == record["file"]
            and os.path.isfile(os.path.join(folder, record["file"]))):
        return record, ""

    if soundtrack:
        audio = audio_tracks.soundtrack_audio(soundtrack, [(count, False) for _, _, count in found])
        if not source:
            waveform, rate = audio
            chunks, position = [], 0
            for entry, _, count in found:
                if entry is not None:
                    chunks.append(waveform[:, timing.sample_at_frame(position, rate):
                                          timing.sample_at_frame(position + count, rate)])
                position += count
            audio = torch.cat(chunks, dim=-1), rate
    else:
        heard, pieces = _source_audio(folder, source) if source else None, []
        for entry, first, count in found:
            if entry is not None:
                pieces.append((entry["context_frames"] + count, entry["context_frames"],
                               store.load_waveform(folder, entry) if entry.get("audio_sample_rate") else None,
                               entry.get("audio_sample_rate")))
            elif heard is not None:
                waveform, rate = heard
                pieces.append((count, 0, waveform[:, timing.sample_at_frame(first, rate):
                                                  timing.sample_at_frame(first + count, rate)], rate))
            elif source:
                pieces.append((count, 0, None, None))
        audio = media.assemble_audio(pieces)
    windows = [(os.path.join(folder, entry["video"]["file"] if entry else source["file"]), first, count)
               for entry, first, count in found if entry is not None or source]
    video = rendered[0]["video"]
    size = (video["width"], video["height"]) if video.get("width") and video.get("height") else None
    written, note = media.build_full_video(os.path.join(folder, f"{name}_partial.mp4"), windows, audio, crf, size)
    if written is None:
        return None, f"Partial video skipped: {note.removeprefix('Full video skipped: ')}"
    record = {"file": os.path.basename(written), "sources": fingerprint, "rendered": len(rendered), "boxes": len(found),
              "mode": "source" if source else "rendered"}
    manifest["partial_video"] = record
    store.write_manifest(folder, manifest)
    return record, ""
