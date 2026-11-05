import unittest
from unittest import mock

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

from h3_continuity import project_nodes as project  # noqa: E402
from h3_continuity.timeline_node import H3C_Timeline  # noqa: E402

# The H3 Timeline widgets of 0.12.x, in the order saved workflows store their values.
WIDGETS_0_12 = ["name", "width", "height", "context_frames", "carry_audio", "ref_image_size", "timeline",
                "audio_context_frames"]
OWNED = {"ref_image_size", "carry_audio", "audio_context_frames"}


class ProjectValueTest(unittest.TestCase):
    def test_with_feature_appends_once(self):
        value = project.with_feature(None, "sound", {"carry_audio": False})
        value = project.with_feature(value, "sound", {"carry_audio": True})
        value = project.with_feature(value, "references", {"ref_image_size": "max"})
        self.assertEqual(value, {"features": ["sound", "references"],
                                 "settings": {"carry_audio": True, "ref_image_size": "max"}})

    def test_with_feature_does_not_change_its_input(self):
        first = project.with_feature(None, "sound", {"carry_audio": False})
        project.with_feature(first, "references", {"ref_image_size": "max"})
        self.assertEqual(first, {"features": ["sound"], "settings": {"carry_audio": False}})

    def test_apply_project_none_is_identity(self):
        self.assertEqual(project.apply_project(None, carry_audio=True), {"carry_audio": True})

    def test_connected_value_replaces_widget(self):
        value = {"features": ["sound"], "settings": {"carry_audio": False}}
        self.assertIs(project.apply_project(value, carry_audio=True)["carry_audio"], False)

    def test_apply_project_never_adds_keys(self):
        value = {"features": ["sound"], "settings": {"carry_audio": False, "other": 1}}
        self.assertEqual(project.apply_project(value, ref_image_size="match"), {"ref_image_size": "match"})

    def test_add_on_owns_only_its_keys(self):
        references = project.H3C_PlusReferences.execute(project=None, ref_image_size="max").args[0]
        sound = project.H3C_PlusSound.execute(project=references, carry_audio=False, audio_context_frames=12).args[0]
        tools = project.H3C_PlusContinuity.execute(project=sound).args[0]
        self.assertEqual(references, {"features": ["references"], "settings": {"ref_image_size": "max"}})
        self.assertEqual(tools, {"features": ["references", "sound", "continuity"],
                                 "settings": {"ref_image_size": "max", "carry_audio": False, "audio_context_frames": 12}})

    def test_schemas_have_project_in_and_out(self):
        for node, widgets in ((project.H3C_PlusReferences, ["ref_image_size"]),
                              (project.H3C_PlusSound, ["carry_audio", "audio_context_frames"]),
                              (project.H3C_PlusContinuity, [])):
            schema = node.define_schema()
            self.assertTrue(schema.display_name.startswith("H3 + "))
            self.assertEqual(schema.inputs[0].id, "project")
            self.assertTrue(schema.inputs[0].optional)
            self.assertEqual([item.id for item in schema.inputs[1:]], widgets)
            self.assertEqual([item.io_type for item in schema.outputs], ["H3C_PROJECT"])


class CoreInputTest(unittest.TestCase):
    def test_core_inputs_keep_widget_order(self):
        inputs = H3C_Timeline.define_schema().inputs
        widgets = [item.id for item in inputs if item.io_type in ("STRING", "INT", "COMBO", "BOOLEAN")]
        self.assertEqual(widgets, WIDGETS_0_12)
        self.assertEqual(inputs[-1].id, "project")
        self.assertTrue(inputs[-1].optional)
        self.assertEqual({item.id for item in inputs if item.advanced}, OWNED)

    def test_core_execute_unchanged_without_project(self):
        given = dict(clip="clip", vae="vae", name="n", width=64, height=32, context_frames="22", carry_audio=True,
                     ref_image_size="match", timeline="{}", audio_vae="avae", images={"image1": 1}, audios=None,
                     negative="neg", story=None, videos=None, video_audios=None, still_recipe=None,
                     audio_context_frames=5)
        with mock.patch.object(H3C_Timeline, "_render", return_value="out") as render:
            self.assertEqual(H3C_Timeline.execute(**given), "out")
            self.assertEqual(render.call_args.kwargs, given)
            H3C_Timeline.execute(**given, project=None)
            self.assertEqual(render.call_args.kwargs, given)

    def test_connected_add_on_changes_only_its_settings(self):
        given = dict(clip="clip", vae="vae", carry_audio=True, ref_image_size="match", audio_context_frames=5)
        value = {"features": ["sound"], "settings": {"carry_audio": False, "audio_context_frames": 0}}
        with mock.patch.object(H3C_Timeline, "_render", return_value="out") as render:
            H3C_Timeline.execute(**given, project=value)
        self.assertEqual(render.call_args.kwargs, {**given, "carry_audio": False, "audio_context_frames": 0})


if __name__ == "__main__":
    unittest.main()
