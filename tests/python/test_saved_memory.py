import os
import tempfile
import unittest

import torch

from h3_continuity import store, visual_memory
from .helpers import box, parse


class SavedVisualMemoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="h3c-saved-memory-")
        self.addCleanup(self.temp.cleanup)
        self.entry = {"index": 1, "stem": "seg_0001", "frames": 22, "context_frames": 0,
                      "latent_width": 64, "latent_height": 64, "timeline": {"box": "a"}}
        store.save_segment(self.temp.name, self.entry, torch.zeros(1, 24, 7, 2, 2),
                           torch.zeros(1, 1, 1, 1), None)
        self.line = parse([box("a", 22), box("b", 22, cut=True, memory="scene")])

    def records(self):
        return visual_memory.records(self.line, 1, self.temp.name, {1: self.entry},
                                     lambda index, entry: False, 64, 64)

    def test_visual_memory_can_read_an_older_saved_take(self):
        records = self.records()
        self.assertTrue(records)
        windows = visual_memory.load(self.temp.name, {1: self.entry}, records)
        self.assertEqual(windows[0].shape, (1, 24, 7, 2, 2))
        self.assertEqual(records[0]["box"], "a")

    def test_missing_latents_still_require_a_render(self):
        os.remove(os.path.join(self.temp.name, "seg_0001.safetensors"))
        with self.assertRaisesRegex(ValueError, "needs rendering first"):
            self.records()

    def test_selected_moment_must_exist_in_the_saved_take(self):
        self.line = parse([box("a", 39), box("b", 22, cut=True, memory="selected",
                          memories=[{"box": "a", "frame": 30, "label": "later moment"}])])
        with self.assertRaisesRegex(ValueError, "saved take"):
            self.records()

    def test_mismatched_identity_and_resolution_are_still_rejected(self):
        self.entry["timeline"]["box"] = "different"
        with self.assertRaisesRegex(ValueError, "needs rendering first"):
            self.records()
        self.entry["timeline"]["box"] = "a"
        self.entry["latent_width"] = 128
        with self.assertRaisesRegex(ValueError, "different resolution"):
            self.records()
