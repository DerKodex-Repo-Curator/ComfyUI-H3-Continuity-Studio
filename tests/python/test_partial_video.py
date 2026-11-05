import os
import shutil
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest import mock

import av
import torch

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

from h3_continuity import audio_tracks, media, partial_video, store, timeline_node  # noqa: E402
from h3_continuity.timeline_api import artifacts  # noqa: E402

from .helpers import box, clip, parse  # noqa: E402

RATE = 8000
SEGMENT_SIZE = 64
SOURCE_SIZE = 32


def coded(count, channel, size, start=0):
    """Frame i shows number start + i in `channel`: a marker bar, then seven bars for its bits, so the source and the
    number survive H.264 and scaling."""
    images = torch.zeros(count, size, size, 3)
    bar = size // 8
    for index in range(count):
        number = start + index
        images[index, :, :bar, channel] = 1
        for bit in range(7):
            if number >> bit & 1:
                images[index, :, (bit + 1) * bar:(bit + 2) * bar, channel] = 1
    return images


def label(array):
    """(channel, number) of a frame written by `coded`."""
    bar = array.shape[1] / 8

    def column(index):
        return array[:, int((index + 0.5) * bar)].mean(axis=0)

    channel = int(column(0).argmax())
    return channel, sum(1 << bit for bit in range(7) if column(bit + 1)[channel] > 127)


def decoded(path):
    with av.open(path) as container:
        stream = container.streams.video[0]
        size = (stream.codec_context.width, stream.codec_context.height)
        count = sum(1 for _ in container.decode(stream))
    found = media.read_frames(path, range(count))
    return size, [label(found[index]) for index in range(count)]


class PartialVideoTest(unittest.TestCase):
    """Box a (22 frames) and box c (17 new frames after 5 carried) are rendered; box b (17 frames) is not."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="h3c-partial-")
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)], video_slices=["video1"])
        self.manifest = {"segments": [self.segment(1, "a", 22, 0, 0, 0.1), self.segment(3, "c", 22, 5, 2, 0.3)]}
        store.write_manifest(self.folder, self.manifest)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def segment(self, index, box_id, frames, context, channel, level):
        entry = {"index": index, "stem": store.stem(index), "frames": frames, "context_frames": context,
                 "audio_sample_rate": RATE, "timeline": {"box": box_id},
                 "video": {"file": f"{store.stem(index)}.mp4", "frames": frames - context, "fps": 24,
                           "width": SEGMENT_SIZE, "height": SEGMENT_SIZE}}
        media.write_segment_video(os.path.join(self.folder, entry["video"]["file"]),
                                  coded(frames - context, channel, SEGMENT_SIZE), 24, 16)
        store.save_segment(self.folder, entry, torch.zeros(1, 1, 1, 1, 1), torch.zeros(1, 1, 1, 1),
                           torch.full((1, frames * RATE // 24), level))
        return entry

    def keep(self, frames=60, sound=0.2, digest=lambda name: name):
        audios = {} if sound is None else {"video_audio1": {"waveform": torch.full((1, 1, frames * RATE // 24), sound),
                                                            "sample_rate": RATE}}
        written = partial_video.keep_source(self.folder, "seq", "video1", {"video1": coded(frames, 1, SOURCE_SIZE)},
                                            audios, SOURCE_SIZE, SOURCE_SIZE, digest)
        self.manifest["source"] = store.load_manifest(self.folder)["source"]
        return written

    def build(self, done=frozenset({0, 2}), soundtrack=()):
        return partial_video.build(self.folder, "seq", self.parsed, self.manifest, set(done), list(soundtrack), 16)

    def heard(self, **keep):
        self.keep(**keep)
        captured = []
        with mock.patch.object(media, "build_full_video",
                               side_effect=lambda path, videos, audio, crf, size: (captured.append(audio), (path, ""))[1]):
            self.build()
        return captured[0]

    def test_unrendered_boxes_play_the_source_at_their_timeline_time(self):
        self.keep()
        record, note = self.build()
        self.assertEqual(note, "")
        self.assertEqual((record["rendered"], record["boxes"]), (2, 3))
        size, labels = decoded(os.path.join(self.folder, record["file"]))
        self.assertEqual(size, (SEGMENT_SIZE, SEGMENT_SIZE), "the source is scaled to the rendered boxes")
        self.assertEqual(labels, [(0, i) for i in range(22)] + [(1, 22 + i) for i in range(17)]
                         + [(2, i) for i in range(17)])
        self.assertEqual(store.load_manifest(self.folder)["partial_video"], record)

    def test_source_soundtrack_fills_the_unrendered_boxes(self):
        waveform, rate = self.heard()
        self.assertEqual(rate, RATE)
        self.assertEqual(waveform.shape[-1], round(56 * RATE / 24))
        for frame, level in ((11, 0.1), (30, 0.2), (50, 0.3)):
            self.assertAlmostEqual(waveform[0, frame * RATE // 24].item(), level, places=5)

    def test_without_a_source_soundtrack_the_gap_is_silent(self):
        waveform, _ = self.heard(sound=None)
        for frame, level in ((11, 0.1), (30, 0.0), (50, 0.3)):
            self.assertAlmostEqual(waveform[0, frame * RATE // 24].item(), level, places=5)

    def test_a_marked_soundtrack_plays_instead(self):
        self.keep()
        ramp = (torch.zeros(1, round(56 * RATE / 24)), RATE)
        with mock.patch.object(audio_tracks, "soundtrack_sources", return_value=[["clip"]]), \
                mock.patch.object(audio_tracks, "soundtrack_audio", return_value=ramp) as placed:
            record, _ = self.build(soundtrack=[{"slot": "audio1"}])
        self.assertEqual(placed.call_args.args[1], [(22, False), (17, False), (17, False)])
        self.assertIsNotNone(record)

    def test_reused_until_a_source_changes(self):
        self.keep()
        first, _ = self.build()
        with mock.patch.object(media, "build_full_video") as rebuilt:
            self.assertEqual(self.build()[0], first)
        rebuilt.assert_not_called()
        self.manifest["segments"].insert(1, self.segment(2, "b", 22, 5, 0, 0.5))
        record, _ = self.build(done={0, 1})
        self.assertNotEqual(record["sources"], first["sources"])
        self.assertEqual(record["rendered"], 2, "box c is no longer current, so the source fills it")
        _, labels = decoded(os.path.join(self.folder, record["file"]))
        self.assertEqual(labels[22:], [(0, i) for i in range(17)] + [(1, 39 + i) for i in range(17)])

    def test_a_short_source_says_how_many_frames_it_needs(self):
        self.keep(frames=30)
        self.assertEqual(self.build(), (None, "Partial video skipped: video1 has 30 frames, but the Timeline needs 39."))

    def test_without_a_source_only_current_renders_play(self):
        record, _ = self.build()
        self.assertEqual(record["mode"], "rendered")
        self.keep()
        self.assertEqual(self.build(done=set()), (None, ""))
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        self.assertEqual(self.build()[0]["mode"], "rendered", "the split was removed")

    def test_the_source_is_saved_once_per_media_and_size(self):
        self.assertTrue(self.keep())
        source = self.manifest["source"]
        self.assertEqual({key: source[key] for key in ("file", "audio", "slot", "frames", "width", "height")},
                         {"file": "seq_source.mp4", "audio": "seq_source.safetensors", "slot": "video1", "frames": 60,
                          "width": SOURCE_SIZE, "height": SOURCE_SIZE})
        self.assertFalse(self.keep())
        self.assertTrue(self.keep(digest=lambda name: name + " changed"))

    def test_status_returns_the_partial_video(self):
        self.keep()
        status = timeline_node._status("seq", self.folder, self.parsed, self.manifest,
                                       lambda index, entry: True, materialize=True)
        self.assertEqual(status["partial_video"]["rendered"], 2)
        self.assertEqual(status["partial_video"]["boxes"], 3)
        self.assertEqual(status["partial_video"]["file"]["filename"], "seq_partial.mp4")
        self.assertNotIn("export_error", status)
        unbuilt = timeline_node._status("seq", self.folder, self.parsed, self.manifest, lambda index, entry: True)
        self.assertNotIn("partial_video", unbuilt, "only a materializing status builds it")

    def test_ordinary_timeline_joins_current_clips_across_gaps(self):
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        self.manifest["segments"].reverse()
        record, note = self.build()
        self.assertIsNotNone(record)
        self.assertEqual(note, "")
        self.assertEqual((record["rendered"], record["boxes"], record["mode"]), (2, 3, "rendered"))
        _, labels = decoded(os.path.join(self.folder, record["file"]))
        self.assertEqual(labels, [(0, i) for i in range(22)] + [(2, i) for i in range(17)])
        status = timeline_node._status("seq", self.folder, self.parsed, self.manifest,
                                       lambda index, entry: True, materialize=True)
        self.assertEqual(status["partial_video"]["mode"], "rendered")

    def test_ordinary_partial_omits_stale_clips_and_handles_no_current_video(self):
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        record, _ = self.build(done={2})
        self.assertIsNotNone(record)
        self.assertEqual(record["rendered"], 1)
        _, labels = decoded(os.path.join(self.folder, record["file"]))
        self.assertEqual(labels, [(2, i) for i in range(17)])
        self.assertEqual(self.build(done=set()), (None, ""))

    def test_missing_rendered_video_does_not_hide_other_playable_clips(self):
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        os.remove(os.path.join(self.folder, "seg_0003.mp4"))
        record, _ = self.build()
        self.assertIsNotNone(record)
        self.assertEqual(record["rendered"], 1)
        _, labels = decoded(os.path.join(self.folder, record["file"]))
        self.assertEqual(labels, [(0, i) for i in range(22)])

    def test_mux_switch_keeps_h3_sound_and_invalidates_the_partial_cache(self):
        self.keep()
        first, _ = self.build()
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)],
                            video_slices=["video1"], mux_audio=False)
        # Invalid uploaded files must not prevent playback with H3 sound selected.
        status = timeline_node._status("seq", self.folder, self.parsed, self.manifest,
                                       lambda index, entry: True, materialize=True)
        self.assertIn("partial_video", status)
        self.assertNotEqual(status["partial_video"]["file"]["v"], first["sources"])

    def test_compact_soundtrack_uses_the_original_clock_after_a_gap(self):
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        ramp = torch.arange(round(56 * RATE / 24), dtype=torch.float32).unsqueeze(0)
        captured = []
        with mock.patch.object(audio_tracks, "soundtrack_sources", return_value=[["clip"]]), \
                mock.patch.object(audio_tracks, "soundtrack_audio", return_value=(ramp, RATE)), \
                mock.patch.object(media, "build_full_video",
                                  side_effect=lambda path, videos, audio, crf, size:
                                  (captured.append(audio), (path, ""))[1]):
            record, _ = self.build(soundtrack=[{"slot": "audio1"}])
        self.assertIsNotNone(record)
        waveform, rate = captured[0]
        expected = torch.cat([ramp[:, :round(22 * RATE / 24)], ramp[:, round(39 * RATE / 24):]], dim=-1)
        self.assertEqual(rate, RATE)
        self.assertTrue(torch.equal(waveform, expected))

    def test_mux_choice_switches_between_uploaded_and_h3_audio_in_partial_and_full_video(self):
        path = os.path.join(self.folder, "uploaded.wav")
        with wave.open(path, "wb") as out:
            out.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            out.writeframes((-13107).to_bytes(2, "little", signed=True) * (RATE * 3))
        boxes = [box("a", 22), box("b", 17), box("c", 17)]
        for complete in (False, True):
            if complete:
                self.manifest["segments"].insert(1, self.segment(2, "b", 22, 5, 1, 0.2))
            versions = []
            for mux, level in ((True, -0.4), (False, 0.1), (True, -0.4)):
                parsed = parse(boxes, audio_clips=[clip(in_full_video=True)], mux_audio=mux)
                with mock.patch.object(audio_tracks, "file_path", return_value=path):
                    status = timeline_node._status("seq", self.folder, parsed, self.manifest,
                                                   lambda index, entry: True, materialize=True)
                descriptor = status["full_video"] if complete else status["partial_video"]["file"]
                versions.append(descriptor["v"])
                with av.open(os.path.join(self.folder, descriptor["filename"])) as container:
                    sound = torch.from_numpy(next(container.decode(audio=0)).to_ndarray())
                self.assertAlmostEqual(sound.float().mean().item(), level, delta=0.03)
                self.assertEqual([item["status"] for item in status["boxes"] if item["id"] != "b"], ["done", "done"])
            self.assertNotEqual(versions[0], versions[1])
            self.assertEqual(versions[0], versions[2])

    def test_mux_audio_is_boolean_and_can_bypass_missing_uploaded_sound(self):
        with self.assertRaisesRegex(ValueError, "mux_audio must be true or false"):
            parse([box("a", 22)], mux_audio="false")
        parsed = parse([box("a", 22), box("b", 17), box("c", 17)],
                       audio_clips=[clip(in_full_video=True)], mux_audio=False)
        with mock.patch.object(audio_tracks, "file_path", side_effect=ValueError("file is missing")):
            status = timeline_node._status("seq", self.folder, parsed, self.manifest,
                                           lambda index, entry: True, materialize=True)
        self.assertIn("partial_video", status)
        self.assertNotIn("export_error", status)

    def test_api_export_uses_h3_sample_rate_when_uploaded_mux_is_disabled(self):
        exporter = artifacts.Artifacts.__new__(artifacts.Artifacts)
        exporter.records = SimpleNamespace(get_blob_record=lambda kind, key: (
            {"verified": True, "input_sha256": "input", "native_sha256": "native"} if kind == "unit"
            else {"media": {"sample_rate": 24000}}))
        video = self.manifest["segments"][0]["video"]["file"]
        full = os.path.join(self.folder, "api_full.mp4")
        media.build_full_video(full, [os.path.join(self.folder, video)],
                               (torch.full((1, round(22 * RATE / 24)), 0.1), RATE), 16)
        exporter._body = lambda project: {}
        exporter._unit = lambda project, unit, status: {"filename": "api_full.mp4"}
        # Keep real decoding/metadata validation; only replace API storage and native status.
        exporter.snapshot = lambda project, job, descriptor, expected_frames, kind: exporter._inspect(
            full, project, descriptor, expected_frames)
        project = {"id": "p1", "prepared": {"settings": {"width": 64, "height": 64},
                   "timeline": {"mux_audio": False, "audio_clips": [{"slot": "audio1", "in_full_video": True}]}},
                   "assets": [{"asset_id": "a1", "bindings": [{"kind": "audio_clip", "slot": "audio1"}]}]}
        job = {"id": "j1", "revision": 1, "profile_sha256": "profile", "owner_token": "owner", "plan": {
            "total_frames": 22, "units": [{"id": "box:a", "kind": "box", "frames": 22, "input_sha256": "input"}]}}
        native = SimpleNamespace(status=lambda *args, **kwargs: {"ok": True, "full_video": {"filename": "api_full.mp4"}})
        with mock.patch.object(artifacts, "native_status", return_value={"unit_evidence": {"box:a": "native"}}):
            delivered = exporter.finalize(project, job, native)
        self.assertEqual(delivered[-1]["audio"]["sample_rate"], RATE)


if __name__ == "__main__":
    unittest.main()
