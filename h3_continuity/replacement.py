"""Replacement bridges: a reviewed region around a cut that a generated candidate replaces with exactly as many
frames, so the sequence keeps its duration and a locked recording keeps its place. Pure Python.

A replacement before box B covers sequence frames [J - left, J + right), J being B's first frame. Its run carries
C' frames of the surviving footage before the region and freezes E' frames of the surviving footage after it, each
on H3's 17k+5 grid, so C' + N + E' stays on the grid for N = left + right in 12, 29 or 46."""

from dataclasses import dataclass

from .timing import FPS
from . import dialogue
from . import timeline as rules

GRID = 17


@dataclass
class Geometry:
    index: int
    join: int
    left: int
    right: int
    frames: int
    start: int
    end: int
    context_frames: int = 0
    ending_frames: int = 0
    # (box index, first frame in that box's saved run, frames); a run's frame 0 is its first carried frame.
    left_window: tuple | None = None
    right_window: tuple | None = None
    generated: int = 0
    problem: str = ""


def canon_floor(frames):
    """The longest 17k+5 length within `frames`, or None below 5."""
    return None if frames < 5 else GRID * ((frames - 5) // GRID) + 5


def records(timeline):
    """Every bridge record, insertion or replacement, in the Timeline's order."""
    return timeline.all_bridges


def position(timeline, bridge):
    return next(index for index, box in enumerate(timeline.boxes) if box.id == bridge["before"])


def sequence_start(timeline, index):
    return sum(rules.played_frames(timeline, i) for i in range(index))


def _coverage(timeline):
    return {position(timeline, item): (item["left"], item["right"]) for item in timeline.replacements}


def geometry(timeline, bridge, context):
    """Where the replacement before `bridge["before"]` sits and what its run reads, with `problem` set when the
    surviving footage can't hold it."""
    index = position(timeline, bridge)
    left, right = bridge["left"], bridge["right"]
    join = sequence_start(timeline, index)
    shape = Geometry(index, join, left, right, left + right, join - left, join + right)
    name = f"the replacement before box {index + 1}"
    try:
        played_a, carried_a = rules.box_length(timeline, index - 1, context)
        played_b, _ = rules.box_length(timeline, index, context)
    except ValueError as error:
        shape.problem = str(error).removeprefix("H3 Timeline: ")
        return shape
    coverage = _coverage(timeline)
    taken_a = coverage.get(index - 1, (0, 0))[1]
    taken_b = coverage.get(index + 1, (0, 0))[0]
    kept_a, kept_b = played_a - taken_a - left, played_b - right - taken_b
    carried = canon_floor(min(context, carried_a + kept_a))
    frozen = canon_floor(min(context, kept_b))
    for kept, taken, number, neighbour, ends, minimum in (
            (kept_a, taken_a, index, index, carried, "carry"), (kept_b, taken_b, index + 1, index + 2, frozen, "freeze")):
        if kept < 1 and taken:
            shape.problem = (f"{name} overlaps the replacement before box {neighbour}: together they leave no frame "
                             f"of box {number}")
        elif kept < 1:
            shape.problem = f"{name} takes every frame of box {number}; leave at least one"
        elif ends is None:
            shape.problem = (f"{name} leaves {kept} frame{'' if kept == 1 else 's'} of box {number} beside it; H3 "
                             f"needs at least 5 to {minimum}")
        if shape.problem:
            return shape
    shape.context_frames, shape.ending_frames = carried, frozen
    shape.left_window = (index - 1, carried_a + played_a - left - carried, carried)
    shape.right_window = (index, right, frozen)
    shape.generated = carried + shape.frames + frozen
    return shape


def _seconds(frames):
    return f"{frames / FPS:.2f} s"


def _protection(timeline, shape, takes, projected):
    index, region = shape.index, (shape.start, shape.end)
    near = (shape.join - rules.played_frames(timeline, index - 1), shape.join + rules.played_frames(timeline, index))

    def overlaps(a, b, span):
        return a < span[1] and b > span[0]

    for item in projected:
        cue = item["cue"]
        speaker = cue.get("speaker", "").strip() or "A speaker"
        if item["state"] == "changed":
            clip = next(clip for clip in timeline.audio_clips if clip["slot"] == item["slot"])
            span = (dialogue.frame_floor(clip["start"]), dialogue.frame_ceil(clip["start"] + clip["duration"]))
            if overlaps(*span, near):
                return (f"@{item['slot']} changed since its cues were written: check cue {cue['id']!r} against the "
                        "new recording, or remove it")
            continue
        for a, b, portrayal in item["segments"]:
            if portrayal == "voiceover":
                continue
            if overlaps(a, b, region):
                what = "speaks on screen" if portrayal == "on_screen" else "has a line of unknown portrayal"
                return (f"{speaker} {what} from {_seconds(a)} to {_seconds(b)}, inside the region "
                        f"({_seconds(shape.start)} to {_seconds(shape.end)}): shorten or move the region, or mark "
                        "that part of the line as off-screen voiceover")
            if not item["aligned"] and overlaps(a, b, near):
                return (f"check cue {cue['id']!r} ({speaker}: {cue['text']!r}) against the recording before "
                        "replacing footage near it")
    positions = {box.id: i for i, box in enumerate(timeline.boxes)}
    for mark in dialogue.observed(timeline):
        i = positions.get(mark["box"])
        if i is None:
            continue
        first = sequence_start(timeline, i)
        span = (first + mark["start"], first + mark["end"])
        label = mark.get("label") or "observed footage"
        if overlaps(*span, near) and takes is not None and takes.get(mark["box"]) != mark["take"]:
            return (f"observed protection {label!r} was marked on an earlier take of box {i + 1}: mark it again on "
                    "this take, or remove it")
        if overlaps(*span, region):
            return (f"box {i + 1} has observed protection {label!r} from {_seconds(span[0])} to {_seconds(span[1])}, "
                    "inside the region: shorten or move the region")
    return ""


def check(timeline, bridge, context, takes=None, projected=None):
    """Why the replacement can't be confirmed or rendered as it stands, or "". `takes` maps box ids to their current
    take identity; without it observed protections count as current."""
    shape = geometry(timeline, bridge, context)
    if shape.problem:
        return shape.problem
    return _protection(timeline, shape, takes, dialogue.projected(timeline) if projected is None else projected)


def stand_in(timeline, index):
    """The replacement record at box `index`'s join, or an uncovered one."""
    box_id = timeline.boxes[index].id
    return next((item for item in timeline.replacements if item["before"] == box_id),
                {"before": box_id, "mode": "replace", "left": 0, "right": 0, "seed": 0, "prompt": ""})


def options(timeline, index, context, takes=None):
    """[[N, [left coverage that geometry and protection allow]]] for each replacement length."""
    bridge, projected = stand_in(timeline, index), dialogue.projected(timeline)
    return [[frames, [left for left in range(frames + 1)
                      if not check(timeline, {**bridge, "left": left, "right": frames - left}, context, takes, projected)]]
            for frames in rules.BRIDGE_FRAMES]


def proposal(timeline, index, context, takes=None, choices=None):
    """(N, left) to suggest: 29 frames before 12 and 46, split as evenly as allowed; None when nothing fits."""
    allowed = dict(choices if choices is not None else options(timeline, index, context, takes))
    for frames in (29, 12, 46):
        if allowed.get(frames):
            return frames, min(allowed[frames], key=lambda left: (abs(left - frames / 2), left))
    return None


def static_key(timeline, bridge, context, settings):
    """Everything a reviewed region depends on except the endpoint takes: its coverage and windows, the cues,
    protections and recordings around it and the node settings."""
    shape = geometry(timeline, bridge, context)
    span = (shape.start - shape.context_frames, shape.end + shape.ending_frames)
    cues = [{"id": item["id"], "state": item["state"], "key": dialogue.alignment_key(item["cue"]),
             "aligned": item["aligned"], "portrayal": item["cue"]["portrayal"], "segments": item["segments"]}
            for item in dialogue.projected(timeline)
            if item["state"] != "bound" or any(a < span[1] and b > span[0] for a, b, _ in item["segments"])]
    marks = [{key: mark.get(key) for key in ("id", "box", "take", "start", "end")} for mark in dialogue.observed(timeline)]
    clips = [{key: clip.get(key) for key in ("slot", "file", "start", "source_start", "duration", "locked", "in_full_video")}
             for clip in timeline.audio_clips if clip.get("locked") or clip.get("in_full_video")]
    return rules._digest({"boxes": [timeline.boxes[shape.index - 1].id, timeline.boxes[shape.index].id],
                          "join": shape.join, "left": shape.left, "right": shape.right,
                          "windows": [shape.left_window, shape.right_window], "problem": shape.problem,
                          "cues": cues, "observed": marks, "clips": clips,
                          "settings": {key: value for key, value in settings.items() if value is not None}})


def region_key(static, before, after):
    """The reviewed region's identity with the saved takes it reads (each {box, stamp} or None)."""
    return rules._digest([static, before, after])


def recipe(timeline, bridge):
    """What tells one candidate render from another of the same region."""
    from . import bridges
    return rules._digest({"prompt": bridges.prompt(timeline, bridge), "seed": bridge["seed"]})


def trims(timeline, active):
    """{box index: (frames cut from its start, frames cut from its end)} for the replacements in `active` (ids)."""
    result = {}
    for item in timeline.replacements:
        if item["before"] not in active:
            continue
        index = position(timeline, item)
        result[index - 1] = (result.get(index - 1, (0, 0))[0], item["left"])
        result[index] = (item["right"], result.get(index, (0, 0))[1])
    return result
