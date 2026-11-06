"""Non-destructive source windows owned by stable box IDs. Times are half-open seconds."""

import copy
import math

FEATURE = 'box-audio-windows-1'
KEYS = ('start', 'source_start', 'duration')


def _number(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError('H3 Timeline: audio windows need finite nonnegative times and positive durations')


def validate(clip, boxes, origin):
    if 'box_windows' not in clip:
        return
    saved = clip['box_windows']
    if not isinstance(saved, dict) or type(saved.get('version')) is not int or saved['version'] != 1:
        raise ValueError('H3 Timeline: unsupported audio windows version')
    if saved.get('source') != origin or saved.get('placement') != {key: clip[key] for key in KEYS}:
        raise ValueError('H3 Timeline: unlock audio windows before changing the source or placement')
    bindings = saved.get('by_box')
    if not isinstance(bindings, dict):
        raise ValueError('H3 Timeline: audio windows need a box mapping')
    ids = {box['id'] for box in boxes}
    for box_id, window in bindings.items():
        if box_id not in ids or not isinstance(window, dict):
            raise ValueError('H3 Timeline: audio window refers to an unknown box')
        for key in ('offset', 'source_start', 'duration'):
            _number(window.get(key), key == 'duration')
        if window['source_start'] < clip['source_start'] - 1e-9 or window['source_start'] + window['duration'] > clip['source_start'] + clip['duration'] + 1e-9:
            raise ValueError('H3 Timeline: audio window is outside its captured source selection')


def capture(clip, boxes, origin):
    bindings = {}
    for box in boxes:
        first, last = max(box['start'], clip['start']), min(box['start'] + box['duration'], clip['start'] + clip['duration'])
        if last > first:
            bindings[box['id']] = dict(offset=first - box['start'], source_start=clip['source_start'] + first - clip['start'], duration=last-first)
    return dict(version=1, source=copy.deepcopy(origin), placement={key: clip[key] for key in KEYS}, by_box=bindings)


def resolve(clip, boxes):
    if 'box_windows' not in clip:
        return [dict(box=None, offset=0, **{key: clip[key] for key in KEYS})]
    result = []
    for box in boxes:
        window = clip['box_windows']['by_box'].get(box['id'])
        if window:
            duration = min(window['duration'], box['duration'] - window['offset'])
            if duration > 0:
                result.append({**window, 'box': box['id'], 'start': box['start'] + window['offset'], 'duration': duration})
    return result
