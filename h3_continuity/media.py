"""Segment videos and full-movie assembly with PyAV."""

import datetime
import os
from fractions import Fraction

import av
import numpy as np
import torch

from comfy_api.latest._input_impl.video_types import set_video_color_properties, video_stream_color_space

from .timing import sample_at_frame

AUDIO_BIT_RATE = 192000
CROSSFADE_SECONDS = 0.1


def _layout(channels):
    return "mono" if channels == 1 else "stereo"


def fit_frame_count(images, count):
    """Drop extra frames or repeat the last one so `images` has exactly `count` frames."""
    if images.shape[0] >= count:
        return images[:count]
    return torch.cat([images, images[-1:].expand(count - images.shape[0], -1, -1, -1)])


def _add_video_stream(container, fps, width, height, crf, color_space="sRGB"):
    stream = container.add_stream("libx264", rate=Fraction(fps).limit_denominator(1001))
    stream.width, stream.height = width, height
    stream.pix_fmt = "yuv420p10le" if color_space in ("HDR", "HDR PQ") else "yuv420p"
    set_video_color_properties(stream.codec_context, color_space)
    stream.options = {"crf": str(crf), "preset": "medium"}
    # decode order must equal presentation order so segments can be joined by packet copy
    stream.codec_context.max_b_frames = 0
    return stream


def _add_audio_stream(container, waveform, sample_rate):
    stream = container.add_stream("aac", rate=sample_rate, layout=_layout(waveform.shape[0]))
    stream.bit_rate = AUDIO_BIT_RATE
    return stream


def _mux_audio(container, stream, waveform, sample_rate):
    frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(waveform.float().cpu().numpy()), format="fltp",
                                       layout=_layout(waveform.shape[0]))
    frame.sample_rate = sample_rate
    frame.pts = 0
    container.mux(stream.encode(frame))
    container.mux(stream.encode(None))


def write_segment_video(path, images, fps, crf, audio=None, color_space="sRGB", size=None):
    """Encode `images` ([N, H, W, C], 0-1) with optional `audio` = (waveform [C, S], sample_rate).
    Returns the encoded (width, height); odd sizes are padded by one edge pixel, unless `size` = (width, height)
    scales every frame to it."""
    height, width = images.shape[1], images.shape[2]
    pad_h, pad_w = (0, 0) if size else (height % 2, width % 2)
    out_width, out_height = size or (width + pad_w, height + pad_h)
    hdr = color_space in ("HDR", "HDR PQ")
    with av.open(path, mode="w") as container:
        video_stream = _add_video_stream(container, fps, out_width, out_height, crf, color_space)
        audio_stream = _add_audio_stream(container, *audio) if audio is not None else None
        for image in images:
            array = (image[..., :3].float().clamp(0, 1) * (65535 if hdr else 255)).round().cpu().numpy().astype(np.uint16 if hdr else np.uint8)
            if pad_h or pad_w:
                array = np.pad(array, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
            frame = av.VideoFrame.from_ndarray(array, format="rgb48le" if hdr else "rgb24")
            frame = frame.reformat(width=out_width, height=out_height, format=video_stream.pix_fmt,
                                   dst_colorspace=video_stream.codec_context.colorspace)
            set_video_color_properties(frame, color_space)
            container.mux(video_stream.encode(frame))
        container.mux(video_stream.encode(None))
        if audio_stream is not None:
            _mux_audio(container, audio_stream, *audio)
    return out_width, out_height


def read_frames(path, indices):
    """The frames at `indices` of the video at `path`, as RGB uint8 arrays by index, decoded in order up to the last
    one wanted. An index past the end gets the last frame."""
    wanted = set(indices)
    end = max(wanted)
    found, last = {}, None
    with av.open(path) as container:
        for number, frame in enumerate(container.decode(video=0)):
            if number in wanted:
                found[number] = frame.to_ndarray(format="rgb24")
            if number >= end:
                break
            last = frame
        if wanted - found.keys():
            if last is None:
                raise ValueError(f"{os.path.basename(path)} has no frames")
            final = last.to_ndarray(format="rgb24")
            found.update({index: final for index in wanted - found.keys()})
    return found


def assemble_audio(parts, crossfade_seconds=CROSSFADE_SECONDS):
    """Join segment audio on the 24 fps timeline.

    `parts` holds (frames, context_frames, waveform [C, S] or None, sample_rate or None) per segment.
    Each segment fills the span of its new frames from its own waveform, starting after its carried
    frames, and fades in over the end of the previous segment from its own decode of that moment.
    Returns (waveform, sample_rate), or None when no segment has audio."""
    with_audio = [(waveform, rate) for _, _, waveform, rate in parts if waveform is not None]
    if not with_audio:
        return None
    sample_rate = with_audio[0][1]
    channels = min(2, max(waveform.shape[0] for waveform, _ in with_audio))
    out = torch.zeros(channels, sample_at_frame(sum(f - c for f, c, _, _ in parts), sample_rate))
    position = 0
    for index, (frames, context, waveform, rate) in enumerate(parts):
        start = sample_at_frame(position, sample_rate)
        position += frames - context
        end = sample_at_frame(position, sample_rate)
        if waveform is None:
            continue
        waveform = waveform.float().cpu()
        if rate != sample_rate:
            import comfy.audio
            waveform = comfy.audio.resample(waveform, rate, sample_rate)
        waveform = waveform[:channels] if waveform.shape[0] >= channels else waveform.repeat(channels, 1)
        local = sample_at_frame(context, sample_rate)
        piece = waveform[:, local:local + end - start]
        out[:, start:start + piece.shape[1]] = piece
        fade = min(round(crossfade_seconds * sample_rate), local, start) if index and waveform.shape[1] >= local else 0
        if fade > 0:
            ramp = torch.linspace(0, 1, fade)
            out[:, start - fade:start] = out[:, start - fade:start] * (1 - ramp) + waveform[:, local - fade:local] * ramp
    return out, sample_rate


def _signature(path):
    with av.open(path) as container:
        stream = container.streams.video[0]
        context = stream.codec_context
        return (context.name, bytes(context.extradata or b""), context.width, context.height, stream.average_rate,
                video_stream_color_space(stream) or "sRGB")


def _replace(temporary, path):
    try:
        os.replace(temporary, path)
        return path, ""
    except PermissionError:
        alternative = "{}_{}.mp4".format(os.path.splitext(path)[0], datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.replace(temporary, alternative)
        return alternative, f"{os.path.basename(path)} is open in another program, so this version is {os.path.basename(alternative)}."


def build_full_video(path, videos, audio, crf, size=None):
    """Concatenate segment videos into `path` with `audio` = (waveform, sample_rate) or None. Each video is a path, or
    (path, first frame, frames) for a window of it. With `size` = (width, height), videos of other sizes are scaled to
    it instead of refused.
    Packets are copied when every file has the same encoding and every window starts at its first frame (segments
    have no B-frames, so a prefix is its first packets); otherwise the frames are re-encoded.
    Returns (written path or None, note)."""
    windows = [(video, 0, None) if isinstance(video, str) else tuple(video) for video in videos]
    signatures = [_signature(video) for video, _, _ in windows]
    first = signatures[0]
    if any(signature[4] != first[4] or (size is None and signature[2:4] != first[2:4]) for signature in signatures):
        return None, "Full video skipped: the segment videos differ in size or frame rate."
    if any(signature[5] != first[5] for signature in signatures):
        return None, "Full video skipped: the segment videos differ in color space."
    width, height = size or first[2:4]
    copy = (all(signature[:2] == first[:2] and signature[2:4] == (width, height) for signature in signatures)
            and all(start == 0 for _, start, _ in windows))
    temporary = path + ".tmp.mp4"
    with av.open(windows[0][0]) as template, av.open(temporary, mode="w") as container:
        color_space = first[5]
        if copy:
            video_stream = container.add_stream_from_template(template.streams.video[0], opaque=True)
        else:
            video_stream = _add_video_stream(container, first[4], width, height, crf, color_space)
        audio_stream = _add_audio_stream(container, *audio) if audio is not None else None
        offset, encoded = Fraction(0), 0
        for video, start, frames in windows:
            end = None if frames is None else start + frames
            with av.open(video) as source_container:
                source = source_container.streams.video[0]
                if not copy:
                    for number, frame in enumerate(source_container.decode(source)):
                        if end is not None and number >= end:
                            break
                        if number >= start:
                            if (frame.width, frame.height) != (width, height):
                                frame = frame.reformat(width=width, height=height)
                            # a decoded frame keeps its source time base, so numbering it there collapses the times
                            frame.pts, frame.time_base = encoded, 1 / first[4]
                            encoded += 1
                            container.mux(video_stream.encode(frame))
                    continue
                origin, count = None, 0
                for packet in source_container.demux(source):
                    if packet.pts is None or packet.size == 0:
                        continue
                    if end is not None and count >= end:
                        break
                    if origin is None:
                        origin = packet.pts
                    shift = offset / packet.time_base - origin
                    packet.pts = round(packet.pts + shift)
                    packet.dts = round(packet.dts + shift) if packet.dts is not None else packet.pts
                    packet.stream = video_stream
                    container.mux(packet)
                    count += 1
                offset += Fraction(count) / source.average_rate
        if not copy:
            container.mux(video_stream.encode(None))
        if audio_stream is not None:
            _mux_audio(container, audio_stream, *audio)
    written, note = _replace(temporary, path)
    if not copy:
        note = ("Segment encodings differ, so the full video was re-encoded. " + note).strip()
    return written, note
