import unittest

from h3_continuity import dialogue, timeline as rules

from .helpers import box, clip, cue, parse


def cued(boxes, *items, clips=None, **extra):
    return parse(boxes, audio_clips=clips or [clip()], dialogue={"version": 1, "cues": list(items)}, **extra)


def plan(timeline, index, context=39):
    return rules.plan_box(timeline, index, context, True, 512, 512, 512, [], [])


class EventTest(unittest.TestCase):
    def test_events_use_the_generation_clock_including_replay(self):
        timeline = cued([box("a", 56), box("b", 51)], cue(start=2.5, end=3.0, language="English"))
        [event] = dialogue.box_events(timeline, 1, 39)
        # Box 2 starts at 56/24 s and replays 39 frames, so its clock starts at 17/24 s.
        self.assertEqual((event["start_ms"], event["end_ms"]), (1792, 2292))
        self.assertFalse(event["continuing"])
        self.assertEqual(dialogue.box_events(timeline, 0, 39), [])

    def test_a_line_crossing_a_cut_is_one_line_and_its_continuation(self):
        timeline = cued([box("a", 56), box("b", 56, cut=True)], cue(start=2.0, end=3.0))
        [first] = dialogue.box_events(timeline, 0, 39)
        [second] = dialogue.box_events(timeline, 1, 39)
        self.assertEqual((first["start_ms"], first["end_ms"], first["continues_after"]), (2000, 2333, True))
        self.assertEqual((second["start_ms"], second["end_ms"], second["continuing"]), (0, 667, True))
        self.assertIn("<d>Hello there.</d>", dialogue.block([first]))
        self.assertIn("still being spoken at the final frame", dialogue.block([first]))
        continuation = dialogue.block([second])
        self.assertIn("finishes the line already in progress", continuation)
        self.assertNotIn("<d>", continuation)

    def test_a_line_starting_in_the_replayed_context_keeps_its_start(self):
        timeline = cued([box("a", 56), box("b", 51)], cue(start=2.0, end=3.0))
        [event] = dialogue.box_events(timeline, 1, 39)
        self.assertFalse(event["continuing"])
        self.assertEqual(event["start_ms"], 1292)

    def test_voiceover_and_on_screen_phrasing(self):
        timeline = cued([box("a", 107)], cue("c1", 1.0, 2.0), cue("c2", 2.0, 3.0, text="Later.", speaker="Narrator",
                                                                     portrayal="voiceover", language="English"))
        text = dialogue.block(dialogue.box_events(timeline, 0, 39))
        self.assertIn("From 00:01.000 to 00:02.000: Mara (S1) says: <d>Hello there.</d>", text)
        self.assertIn("Narrator (S2) says in an off-screen voiceover: <d>[English] Later.</d>", text)
        self.assertIn("no on-screen character's lips move", text)

    def test_mixed_portrayal_names_the_voiceover_part(self):
        line = cue(start=1.0, end=3.0, spans=[{"start": 2.0, "end": 3.0, "portrayal": "voiceover"}])
        text = dialogue.block(dialogue.box_events(cued([box("a", 107)], line), 0, 39))
        self.assertIn("off-screen voiceover from 00:02.000 to 00:03.000", text)

    def test_unbound_and_manual_boxes_compile_nothing(self):
        timeline = cued([box("a", 107), box("b", 107, cut=True, dialogue="manual")],
                        cue("c1", 1.0, 2.0), cue("c2", 5.0, 6.0))
        self.assertEqual([event["id"] for event in dialogue.box_events(timeline, 0, 39)], ["c1"])
        self.assertEqual(dialogue.box_events(timeline, 1, 39), [])
        timeline = cued([box("a", 107)], cue(slot="audio2"))
        self.assertEqual(dialogue.box_events(timeline, 0, 39), [])


class PlanTest(unittest.TestCase):
    def test_plan_inserts_compiled_dialogue(self):
        result = plan(cued([box("a", 107)], cue(language="English")), 0)
        # The recording is an audio reference, so H3 runs ref2va and reads the detailed description.
        self.assertEqual(result.slots.mode, "ref2va")
        self.assertTrue(result.prompt.startswith("detailed_description: A quiet street.\nDialogue from the recording"))
        self.assertIn("<d>[English] Hello there.</d>", result.prompt)

    def test_visual_memory_keeps_the_compiled_dialogue(self):
        from h3_continuity import visual_memory
        timeline = cued([box("a", 107), box("b", 107, cut=True, memory="scene")], cue(start=5.6, end=7.9))
        records = [{"label": "the previous shot before this cut", "whole": True, "new_scene": False}]
        prompt = visual_memory.box_prompt(timeline, 1, 39, plan(timeline, 1), records)
        self.assertIn("<Video 1> is an earlier moment of this film (the previous shot before this cut).", prompt)
        # Box 2 starts at 107/24 s, so the line plays from 1.142 s of its own clock.
        self.assertIn("From 00:01.142 to 00:03.442: Mara (S1) says: <d>Hello there.</d>", prompt)

    def test_a_cut_cue_needs_review_before_rendering(self):
        timeline = cued([box("a", 107)], cue(start=9.0, end=11.0), clips=[clip(source_start=10.0, duration=5.0)])
        with self.assertRaises(ValueError) as caught:
            plan(timeline, 0)
        self.assertIn("cut by", str(caught.exception))
        self.assertIn("@audio1", str(caught.exception))

    def test_typed_dialogue_conflicts_with_covering_cues(self):
        typed = box("a", 107, prompt="Mara says: <d>Hello.</d>")
        with self.assertRaises(ValueError) as caught:
            plan(cued([typed], cue()), 0)
        self.assertIn("manual", str(caught.exception))
        manual = plan(cued([{**typed, "dialogue": "manual"}], cue()), 0)
        self.assertEqual(manual.prompt, "Mara says: <d>Hello.</d>")
        self.assertEqual(plan(parse([typed]), 0).prompt, "Mara says: <d>Hello.</d>")

    def test_layout_follows_compiled_dialogue_only(self):
        line = cue()
        key = rules.layout_key(cued([box("a", 107)], line), 0)
        self.assertNotEqual(rules.layout_key(cued([box("a", 107)], {**line, "text": "Hi."}), 0), key)
        self.assertEqual(rules.layout_key(cued([box("a", 107)], {**line, "aligned": dialogue.alignment_key(line)}), 0), key)
        self.assertEqual(rules.layout_key(cued([box("a", 107)], cue(start=20.0, end=21.0)), 0),
                         rules.layout_key(parse([box("a", 107)], audio_clips=[clip()]), 0))


if __name__ == "__main__":
    unittest.main()
