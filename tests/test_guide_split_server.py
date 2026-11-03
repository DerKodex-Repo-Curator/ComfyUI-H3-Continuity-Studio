"""The server reads a browser guide split as intended: the left clip ends on the guide, the right one continues from it.

The browser edit runs in Node (tests/js/emit_guide_split.mjs); this test parses its JSON with the render code."""
import json
import os
import shutil
import subprocess
import unittest

from h3_continuity import timeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which("node")


def emitted():
    script = os.path.join(ROOT, "tests", "js", "emit_guide_split.mjs")
    return json.loads(subprocess.run([NODE, script], cwd=ROOT, check=True, capture_output=True, text=True).stdout)


@unittest.skipUnless(NODE, "Node.js is needed to run the browser edit")
class GuideSplitServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = emitted()
        cls.context = cls.data["context"]

    def parsed(self, case):
        return timeline.parse(self.data[case]["after"])

    def assert_no_conflicts(self, parsed):
        for index in range(len(parsed.boxes)):
            timeline.box_length(parsed, index, self.context)
            self.assertEqual(timeline.carry_conflict(parsed, index, self.context), "")
            self.assertEqual(timeline.dropped_frames(parsed, index), 0)
            timeline.frame_guides(parsed, index, self.context)
            timeline.layout_key(parsed, index, self.context)

    def test_shot_guide_becomes_last_and_first(self):
        parsed = self.parsed("shot")
        guide = "guide_a.png"
        self.assert_no_conflicts(parsed)
        left, right = 0, 1
        self.assertFalse(timeline.is_fresh(parsed, right), "the right clip continues the left one")
        frames, carried = timeline.box_length(parsed, left, self.context)
        # The guide is the left clip's final generated frame, and an endpoint rather than an inserted frame.
        self.assertEqual([(frame, g["filename"]) for frame, g in timeline.frame_guides(parsed, left, self.context)],
                         [(frames + carried - 1, guide)])
        self.assertEqual(timeline.accepted_endpoints(parsed, left, self.context)["last"]["filename"], guide)
        self.assertEqual(timeline.box_slots(parsed, left, self.context).mode, "flf2va")
        # On the right the same PNG is the shared boundary: the last carried frame.
        right_frames, right_carried = timeline.box_length(parsed, right, self.context)
        self.assertEqual(right_carried, self.context)
        guides = dict((g["filename"], frame) for frame, g in timeline.frame_guides(parsed, right, self.context))
        self.assertEqual(guides[guide], right_carried - 1)
        self.assertEqual(timeline.accepted_endpoints(parsed, right, self.context)["first"]["filename"], guide)
        # The later Shot guide still resolves, at its shot's re-based time.
        self.assertEqual(guides["guide_c.png"], 48 + right_carried - 1)

    def test_shot_guide_split_keeps_later_movie_timing(self):
        before = timeline.parse(self.data["shot"]["before"])
        after = self.parsed("shot")
        result = self.data["shot"]["result"]
        total = lambda parsed: sum(timeline.box_length(parsed, i, self.context)[0] for i in range(len(parsed.boxes)))
        self.assertEqual(total(after), total(before) + result["added"])
        # Shot 3 sits 48 frames after the guide before and after the split.
        shots = timeline._shot_frames(after.boxes[1].prompt, self.context, after.boxes[1].frames)
        self.assertEqual(shots[2], 48)

    def test_continuing_split_with_references_stays_flf2va(self):
        parsed = self.parsed("continuing")
        self.assert_no_conflicts(parsed)
        left, right = 1, 2
        for index in (left, right):
            self.assertTrue(parsed.boxes[index].flf_refmods)
            self.assertEqual(timeline.box_slots(parsed, index, self.context).mode, "flf2va")
        frames, carried = timeline.box_length(parsed, left, self.context)
        self.assertIn((frames + carried - 1, "guide_a.png"),
                      [(frame, g["filename"]) for frame, g in timeline.frame_guides(parsed, left, self.context)])
        # The Last candidate moved to the right clip's Last; the plate change after the guide moved with it.
        last = [p for p in timeline.resolved_previews(parsed, right, self.context) if p.get("target") == {"kind": "last"}]
        self.assertEqual(last[0]["frame"], parsed.boxes[right].frames)
        self.assertEqual([c["frame"] for c in parsed.boxes[right].plate_changes], [70])
        self.assertEqual([c["frame"] for c in parsed.boxes[left].plate_changes], [20])

    def test_before_the_split_the_mid_clip_guide_is_an_insert(self):
        """The baseline the feature fixes: the guide is a pinned frame inside one generation, not an endpoint."""
        parsed = timeline.parse(self.data["continuing"]["before"])
        endpoints = timeline.accepted_endpoints(parsed, 1, self.context)
        self.assertNotIn("guide_a.png", [g["filename"] for g in endpoints.values()])
        self.assertEqual(timeline.box_slots(parsed, 1, self.context).mode, "ref2va")


if __name__ == "__main__":
    unittest.main()
