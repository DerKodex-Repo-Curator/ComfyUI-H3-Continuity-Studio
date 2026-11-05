"""Local Timeline audio files, sample-accurate reference windows, and the soundtrack the full video plays instead of
H3's audio. No time stretching."""

import hashlib
import os

import av
import folder_paths
import torch
import torch.nn.functional as F
from comfy_extras.nodes_audio import load as load_audio
from comfy_api.latest import io, ui

from . import timeline as rules
from . import reference_replacements
from .timing import FPS, sample_at_frame

SOUNDTRACK_KEYS = ("slot", "file", "start", "source_start", "duration")


def file_path(file):
    rules.audio_file(file)
    root = folder_paths.get_directory_by_type(file["type"])
    path = os.path.realpath(os.path.join(root, file.get("subfolder", ""), file["filename"]))
    if not folder_paths.is_within_directory(os.path.realpath(root), path):
        raise ValueError("H3 Timeline: audio must stay inside its ComfyUI folder")
    if not os.path.isfile(path):
        raise ValueError(f"H3 Timeline: audio file is missing: {file['filename']}")
    return path


def read(file):
    try:
        waveform, sample_rate = load_audio(file_path(file))
    except (av.error.FFmpegError, ValueError, OSError) as error:
        raise ValueError(f"H3 Timeline: could not read audio: {error}") from None
    return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}


def metadata(file):
    audio = read(file)
    wave = audio["waveform"]
    envelope = wave.abs().amax(dim=1)
    peaks = F.adaptive_max_pool1d(envelope, min(256, wave.shape[-1]))[0].tolist()
    return {"duration": wave.shape[-1] / audio["sample_rate"], "sample_rate": audio["sample_rate"], "peaks": peaks}


def load_sources(timeline, audios):
    sources = dict(audios)
    for clip in timeline.audio_clips:
        slot = clip["slot"]
        if slot in timeline.reference_replacements:
            continue
        if slot in timeline.disabled_refs:
            continue
        if "file" in clip:
            if slot in sources:
                raise ValueError(f"H3 Timeline: {slot} has both an uploaded clip and a connected audio input")
            sources[slot] = read(clip["file"])
        elif slot not in sources:
            raise ValueError(f"H3 Timeline: connect {slot} again or remove its audio clip")
    return sources


def for_box(timeline, index, context, sources):
    if not timeline.audio_clips:
        return dict(sources)
    timed = {clip["slot"] for clip in timeline.audio_clips}
    result = {slot: audio for slot, audio in sources.items() if slot not in timed}
    frames, carried = rules.box_length(timeline, index, context)
    start = rules.box_start(timeline, index) - carried / FPS
    end = start + (frames + carried) / FPS
    for clip in rules.active_audio_clips(timeline, index):
        if any(ref['slot'] == clip['slot'] and ref.get('strength', 1) > 0 for ref in timeline.refmods):
            continue
        source = sources[clip["slot"]]
        rate, wave = source["sample_rate"], source["waveform"]
        # Absolute endpoints keep adjacent boxes on the same sample clock, including non-24-divisible rates.
        first, last = round(start * rate), round(end * rate)
        chunk = wave.new_zeros((*wave.shape[:-1], last - first))
        offset = round(clip["source_start"] * rate) - round(clip["start"] * rate)
        left = max(first, round(clip["start"] * rate), -offset)
        right = min(last, round((clip["start"] + clip["duration"]) * rate), wave.shape[-1] - offset)
        if right > left:
            chunk[..., left - first:right - first] = wave[..., left + offset:right + offset]
        result[clip["slot"]] = {"waveform": chunk, "sample_rate": rate}
    return result


def fingerprint(timeline):
    files = [file_path(file) for clip in timeline.audio_clips if clip['slot'] not in timeline.disabled_refs
             if (file := reference_replacements.file_for(timeline, clip['slot']))]
    return [(path, os.stat(path).st_mtime_ns, os.stat(path).st_size) for path in files]


def marked(timeline, snapshots=None):
    """The clips the full video plays instead of H3's audio, as placed, in slot order."""
    clips = []
    for clip in sorted(timeline.audio_clips, key=lambda clip: clip['slot']):
        if clip.get('in_full_video') is not True:
            continue
        file = reference_replacements.file_for(timeline, clip['slot'])
        if file is None:
            record = (snapshots or {}).get(clip['slot'], {})
            source = reference_replacements.origin(clip['slot'], reference_replacements.effective(timeline))
            if record.get('replacement') == source and not any(
                    ref['slot'] == clip['slot'] and ref.get('strength', 1) > 0 for ref in timeline.refmods):
                file = record['file']
        if file is None:
            raise ValueError(f"H3 Timeline: {clip['slot']}'s full-video soundtrack replacement needs an uploaded audio file")
        clips.append({**{key: clip[key] for key in SOUNDTRACK_KEYS if key != 'file'}, 'file': file})
    return clips


def snapshot_replacements(timeline, sources, name, records):
    """Save resolved wired soundtrack audio using native FLAC saving, once per waveform, for later export/status."""
    changed = False
    replacements = reference_replacements.effective(timeline)
    for clip in timeline.audio_clips:
        slot = clip['slot']
        if clip.get('in_full_video') is not True or reference_replacements.file_for(timeline, slot) is not None:
            continue
        source = reference_replacements.origin(slot, replacements)
        audio = sources.get(slot) or sources.get(source.get('source'))
        if audio is None:
            continue
        wave = audio['waveform'].detach().float().contiguous().cpu()
        digest = hashlib.sha256(str((audio['sample_rate'], tuple(wave.shape))).encode())
        digest.update(wave.numpy().tobytes())
        digest = digest.hexdigest()
        record = records.get(slot, {})
        if record.get('replacement') == source and record.get('digest') == digest:
            from . import studio_pictures
            found = studio_pictures.path(record['file'])
            if found and record.get('stamp') == [os.stat(found).st_mtime_ns, os.stat(found).st_size]:
                continue
        saved = ui.AudioSaveHelper.save_audio(audio, f'h3_sequences/{name}/reference_audio_{digest}',
                                              io.FolderType.output, None)[0]
        file = dict(saved)
        path = file_path(file)
        stat = os.stat(path)
        records[slot] = dict(replacement=source, digest=digest, file=file, stamp=[stat.st_mtime_ns, stat.st_size])
        changed = True
    return changed


def soundtrack_sources(clips):
    sources = []
    for clip in clips:
        path = file_path(clip["file"])
        stat = os.stat(path)
        sources.append([clip, path, stat.st_mtime_ns, stat.st_size])
    return sources


def place(clips, sources, parts):
    """The full video's audio: `clips` from their decoded `sources` by slot, on the full video's clock.

    `parts` holds (played frames, is a bridge) for the full video's boxes and bridges in order. A clip starts with
    the box its start falls in, after the bridges before that box, and plays straight through; it is cut at the end.
    Overlapping clips add up within full scale. Returns (waveform [C, S], sample_rate)."""
    rate = sources[clips[0]["slot"]]["sample_rate"]
    waves = {}
    for clip in clips:
        source = sources[clip["slot"]]
        wave = source["waveform"][0].float().cpu()
        if source["sample_rate"] != rate:
            import comfy.audio
            wave = comfy.audio.resample(wave, source["sample_rate"], rate)
        waves[clip["slot"]] = wave
    channels = 2 if any(wave.shape[0] >= 2 for wave in waves.values()) else 1
    out = torch.zeros(channels, sample_at_frame(sum(frames for frames, _ in parts), rate))
    boxes, on_timeline, in_video = [], 0, 0
    for frames, bridge in parts:
        if not bridge:
            boxes.append((on_timeline / FPS, (in_video - on_timeline) / FPS))
            on_timeline += frames
        in_video += frames
    for clip in clips:
        if clip["start"] >= on_timeline / FPS:
            continue
        shift = next(shift for begin, shift in reversed(boxes) if clip["start"] >= begin)
        wave = waves[clip["slot"]]
        wave = wave[:channels] if wave.shape[0] >= channels else wave.repeat(channels, 1)
        start = clip["start"] + shift
        offset = round(clip["source_start"] * rate) - round(start * rate)
        left = max(0, round(start * rate), -offset)
        right = min(out.shape[-1], round((start + clip["duration"]) * rate), wave.shape[-1] - offset)
        if right > left:
            out[:, left:right] += wave[:, left + offset:right + offset]
    return out.clamp_(-1, 1), rate


def soundtrack_audio(clips, parts):
    return place(clips, {clip["slot"]: read(clip["file"]) for clip in clips}, parts)


def named(clips):
    """'@audio1', '@audio1 and @audio2' or '@audio1, @audio2 and @audio3'."""
    slots = [f"@{clip['slot']}" for clip in clips]
    return slots[0] if len(slots) == 1 else ", ".join(slots[:-1]) + " and " + slots[-1]
