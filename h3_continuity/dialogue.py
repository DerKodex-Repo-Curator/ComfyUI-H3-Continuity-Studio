"""Dialogue cues bound to the Timeline's recordings: identity, source and sequence clocks, and what a locked
recording means for the picture. Pure Python.

A cue's times belong to its recording's source; the clip placement maps them onto the sequence, as
`sequence = clip.start + source - clip.source_start`."""

import copy
import hashlib
import json
import math

from .timing import FPS
from . import timed_text

VERSION = 1
PORTRAYALS = ("on_screen", "voiceover", "unknown")
ORIGINS = ("manual", "transcript", "story")
RECORDING_SLOTS = ("audio1", "audio2", "audio3")
# Clip and cue times are decimal seconds; a frame edge within this of a time is that edge.
EPSILON = 1e-6


def _error(message):
    return ValueError(f"H3 Timeline: dialogue {message}")


def _seconds(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise _error(f"{what} must be a nonnegative number of seconds")
    return value


def _same_file(one, other):
    if not isinstance(one, dict) or not isinstance(other, dict):
        return False
    return all(one.get(key, "") == other.get(key, "") for key in ("type", "subfolder", "filename"))


def validate(value):
    """An independent copy of the Timeline's `dialogue`, or None; raises naming the problem."""
    if value is None:
        return None
    from . import timeline as rules
    if not isinstance(value, dict) or value.get("version") != VERSION:
        raise _error(f"must be an object with version {VERSION}")
    if not isinstance(value.get("cues", []), list) or not isinstance(value.get("observed", []), list):
        raise _error("cues and observed must be lists")
    ids = set()
    for n, cue in enumerate(value.get("cues", []), 1):
        if not isinstance(cue, dict) or not isinstance(cue.get("id"), str) or not cue["id"] or cue["id"] in ids:
            raise _error(f"cue {n} needs a unique nonempty id")
        ids.add(cue["id"])
        name = f"cue {cue['id']!r}"
        recording = cue.get("recording")
        if not isinstance(recording, dict) or recording.get("slot") not in RECORDING_SLOTS:
            raise _error(f"{name} needs a recording on audio1, audio2 or audio3")
        rules.audio_file(recording.get("file"))
        start, end = _seconds(cue.get("start"), f"{name} start"), _seconds(cue.get("end"), f"{name} end")
        if end <= start:
            raise _error(f"{name} must end after its start")
        if not isinstance(cue.get("text"), str) or not cue["text"].strip():
            raise _error(f"{name} needs its exact words")
        token = timed_text.CONTROL.search(cue["text"])
        if token:
            raise _error(f"{name} contains {token.group(0)!r}; write only the spoken words")
        for key in ("speaker", "language", "aligned"):
            if key in cue and not isinstance(cue[key], str):
                raise _error(f"{name} {key} must be text")
        if cue.get("portrayal") not in PORTRAYALS:
            raise _error(f"{name} portrayal must be on_screen, voiceover or unknown")
        if cue.get("origin", "manual") not in ORIGINS:
            raise _error(f"{name} origin must be manual, transcript or story")
        spans = cue.get("spans", [])
        if not isinstance(spans, list):
            raise _error(f"{name} spans must be a list")
        previous = start
        for span in sorted(spans, key=lambda item: item.get("start", 0) if isinstance(item, dict) else 0):
            if not isinstance(span, dict) or span.get("portrayal") not in PORTRAYALS:
                raise _error(f"{name} spans need an on_screen, voiceover or unknown portrayal")
            low, high = _seconds(span.get("start"), f"{name} span start"), _seconds(span.get("end"), f"{name} span end")
            if not start <= low < high <= end:
                raise _error(f"{name} spans must lie inside its cue")
            if low < previous - EPSILON:
                raise _error(f"{name} spans overlap")
            previous = high
    observed_ids = set()
    for n, item in enumerate(value.get("observed", []), 1):
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]
                or item["id"] in observed_ids or not isinstance(item.get("box"), str)
                or not isinstance(item.get("take"), str) or not isinstance(item.get("label", ""), str)
                or type(item.get("start")) is not int or type(item.get("end")) is not int
                or not 0 <= item["start"] < item["end"]):
            raise _error(f"observed protection {n} needs a unique id, a box, its take and a frame range")
        observed_ids.add(item["id"])
    return copy.deepcopy(value)


def cues(timeline):
    return (timeline.dialogue or {}).get("cues", [])


def observed(timeline):
    return (timeline.dialogue or {}).get("observed", [])


def binding(cue, timeline):
    """("bound" | "missing" | "changed", clip or None): whether the cue's recording still plays from its slot."""
    from . import reference_replacements
    slot = cue["recording"]["slot"]
    clip = next((item for item in timeline.audio_clips if item["slot"] == slot), None)
    if clip is None or slot in timeline.disabled_refs:
        return "missing", None
    if not _same_file(reference_replacements.file_for(timeline, slot), cue["recording"]["file"]):
        return "changed", clip
    return "bound", clip


def alignment_key(cue):
    """What a user checks against the recording: its words, its source interval and the recording itself."""
    file = cue["recording"]["file"]
    value = [cue["recording"]["slot"], [file.get(key, "") for key in ("type", "subfolder", "filename")],
             cue["start"], cue["end"], cue["text"]]
    return hashlib.sha1(json.dumps(value, separators=(",", ":")).encode("utf-8")).hexdigest()


def is_aligned(cue):
    return cue.get("aligned") == alignment_key(cue)


def frame_floor(seconds):
    return math.floor(seconds * FPS + EPSILON)


def frame_ceil(seconds):
    return math.ceil(seconds * FPS - EPSILON)


def _segments(cue):
    """(source start, source end, portrayal) covering the cue; spans override its portrayal."""
    result, cursor = [], cue["start"]
    for span in sorted(cue.get("spans", []), key=lambda item: item["start"]):
        if span["start"] > cursor:
            result.append((cursor, span["start"], cue["portrayal"]))
        result.append((span["start"], span["end"], span["portrayal"]))
        cursor = span["end"]
    if cursor < cue["end"]:
        result.append((cursor, cue["end"], cue["portrayal"]))
    return result


def placed(cue, clip):
    """The cue through its clip's placed window, or None when the window leaves none of it. `frames` and
    `segments` round speech outward to whole sequence frames."""
    low, high = clip["source_start"], clip["source_start"] + clip["duration"]
    start, end = max(cue["start"], low), min(cue["end"], high)
    if end - start <= EPSILON:
        return None

    def sequence(seconds):
        return clip["start"] + seconds - low

    segments = []
    for first, last, portrayal in _segments(cue):
        first, last = max(first, start), min(last, end)
        if last - first > EPSILON:
            segments.append((frame_floor(sequence(first)), frame_ceil(sequence(last)), portrayal))
    return {"source": (start, end), "sequence": (sequence(start), sequence(end)),
            "frames": (frame_floor(sequence(start)), frame_ceil(sequence(end))),
            "cut": start > cue["start"] + EPSILON or end < cue["end"] - EPSILON, "segments": segments}


def projected(timeline):
    """Every cue with its binding state and, when bound and placed, its sequence position."""
    result = []
    for cue in cues(timeline):
        state, clip = binding(cue, timeline)
        where = placed(cue, clip) if state == "bound" else None
        result.append({"id": cue["id"], "cue": cue, "state": state, "slot": cue["recording"]["slot"],
                       "aligned": is_aligned(cue), "placed": where is not None,
                       "cut": bool(where and where["cut"]), "sequence": where and where["sequence"],
                       "frames": where and where["frames"], "segments": where["segments"] if where else []})
    return result


def locked_clips(timeline):
    return [clip for clip in timeline.audio_clips if clip.get("locked") is True and clip["slot"] not in timeline.disabled_refs]


def lock_conflicts(timeline):
    """Why a locked recording and the picture would not stay together in the full video; [] when they do."""
    from . import timeline as rules
    messages = []
    positions = {box.id: index for index, box in enumerate(timeline.boxes)}
    for clip in locked_clips(timeline):
        slot = clip["slot"]
        if clip.get("in_full_video") is not True:
            messages.append(f"@{slot} is locked to the sequence clock but isn't in the full video: turn on "
                            "In the full video, or unlock it.")
        start, end = clip["start"], clip["start"] + clip["duration"]
        for bridge in timeline.bridges:
            if "frames" not in bridge:
                continue
            index = positions[bridge["before"]]
            join = rules.box_start(timeline, index)
            if start < join < end:
                messages.append(f"@{slot} is locked to the sequence clock, but the bridge before box {index + 1} "
                                f"inserts {bridge['frames'] / FPS:.2f} s inside it, so the picture after it drifts "
                                "from the recording: replace within the existing duration, or remove the bridge.")
    return messages
