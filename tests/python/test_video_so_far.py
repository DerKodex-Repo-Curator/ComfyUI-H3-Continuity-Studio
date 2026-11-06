"""The video so far: the boxes rendered from the first one on, joined while later boxes still wait, so sound and picture
can be checked before every box renders."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

import torch

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

from h3_continuity import media, nodes, store, timeline_node  # noqa: E402

from .helpers import box, parse  # noqa: E402
from .test_partial_video import RATE, SEGMENT_SIZE, coded, decoded  # noqa: E402


class VideoSoFarTest(unittest.TestCase):
    """Boxes a (22 frames), b (17 after 5 carried) and c (17): a and b are rendered, c is not."""

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="h3c-so-far-")
        patcher = mock.patch("h3_continuity.timeline_api.service.authorize_sequence", lambda *args, **kwargs: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.parsed = parse([box("a", 22), box("b", 17), box("c", 17)])
        self.manifest = {"segments": [self.segment(1, "a", 22, 0, 0, 0.1), self.segment(2, "b", 22, 5, 1, 0.3)]}
        store.write_manifest(self.folder, self.manifest)

    def tearDown(self):
        nodes.wait_full_video(self.folder, 30)
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

    def status(self, materialize=True):
        """A status from the saved manifest, as a request reads it, with this test's segments."""
        manifest = {**store.load_manifest(self.folder), "segments": self.manifest["segments"]}
        store.write_manifest(self.folder, manifest)
        return timeline_node._status("seq", self.folder, self.parsed, manifest, lambda index, entry: True,
                                     materialize=materialize)

    def built(self):
        first = self.status()
        nodes.wait_full_video(self.folder, 30)
        return first, self.status()

    def test_the_rendered_boxes_play_before_the_rest_render(self):
        first, status = self.built()
        self.assertTrue(first.get("preview_video_building") or "preview_video" in first, first)
        self.assertIsNone(status["full_video"])
        so_far = status["preview_video"]
        self.assertEqual((so_far["boxes"], so_far["total"]), (2, 3))
        self.assertEqual(so_far["file"]["filename"], "seq_sofar.mp4")
        self.assertEqual(so_far["clock"], [[0, 22, 0, 1], [22, 17, 22, 1]])
        _, labels = decoded(os.path.join(self.folder, "seq_sofar.mp4"))
        self.assertEqual(labels, [(0, i) for i in range(22)] + [(1, i) for i in range(17)])
        self.assertEqual(store.load_manifest(self.folder)["preview_video"]["boxes"], 2)

    def test_only_a_materializing_status_builds_it(self):
        self.assertNotIn("preview_video", self.status(materialize=False))
        nodes.wait_full_video(self.folder, 30)
        self.assertFalse(os.path.exists(os.path.join(self.folder, "seq_sofar.mp4")))

    def test_it_stops_at_the_first_box_without_a_take(self):
        self.manifest["segments"] = [self.manifest["segments"][1]]
        self.manifest["segments"][0]["index"] = 2
        self.assertNotIn("preview_video", self.built()[1], "box a has no take, so nothing plays from the start")

    def test_it_is_reused_until_a_box_changes(self):
        self.built()
        with mock.patch.object(media, "build_full_video") as rebuilt:
            self.assertIn("preview_video", self.status())
        rebuilt.assert_not_called()
        self.manifest["segments"].append(self.segment(3, "c", 22, 5, 2, 0.5))
        status = self.status()
        self.assertIn("full_video_building", status, "every box has a take, so the full video builds instead")
        self.assertNotIn("preview_video", status)


class VideoClockTest(unittest.TestCase):
    def test_bridges_hold_the_timeline_and_replacements_keep_its_time(self):
        parsed = parse([box("a", 22), box("b", 22, cut=True), box("c", 22, cut=True)])
        a, b, c = ({"index": i + 1, "timeline": {"box": name}} for i, name in enumerate("abc"))
        bridge = {"box": "b"}
        candidate = {"box": "c", "candidate": "x", "timeline": {"left": 4, "right": 6}}
        ordered = [(a, 0, 22, False), (bridge, 0, 29, True), (b, 0, 18, False), (candidate, 0, 10, False),
                   (c, 6, 16, False)]
        self.assertEqual(timeline_node.video_clock(parsed, ordered),
                         [[0, 22, 0, 1], [22, 29, 22, 0], [51, 18, 22, 1], [69, 10, 40, 1], [79, 16, 50, 1]])


if __name__ == "__main__":
    unittest.main()
