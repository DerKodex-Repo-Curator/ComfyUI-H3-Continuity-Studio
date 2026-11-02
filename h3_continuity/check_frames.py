"""The frames a continuity check looks at, and the drift measure: the mean CIELAB colour of a box's frames against its
scene's first box."""

import os

import av
import numpy as np

from . import media
from . import timeline as rules

LIGHTNESS_STEP = 10.0
COLOR_STEP = 8.0
MAX_SHOTS = 5
_SRGB_TO_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                         [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def shot_starts(source):
    """The shots' start_ms of a box's saved source, or None when it has no shots or a start isn't a whole number."""
    reply = source.get("reply") if isinstance(source, dict) else None
    shots = reply.get("shots") if isinstance(reply, dict) else None
    if not isinstance(shots, list) or not shots:
        return None
    starts = [shot.get("start_ms") if isinstance(shot, dict) else None for shot in shots]
    return starts if all(type(value) is int for value in starts) else None


def picks(source, frames, carried):
    """(shot, frame) pairs for a box of `frames` frames whose first `carried` replay the box before; `frame` counts the
    frames after the replay. The middle of each shot after the replay, by the shot's number from 1 (more than 5 give
    5, evenly chosen), then the last frame as shot 0. Without a usable source, 3 evenly spaced frames after the
    replay, the last of them the last frame. Shot times count the replay, as the source's do."""
    own = frames - carried
    starts = shot_starts(source)
    if starts is None:
        return [(0, -(-own * k // 3) - 1) for k in (1, 2, 3)]
    replay, end = round(carried * 1000 / rules.FPS), round(frames * 1000 / rules.FPS)
    middles = []
    for number, start in enumerate(starts, 1):
        stop = starts[number] if number < len(starts) else end
        start = max(start, replay)
        if stop > start:
            middles.append((number, min(max((start + stop) * rules.FPS // 2000 - carried, 0), own - 1)))
    if len(middles) > MAX_SHOTS:
        span, steps = len(middles) - 1, MAX_SHOTS - 1
        middles = [middles[(2 * k * span + steps) // (2 * steps)] for k in range(MAX_SHOTS)]
    if not middles or middles[-1][1] != own - 1:
        middles.append((0, own - 1))
    return middles


def read(folder, entry, picks):
    """The frames of `picks` from the manifest entry's segment video, in order; frame numbers scale by the video's
    fps over 24. Raises ValueError when the video can't be read."""
    video = entry["video"]
    count = video.get("frames") or 1
    indices = [min(count - 1, round(frame * video["fps"] / rules.FPS)) for _, frame in picks]
    try:
        found = media.read_frames(os.path.join(folder, video["file"]), indices)
    except (OSError, av.error.FFmpegError) as error:
        raise ValueError(f"{video['file']} can't be read: {error}") from None
    return [found[index] for index in indices]


def _lab(frame):
    """The mean CIELAB colour (D65) of an sRGB frame's pixels."""
    rgb = frame.reshape(-1, 3).astype(np.float64) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = linear @ _SRGB_TO_XYZ.T / _WHITE
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1).mean(axis=0)


def lab_mean(frames):
    """The mean CIELAB colour (L, a, b) of `frames`: each frame's pixels averaged in CIELAB, then the frames."""
    return np.mean([_lab(frame) for frame in frames], axis=0)


def drift_words(lab, first):
    """How the colour `lab` differs from its scene's first box's `first`: a shift of COLOR_STEP or more on the a*b*
    plane names its larger axis, and a lightness change of LIGHTNESS_STEP L* units or more reads in percent of the
    first box's lightness, as in "warmer and 12% darker"; "" below both."""
    lightness, da, db = lab[0] - first[0], lab[1] - first[1], lab[2] - first[2]
    words = []
    if np.hypot(da, db) >= COLOR_STEP:
        words.append(("warmer" if db > 0 else "cooler") if abs(db) >= abs(da) else ("redder" if da > 0 else "greener"))
    if abs(lightness) >= LIGHTNESS_STEP:
        percent = round(abs(lightness) / max(first[0], 1.0) * 100)
        words.append(f"{percent}% {'brighter' if lightness > 0 else 'darker'}")
    return " and ".join(words)


def scene_start(timeline, index):
    """The index of the box that starts box `index`'s scene: the nearest one at or before it that cuts to a new
    scene, else box 1."""
    while index > 0 and not (timeline.boxes[index].cut and timeline.boxes[index].new_scene):
        index -= 1
    return index
