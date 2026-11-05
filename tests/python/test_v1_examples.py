import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "examples" / "v1"
OURS = {"H3C_Timeline", "H3C_SaveSegment", "H3C_Story", "H3C_StillRecipe", "H3C_ContextWindows", "H3C_PlusReferences",
        "H3C_PlusSound", "H3C_PlusContinuity"}
CORE = {"UNETLoader", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader", "MiniMaxH3SigmaShift", "BasicGuider",
        "BasicScheduler", "RandomNoise", "KSamplerSelect", "SamplerCustomAdvanced", "VAEDecode", "VAEDecodeAudio",
        "SaveImage", "LoadImage", "Note"}
# The node each add-on example is about, and the Timeline input it joins through (None: placed in the model chain).
ADD_ON = {"02": ("H3C_PlusReferences", "project"), "03": ("H3C_PlusSound", "project"),
          "04": ("H3C_PlusContinuity", "project"), "05": ("H3C_Story", "story"), "06": ("H3C_ContextWindows", None),
          "07": ("H3C_PlusReferences", "project")}


def load(name):
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


def timeline(workflow):
    return next(node for node in workflow["nodes"] if node["type"] == "H3C_Timeline")


def linked(workflow, node, name):
    """The node type feeding `node`'s input `name`, or None."""
    link = next((item.get("link") for item in node.get("inputs", []) if item["name"] == name), None)
    if link is None:
        return None
    origin = next(item[1] for item in workflow["links"] if item[0] == link)
    return next(other["type"] for other in workflow["nodes"] if other["id"] == origin)


class V1ExamplesTest(unittest.TestCase):
    def setUp(self):
        self.files = sorted(path.name for path in FOLDER.glob("*.json"))

    def test_seven_examples_parse_and_use_known_nodes(self):
        self.assertEqual(len(self.files), 7)
        for name in self.files:
            workflow = load(name)
            subgraphs = {graph["id"] for graph in (workflow.get("definitions") or {}).get("subgraphs", [])}
            for node in workflow["nodes"]:
                self.assertIn(node["type"], OURS | CORE | subgraphs, f"{name}: {node['type']}")

    def test_every_example_opens_guided_with_clip_and_vae(self):
        for name in self.files:
            workflow = load(name)
            core = timeline(workflow)
            self.assertEqual(core["properties"].get("h3c_ui"), "guided", name)
            self.assertEqual(linked(workflow, core, "clip"), "CLIPLoader", name)
            self.assertEqual(linked(workflow, core, "vae"), "VAELoader", name)
            self.assertTrue(any(node["type"] == "Note" for node in workflow["nodes"]), name)

    def test_hello_h3_needs_nothing_but_models(self):
        workflow = load("01-hello-h3.json")
        types = {node["type"] for node in workflow["nodes"]}
        self.assertFalse(types & {"H3C_Story", "LoadImage", "LoadAudio", "H3C_PlusReferences", "H3C_PlusSound",
                                  "H3C_PlusContinuity"})
        state = json.loads(timeline(workflow)["widgets_values"][6])
        self.assertGreaterEqual(len(state["boxes"]), 2)
        self.assertFalse(state["boxes"][1]["cut"])
        self.assertTrue(all(box["prompt"].strip() for box in state["boxes"]))
        note = next(node for node in workflow["nodes"] if node["type"] == "Note")
        self.assertIn("▶ Render", note["widgets_values"][0])

    def test_each_add_on_example_holds_its_node_and_link(self):
        for name in self.files[1:]:
            workflow = load(name)
            node_type, socket = ADD_ON[name[:2]]
            self.assertTrue(any(node["type"] == node_type for node in workflow["nodes"]), name)
            if socket:
                self.assertEqual(linked(workflow, timeline(workflow), socket), node_type, name)

    def test_models_have_name_folder_and_a_verified_https_url(self):
        for name in self.files:
            for model in load(name).get("models", []):
                self.assertTrue(model["name"] and model["directory"], name)
                self.assertTrue(model["url"].startswith("https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/"), name)
                self.assertTrue(model["url"].endswith("/" + model["name"]), name)

    def test_reference_asset_is_small(self):
        asset = ROOT / "examples" / "assets" / "h3_example_lantern.png"
        self.assertLess(asset.stat().st_size, 300_000)


if __name__ == "__main__":
    unittest.main()
