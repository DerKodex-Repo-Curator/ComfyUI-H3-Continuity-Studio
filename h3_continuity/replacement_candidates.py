"""Saved replacement candidates: renders of a reviewed region kept beside the boxes, never moved or chosen on their
own. A candidate plays only while the Timeline selects it and its region is still the one it was rendered for."""

import hashlib
import os
from dataclasses import dataclass, field

from . import bridges, replacement, store
from . import timeline as rules


@dataclass
class State:
    bridge: dict
    index: int
    # problem | waiting | review | pending | next | done
    status: str
    note: str
    geometry: replacement.Geometry
    region: str | None
    recipe: str
    # Each {"entry", "state": current | stale | missing}, oldest first.
    candidates: list = field(default_factory=list)
    # none | current | stale | missing
    selected: str = "none"
    options: list = field(default_factory=list)
    proposal: tuple | None = None


def stem(box_id, candidate):
    return "replace@" + bridges.stem(box_id).removeprefix("bridge@") + "-" + candidate


def candidate_id(box_id, created, seed, region):
    return hashlib.sha1(f"{box_id}\n{created}\n{seed}\n{region}".encode("utf-8")).hexdigest()[:8]


def add(manifest, entry):
    manifest.setdefault("replacements", []).append(entry)


def entries(manifest, box_id):
    return [entry for entry in manifest.get("replacements", []) if entry.get("box") == box_id]


def take_id(folder, entry):
    """A saved box take's identity: its latent file's stamp, or None without one."""
    if entry is None or not store.has_segment_latents(folder, entry):
        return None
    return "-".join(str(value) for value in store.latent_stamp(folder, entry))


def takes(folder, timeline, manifest):
    """{box id: take identity} for the boxes saved at their own position."""
    result = {}
    for entry in manifest["segments"]:
        index = entry["index"] - 1
        if 0 <= index < len(timeline.boxes) and (entry.get("timeline") or {}).get("box") == timeline.boxes[index].id:
            result[timeline.boxes[index].id] = take_id(folder, entry)
    return result


def candidate_state(folder, entry, region):
    video = entry.get("video")
    if not video or not os.path.isfile(os.path.join(folder, video["file"])):
        return "missing"
    return "current" if region is not None and (entry.get("timeline") or {}).get("region") == region else "stale"


def states(folder, timeline, manifest, done, known, context):
    """Each replacement's State in Timeline order; `done` holds the indices of the boxes that are done. The first
    pending replacement is next once every box is done."""
    segments = {entry["index"]: entry for entry in manifest["segments"]}
    current_takes = takes(folder, timeline, manifest)
    found = []
    for bridge in timeline.replacements:
        index = replacement.position(timeline, bridge)
        shape = replacement.geometry(timeline, bridge, context)
        trouble = replacement.check(timeline, bridge, context, current_takes)
        links = [bridges.link(folder, segments.get(n)) for n in (index, index + 1)]
        region = None
        if all(links) and [link["box"] for link in links] == [timeline.boxes[index - 1].id, timeline.boxes[index].id]:
            region = replacement.region_key(replacement.static_key(timeline, bridge, context, known), *links)
        recipe = replacement.recipe(timeline, bridge)
        saved = [{"entry": entry, "state": candidate_state(folder, entry, region)}
                 for entry in entries(manifest, bridge["before"])]
        chosen = bridge.get("selected")
        selected = "none"
        if chosen:
            match = next((item for item in saved if item["entry"].get("candidate") == chosen), None)
            selected = match["state"] if match else "missing"
        waiting = [n for n in (index, index + 1) if n - 1 not in done]
        if trouble:
            status, note = "problem", trouble
        elif waiting or region is None:
            status, note = "waiting", f"render {' and '.join(f'box {n}' for n in waiting or (index, index + 1))} first"
        elif bridge.get("review") != region:
            status = "review"
            note = ("confirm the region again: its footage, cues or settings changed since you confirmed it"
                    if bridge.get("review") else "confirm the region before rendering a candidate")
        elif any(item["state"] == "current" and (item["entry"].get("timeline") or {}).get("recipe") == recipe
                 for item in saved):
            status, note = "done", ""
        else:
            status, note = "pending", ""
        found.append(State(bridge, index, status, note, shape, region, recipe, saved, selected))
    if len(done) == len(timeline.boxes):
        upcoming = next((state for state in found if state.status == "pending"), None)
        if upcoming:
            upcoming.status = "next"
    return found


def active(found):
    """{box id: candidate entry} for the replacements whose selected candidate plays in the full video."""
    result = {}
    for state in found:
        if state.selected == "current":
            result[state.bridge["before"]] = next(item["entry"] for item in state.candidates
                                                  if item["entry"].get("candidate") == state.bridge["selected"])
    return result


def prepare(state, latent, positive, negative, sequence, before, after, vae, carry_audio, *, audio_context_frames=0):
    """The candidate's `latent` with the surviving footage carried at its start and frozen at its end, and its
    SegmentPlan. `sequence` is (name, folder, index, base entry); `before` and `after` are the two boxes' saved
    (video, audio) latents."""
    from . import latents, nodes as continuity
    shape = state.geometry
    carried = latents.window(*before, shape.left_window[1], shape.context_frames, vae)
    reference = continuity.SequenceRef(*sequence, *carried)
    latent, positive, negative, segment, _ = continuity.prepare_segment(
        reference, latent, shape.context_frames, carry_audio, positive, negative, node="H3 Timeline",
        audio_context_frames=audio_context_frames)
    frozen = latents.window(*after, shape.right_window[1], shape.ending_frames, vae)
    latent, segment.ending_video, segment.ending_audio = latents.build_ending(
        latent, *frozen, shape.ending_frames, carry_audio, segment.context_frames)
    positive, _ = latents.drop_guides_before(positive, 0, segment.frames - shape.ending_frames)
    negative, _ = latents.drop_guides_before(negative, 0, segment.frames - shape.ending_frames)
    segment.preserve_following = True
    return latent, positive, negative, segment


def plan(timeline, state, width, height, context, carry_audio, *, audio_context_frames=0):
    """The run that renders a candidate: T2VA without references, between C' carried and E' frozen frames."""
    bridge, shape = state.bridge, state.geometry
    stand_in = rules.Box(bridge["before"], shape.frames, bridge["prompt"], bridge["seed"], True, "", "")
    settings = bridges.settings(width, height, context, carry_audio, audio_context_frames=audio_context_frames)
    return rules.BoxPlan(state.index, stand_in, False, shape.frames, shape.context_frames, shape.generated,
                         rules.Slots("t2va", [], [], "", "", {}), bridges.prompt(timeline, bridge), state.recipe,
                         settings, [])
