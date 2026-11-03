"""ComfyUI nodes: H3 Sequence, H3 Continue and H3 Save Segment."""

import datetime
import os
import threading
from dataclasses import dataclass

import torch

import folder_paths
from comfy_api.latest import io, ui

from . import audio_tracks, bridges, latents, media, store, timing

CATEGORY = "H3 Continuity"
SequenceType = io.Custom("H3C_SEQUENCE")
SegmentType = io.Custom("H3C_SEGMENT")
# ponytail: serialize local saves/exports; use per-sequence locks if concurrent exports become common.
SEQUENCE_LOCK = threading.RLock()
# The Timeline hands H3 Save these record keys for this save only; saved entries never hold them.
UNSAVED = ("splice", "soundtrack", "export_error")


def sequences_root():
    return os.path.join(folder_paths.get_output_directory(), "h3_sequences")


@dataclass
class SequenceRef:
    name: str
    folder: str
    index: int
    base: dict | None
    video: torch.Tensor | None
    audio: torch.Tensor | None


@dataclass
class SegmentPlan:
    sequence: SequenceRef
    context_frames: int
    carried_ticks: int
    frames: int
    latent_size: tuple
    carried_video: torch.Tensor | None
    carried_audio: torch.Tensor | None
    description: str = ""
    timeline: dict | None = None
    preserve_following: bool = False
    ending_video: torch.Tensor | None = None
    ending_audio: torch.Tensor | None = None
    timeline_complete: bool = False
    carried_audio_start: int = 0


def _plural(count, word):
    return f"{word}{'s' if count != 1 else ''}"


def prepare_segment(sequence, latent, context_frames, carry_audio, positive=None, negative=None, node="H3 Continue", *, audio_context_frames=0):
    """Carries the end of the previous segment into `latent`. Returns the latent, the conditionings
    without guides inside the carried frames, the SegmentPlan for H3 Save Segment and the number of
    removed guides. Without a previous latent nothing is carried and `latent` is returned as is."""
    video, _ = latents.split_h3_latent(latent, node)
    frames = timing.frames_for_tokens(video.shape[2])
    size = tuple(video.shape[3:])
    if sequence.video is None:
        return latent, positive, negative, SegmentPlan(sequence, 0, 0, frames, size, None, None), 0
    context = int(context_frames)
    out, carried_video, carried_audio, ticks = latents.build_continuation(
        latent, sequence.video, sequence.audio, context, carry_audio, node=node, audio_context_frames=audio_context_frames)
    positive, removed_positive = latents.drop_guides_before(positive, context)
    negative, removed_negative = latents.drop_guides_before(negative, context)
    plan = SegmentPlan(sequence, context, ticks, frames, size, carried_video, carried_audio)
    plan.carried_audio_start = timing.ticks_for_frames(context) - ticks if ticks else 0
    return out, positive, negative, plan, max(removed_positive, removed_negative)


class H3C_Sequence(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="H3C_Sequence",
            hidden=[io.Hidden.extra_pnginfo],
            display_name="H3 Sequence",
            category=CATEGORY,
            description="Deprecated: use H3 Timeline. Picks the long-video sequence and the segment this run "
                        "continues. Connect sequence to H3 Continue and last_frame to your first-frame, reference "
                        "or prompt nodes.",
            is_deprecated=True,
            inputs=[
                io.String.Input("name", default="sequence", tooltip="Folder under output/h3_sequences."),
                io.Int.Input("continue_from", default=-1, min=-1, max=9999,
                             tooltip="-1 continues the latest segment. N continues segment N; saving replaces "
                                     "N+1 and later, keeping the old takes in takes/. 0 starts over as segment 1."),
                io.Image.Input("start_image", optional=True,
                               tooltip="Returned as last_frame when there is no previous segment, so segment 1 "
                                       "can use the same wiring."),
            ],
            outputs=[
                SequenceType.Output(display_name="sequence"),
                io.Image.Output(display_name="last_frame"),
                io.String.Output(display_name="previous_description"),
                io.String.Output(display_name="info"),
            ],
        )

    @classmethod
    def fingerprint_inputs(cls, name, continue_from, **kwargs):
        try:
            folder = store.sequence_dir(sequences_root(), name)
        except (AttributeError, ValueError):
            # a linked name arrives as None, so the manifest is unknown: always run rather than reuse a stale sequence
            return float("nan")
        return f"{store.manifest_fingerprint(folder)}:{continue_from}"

    @classmethod
    def execute(cls, name, continue_from, start_image=None) -> io.NodeOutput:
        from .timeline_api.service import authorize_sequence, sequence_owner
        authorize_sequence(name, sequence_owner(cls), "sequence")
        folder = store.sequence_dir(sequences_root(), name)
        name = os.path.basename(folder)
        manifest = store.load_manifest(folder)
        base, index = store.resolve_base(manifest, continue_from)
        video = audio = None
        description = ""
        if base is None:
            last_frame = start_image if start_image is not None else torch.zeros(1, 64, 64, 3)
        else:
            video, audio = store.load_segment_latents(folder, base)
            last_frame = store.load_last_frame(folder, base)
            if last_frame is None:
                width, height = latents.pixel_size(video)
                last_frame = torch.zeros(1, height, width, 3)
            description = base.get("description", "")
        count = len(manifest["segments"])
        info = f"sequence '{name}': "
        info += f"{count} {_plural(count, 'segment')}, {store.sequence_seconds(manifest):.1f} s. " if count else "new. "
        info += f"This run writes segment {index}" + (f", continuing from segment {base['index']}." if base else ".")
        if index <= count:
            moved = f"segments {index}-{count}" if count > index else f"segment {index}"
            info += f" Saving it moves {moved} to takes/."
        return io.NodeOutput(SequenceRef(name, folder, index, base, video, audio), last_frame, description, info)


class H3C_Continue(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="H3C_Continue",
            display_name="H3 Continue",
            category=CATEGORY,
            description="Deprecated: use H3 Timeline. Place between the H3 conditioning node and the sampler. "
                        "Copies the end of the previous segment's latent (video and audio) into the start of this "
                        "run and freezes it, so the new segment continues the motion and sound. On the first "
                        "segment it changes nothing.",
            is_deprecated=True,
            inputs=[
                SequenceType.Input("sequence"),
                io.Latent.Input("latent", tooltip="This run's H3 audio+video latent, e.g. from MiniMax H3 Image to "
                                                  "Video or Reference to Video."),
                io.Combo.Input("context_frames", options=list(timing.CONTEXT_OPTIONS), default="39",
                               tooltip="Frames carried from the previous segment: 39 = 1.6 s, 90 = 3.75 s, "
                                       "141 = 5.9 s. Longer carries more memory but leaves fewer new frames."),
                io.Boolean.Input("carry_audio", default=True,
                                 tooltip="Also carry and freeze the matching audio. Off: the whole soundtrack "
                                         "is generated fresh."),
                io.Conditioning.Input("positive", optional=True,
                                      tooltip="Guides that land inside the carried frames are removed."),
                io.Conditioning.Input("negative", optional=True),
                io.Int.Input('audio_context_frames', optional=True, default=0, min=0,
                             tooltip='Incoming audio context in 24 fps frames; 0 follows video. Longer requests are bounded to the video context. Ending pins stay full length.'),
            ],
            outputs=[
                io.Latent.Output(display_name="latent"),
                io.Conditioning.Output(display_name="positive"),
                io.Conditioning.Output(display_name="negative"),
                SegmentType.Output(display_name="segment"),
                io.String.Output(display_name="info"),
            ],
        )

    @classmethod
    def execute(cls, sequence, latent, context_frames, carry_audio, positive=None, negative=None, audio_context_frames=0) -> io.NodeOutput:
        out, positive, negative, plan, removed = prepare_segment(
            sequence, latent, context_frames, carry_audio, positive, negative, audio_context_frames=audio_context_frames)
        frames = plan.frames
        if sequence.video is None:
            info = (f"Segment {sequence.index}: first segment, nothing carried; "
                    f"{frames} frames ({timing.seconds(frames):.2f} s).")
            return io.NodeOutput(out, positive, negative, plan, info)
        context, ticks = plan.context_frames, plan.carried_ticks
        new = frames - context
        info = (f"Segment {sequence.index}: carrying the last {context} frames ({timing.seconds(context):.2f} s)"
                + (f" and {ticks} audio ticks" if ticks else ", video only")
                + f" of segment {sequence.base['index']}; {new} new frames ({timing.seconds(new):.2f} s).")
        if removed:
            info += f" Removed {removed} {_plural(removed, 'guide')} inside the carried frames."
        if plan.carried_audio_start:
            info += f" Audio frozen at target ticks {plan.carried_audio_start}–{plan.carried_audio_start + ticks}."
        return io.NodeOutput(out, positive, negative, plan, info)


class H3C_SaveSegment(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="H3C_SaveSegment",
            hidden=[io.Hidden.extra_pnginfo],
            display_name="H3 Save Segment",
            category=CATEGORY,
            description="Saves this run as the next segment of the sequence: the latent for the next run and the "
                        "finished video without the repeated frames. Then rebuilds the full video.",
            is_output_node=True,
            inputs=[
                SegmentType.Input("segment"),
                io.Latent.Input("latent", tooltip="The sampler's output latent."),
                io.Image.Input("images", optional=True,
                               tooltip="Finished frames of this run, after any upscaling or grading. Needed for "
                                       "the segment and full videos."),
                io.Audio.Input("audio", optional=True, tooltip="Decoded audio of this run."),
                io.Float.Input("fps", default=24.0, min=1.0, max=240.0, step=0.001,
                               tooltip="Frame rate of images: 24 unless you interpolate."),
                io.String.Input("description", optional=True, force_input=True,
                                tooltip="Text stored with the segment and returned by H3 Sequence as "
                                        "previous_description, such as the prompt."),
                io.Boolean.Input("write_full_video", default=True,
                                 tooltip="Rebuild after each H3 Sequence segment. H3 Timeline exports when all current boxes finish."),
                io.Int.Input("crf", default=16, min=0, max=51,
                             tooltip="H.264 quality of the saved videos; lower is better and larger."),
                io.Combo.Input("color_space", options=["sRGB", "HDR", "HDR PQ"], default="sRGB", optional=True,
                               tooltip="Colorspace of the finished frames. HDR videos use 10-bit BT.2020."),
            ],
            outputs=[io.String.Output(display_name="info")],
        )

    @classmethod
    def execute(cls, segment, latent, fps, write_full_video, crf, images=None, audio=None, description="", color_space="sRGB") -> io.NodeOutput:
        sequence = segment.sequence
        from .timeline_api.service import authorize_sequence, sequence_owner
        authorize_sequence(sequence.name, sequence_owner(cls), "save_segment")
        video, audio_latent = latents.split_h3_latent(latent, "H3 Save Segment")
        frames = timing.frames_for_tokens(video.shape[2])
        if frames != segment.frames or tuple(video.shape[3:]) != segment.latent_size:
            raise ValueError(f"H3 Save Segment: this latent ({frames} frames) does not match the one H3 Continue or "
                             f"H3 Timeline prepared ({segment.frames} frames). Connect the output of the sampler that "
                             "received its latent.")
        notes = []
        if video.shape[0] > 1:
            notes.append(f"Batch of {video.shape[0]}: saved the first item only.")
        video, audio_latent = video[:1], audio_latent[:1]
        drift = latents.carried_difference(video, audio_latent, segment.carried_video, segment.carried_audio,
                                          audio_start=segment.carried_audio_start)
        drift = max(drift, latents.carried_difference(video, audio_latent, segment.ending_video,
                                                    segment.ending_audio, at_end=True))
        if drift > 1e-3:
            notes.append(f"Warning: the carried frames changed during sampling (max difference {drift:.3g}). "
                         "Make sure the sampler gets its latent from H3 Continue or H3 Timeline.")
        waveform = sample_rate = None
        if audio is not None:
            waveform, sample_rate = audio["waveform"][0, :2].float().cpu(), int(audio["sample_rate"])
        if "bridge" in (segment.timeline or {}):
            return cls.save_bridge(segment, video, audio_latent, frames, fps, crf, images, waveform, sample_rate,
                                   description, notes, color_space)
        if "replacement" in (segment.timeline or {}):
            return cls.save_replacement(segment, video, audio_latent, frames, fps, crf, images, waveform, sample_rate,
                                        description, notes, color_space)

        with SEQUENCE_LOCK:
            authorize_sequence(sequence.name, sequence_owner(cls), "save_segment")
            now = datetime.datetime.now()
            folder = sequence.folder
            os.makedirs(folder, exist_ok=True)
            manifest = store.load_manifest(folder)
            manifest.pop("full_video", None)
            archived = store.archive_from(folder, manifest, sequence.index, now, only=segment.preserve_following)
            context = segment.context_frames
            width, height = latents.pixel_size(video)
            entry = {
                "index": sequence.index, "stem": store.stem(sequence.index), "frames": frames,
                "context_frames": context, "carried_audio": segment.carried_ticks > 0,
                "latent_width": width, "latent_height": height, "video": None, "audio_sample_rate": sample_rate,
                "description": description or segment.description or "", "created": now.isoformat(timespec="seconds"),
            }
            if segment.carried_audio_start:
                entry['audio_pin'] = {'start_tick': segment.carried_audio_start, 'ticks': segment.carried_ticks}
            if segment.timeline:
                entry["timeline"] = {key: value for key, value in segment.timeline.items() if key not in UNSAVED}
            # A box that drops generated frames plays only its first `played` new frames; its latent keeps them all.
            played = (segment.timeline or {}).get("played")
            if played is not None:
                entry["played"] = played
            if images is not None:
                _write_video(folder, entry, images, fps, crf, waveform, sample_rate, notes, color_space)
            store.save_segment(folder, entry, video, audio_latent, waveform)
            manifest["segments"].append(entry)
            manifest["segments"].sort(key=lambda e: e["index"])
            # The Timeline lists its bridges in `splice`; a Timeline record without it lists none.
            keys = (segment.timeline or {}).get("splice", {})
            if segment.timeline:
                bridges.keep(folder, manifest, keys, now)
            store.write_manifest(folder, manifest)
            spliced = bridges.spliced(folder, manifest, keys) if keys else []

            new = store.played_frames(entry)
            count = len(manifest["segments"])
            info = (f"Saved segment {sequence.index} of '{sequence.name}': {new} new frames ({timing.seconds(new):.2f} s). "
                    f"Sequence: {count} {_plural(count, 'segment')}, {store.sequence_seconds(manifest, spliced):.1f} s.")
            if archived:
                info += f" Moved {_plural(len(archived), 'segment')} {', '.join(map(str, archived))} to takes/."
            if (write_full_video and not segment.timeline) or segment.timeline_complete:
                info += " " + ((segment.timeline or {})['export_error'] if (segment.timeline or {}).get('export_error') else
                               rebuild_full_video(folder, sequence.name, manifest, crf, spliced,
                                                 (segment.timeline or {}).get("soundtrack", ()), managed_owner=sequence_owner(cls)))
            if notes:
                info += " " + " ".join(notes)
            return io.NodeOutput(info, ui=ui.PreviewText(info))

    @classmethod
    def save_bridge(cls, segment, video, audio_latent, frames, fps, crf, images, waveform, sample_rate, description,
                    notes, color_space="sRGB"):
        """Saves a bridge run beside the segments, moving only the bridge's own earlier take."""
        sequence, record = segment.sequence, segment.timeline
        from .timeline_api.service import authorize_sequence, sequence_owner
        keys = record.get("splice", {})
        with SEQUENCE_LOCK:
            authorize_sequence(sequence.name, sequence_owner(cls), "save_segment")
            now = datetime.datetime.now()
            folder = sequence.folder
            os.makedirs(folder, exist_ok=True)
            manifest = store.load_manifest(folder)
            manifest.pop("full_video", None)
            earlier = bridges.saved(manifest, record["bridge"])
            if earlier is not None:
                bridges.archive(folder, manifest, earlier, now)
            width, height = latents.pixel_size(video)
            entry = {
                "box": record["bridge"], "stem": bridges.stem(record["bridge"]), "frames": frames,
                "context_frames": segment.context_frames, "carried_audio": segment.carried_ticks > 0,
                "latent_width": width, "latent_height": height, "video": None, "audio_sample_rate": sample_rate,
                "description": description or segment.description or "", "created": now.isoformat(timespec="seconds"),
                "timeline": {key: value for key, value in record.items() if key not in UNSAVED}, "played": record["played"],
            }
            if segment.carried_audio_start:
                entry['audio_pin'] = {'start_tick': segment.carried_audio_start, 'ticks': segment.carried_ticks}
            if images is not None:
                _write_video(folder, entry, images, fps, crf, waveform, sample_rate, notes, color_space)
            store.save_segment(folder, entry, video, audio_latent, waveform)
            manifest.setdefault("bridges", []).append(entry)
            bridges.keep(folder, manifest, keys, now)
            store.write_manifest(folder, manifest)

            played = entry["played"]
            info = (f"Saved the bridge before box {sequence.index} of '{sequence.name}': {played} new frames "
                    f"({timing.seconds(played):.2f} s).")
            if earlier is not None:
                info += " Moved its earlier take to takes/."
            if segment.timeline_complete:
                info += " " + (record['export_error'] if record.get('export_error') else
                               rebuild_full_video(folder, sequence.name, manifest, crf, bridges.spliced(folder, manifest, keys),
                                                 record.get("soundtrack", ()), managed_owner=sequence_owner(cls)))
            if notes:
                info += " " + " ".join(notes)
            return io.NodeOutput(info, ui=ui.PreviewText(info))


    @classmethod
    def save_replacement(cls, segment, video, audio_latent, frames, fps, crf, images, waveform, sample_rate,
                         description, notes, color_space="sRGB"):
        """Saves a replacement candidate beside the earlier ones; nothing is moved and nothing is selected."""
        from . import replacement_candidates
        sequence, record = segment.sequence, segment.timeline
        from .timeline_api.service import authorize_sequence, sequence_owner
        with SEQUENCE_LOCK:
            authorize_sequence(sequence.name, sequence_owner(cls), "save_segment")
            now = datetime.datetime.now()
            folder = sequence.folder
            os.makedirs(folder, exist_ok=True)
            manifest = store.load_manifest(folder)
            box = record["replacement"]
            taken = {entry.get("candidate") for entry in replacement_candidates.entries(manifest, box)}
            salt, candidate = 0, None
            while candidate is None or candidate in taken:
                candidate = replacement_candidates.candidate_id(box, f"{now.isoformat()}#{salt}", record["seed"],
                                                                record["region"])
                salt += 1
            width, height = latents.pixel_size(video)
            entry = {
                "box": box, "candidate": candidate, "stem": replacement_candidates.stem(box, candidate),
                "frames": frames, "context_frames": segment.context_frames, "carried_audio": segment.carried_ticks > 0,
                "latent_width": width, "latent_height": height, "video": None, "audio_sample_rate": sample_rate,
                "description": description or segment.description or "", "created": now.isoformat(timespec="seconds"),
                "timeline": {**{key: value for key, value in record.items() if key not in UNSAVED},
                             "candidate": candidate},
                "played": record["played"],
            }
            if segment.carried_audio_start:
                entry['audio_pin'] = {'start_tick': segment.carried_audio_start, 'ticks': segment.carried_ticks}
            if images is not None:
                _write_video(folder, entry, images, fps, crf, waveform, sample_rate, notes, color_space)
            store.save_segment(folder, entry, video, audio_latent, waveform)
            replacement_candidates.add(manifest, entry)
            store.write_manifest(folder, manifest)
            info = (f"Saved replacement candidate {candidate} before box {sequence.index} of '{sequence.name}': "
                    f"{entry['played']} frames ({timing.seconds(entry['played']):.2f} s) in place of the same number. "
                    "Select it in the Studio to play it in the full video.")
            if images is None:
                info += " No images were connected, so it has no video to review or play."
            if notes:
                info += " " + " ".join(notes)
            return io.NodeOutput(info, ui=ui.PreviewText(info))


def _write_video(folder, entry, images, fps, crf, waveform, sample_rate, notes, color_space="sRGB"):
    """Writes the video of the entry's new frames, without the carried ones, and its last frame."""
    context, frames, played = entry["context_frames"], entry["frames"], entry.get("played")
    trim = timing.frames_at_fps(context, fps)
    if images.shape[0] <= trim:
        raise ValueError(f"H3 Save Segment: got {images.shape[0]} images, but the first {trim} repeat the "
                         "previous segment. Connect all frames of this run.")
    expected = timing.frames_at_fps(frames - context, fps)
    new_images = images[trim:]
    if new_images.shape[0] != expected:
        fix = "repeated the last frame" if new_images.shape[0] < expected else "dropped the extra frames"
        notes.append(f"{new_images.shape[0]} new images for {expected} frames: {fix}.")
        new_images = media.fit_frame_count(new_images, expected)
    last_image = images[-1]
    end_sample = None
    if played is not None:
        expected = max(1, timing.frames_at_fps(played, fps))
        new_images = new_images[:expected]
        last_image = new_images[-1]
        if waveform is not None:
            end_sample = timing.sample_at_frame(context + played, sample_rate)
    segment_audio = None
    if waveform is not None:
        segment_audio = (waveform[:, timing.sample_at_frame(context, sample_rate):end_sample], sample_rate)
    file = entry["stem"] + ".mp4"
    encoded = media.write_segment_video(os.path.join(folder, file), new_images, fps, crf, segment_audio, color_space=color_space)
    store.save_last_frame(folder, entry, last_image)
    entry["video"] = {"file": file, "fps": fps, "width": encoded[0], "height": encoded[1], "frames": expected,
                      "color_space": color_space}


def _not_rebuilt(error):
    return f"Full video not rebuilt: {str(error).removeprefix('H3 Timeline: ').rstrip('.')}."


def rebuild_full_video(folder, name, manifest, crf, spliced=(), soundtrack=(), *, managed_owner=None):
    """Joins the saved segments, each `spliced` bridge before the segment of its box. With `soundtrack` clips
    (`audio_tracks.marked`), it plays them instead of the segments' audio."""
    with SEQUENCE_LOCK:
        from .timeline_api.service import authorize_sequence
        authorize_sequence(name, managed_owner, "full_video")
        segments = manifest["segments"]
        manifest.pop("full_video", None)
        store.write_manifest(folder, manifest)
        if not segments:
            return "Full video not rebuilt: no segments are saved."
        if [e["index"] for e in segments] != list(range(1, len(segments) + 1)):
            return "Full video not rebuilt: generate the missing earlier boxes first."
        missing = [str(e["index"]) for e in segments if not e.get("video")]
        if missing:
            return (f"Full video not rebuilt: {_plural(len(missing), 'segment')} {', '.join(missing)} "
                    f"{'has' if len(missing) == 1 else 'have'} no saved frames (connect images).")
        try:
            sources = audio_tracks.soundtrack_sources(soundtrack)
        except ValueError as error:
            return _not_rebuilt(error)
        fingerprint = store.full_video_fingerprint(folder, manifest, spliced, sources)
        if fingerprint is None:
            return "Full video not rebuilt: a segment video or audio source is missing."
        leading = {entry["box"]: entry for entry in spliced}
        ordered = []
        for entry in segments:
            box_id = (entry.get("timeline") or {}).get("box")
            if box_id in leading:
                ordered.append(leading[box_id])
            ordered.append(entry)
        if soundtrack:
            try:
                audio = audio_tracks.soundtrack_audio(soundtrack, [(store.played_frames(e), "box" in e) for e in ordered])
            except ValueError as error:
                return _not_rebuilt(error)
        else:
            parts = [(e["context_frames"] + store.played_frames(e), e["context_frames"],
                      store.load_waveform(folder, e) if e.get("audio_sample_rate") else None, e.get("audio_sample_rate"))
                     for e in ordered]
            audio = media.assemble_audio(parts)
        written, note = media.build_full_video(os.path.join(folder, f"{name}_full.mp4"),
                                               [os.path.join(folder, e["video"]["file"]) for e in ordered], audio, crf)
        if written is None:
            return note
        manifest["full_video"] = {"file": os.path.basename(written), "sources": fingerprint}
        store.write_manifest(folder, manifest)
        heard = f", with the soundtrack from {audio_tracks.named(soundtrack)}" if soundtrack else ""
        return f"Full video: {written}{heard}." + (f" {note}" if note else "")
