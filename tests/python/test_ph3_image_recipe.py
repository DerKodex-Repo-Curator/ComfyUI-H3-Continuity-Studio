import unittest
from unittest import mock

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

import nodes  # noqa: E402

from h3_continuity import image_recipe, ph3_image_nodes as ph3, story_context  # noqa: E402

FILES = {"diffusion_models": ["p-h3-image_int8_convrot.safetensors"],
         "text_encoders": ["p-h3-image_text_encoder_bf16.safetensors"], "vae": ["p-h3-image_vae_int8_convrot.safetensors"]}
NODE = "5"


def at(input):
    return {"node": NODE, "input": input}


def recipe():
    """What web/h3c_stills.mjs captureRecipe returns for the node."""
    return {"version": 2, "adapter": "pixels", "label": "P-H3-Image", "reference_limit": 8, "reference_label": "<Picture {index}>",
            "output": [NODE, 0],
            "bindings": {"prompt": at("prompt"), "instruction": at("instruction"), "seed": at("seed"),
                         "size": {"width": [at("width")], "height": [at("height")]},
                         "references": [at(f"images.image_{i}") for i in range(1, 9)]}}


def workflow():
    return {"api": {NODE: {"class_type": "H3C_PH3ImageStill", "inputs": {
        "diffusion_model": "p-h3-image_int8_convrot.safetensors", "text_encoder": "p-h3-image_text_encoder_bf16.safetensors",
        "vae": "p-h3-image_vae_int8_convrot.safetensors", "prompt": "", "instruction": "", "seed": 1, "width": 1024,
        "height": 576, "prompt_upsampler": "off"}}}}


def reference(slot, roles, digest):
    return {"slot": slot, "roles": roles, "sha256": digest, "file": {"type": "input", "filename": slot + ".png"}}


def prepare(references=(), **request):
    body = {"request_id": "r1", "box": "b1", "target": {"kind": "first"}, "prompt": "She pours coffee.", "seed": 42,
            "size": {"width": 1280, "height": 704}, "frame": 0, **request}
    with mock.patch("folder_paths.get_filename_list", lambda folder: list(FILES.get(folder, []))), \
         mock.patch.dict(nodes.NODE_CLASS_MAPPINGS, {"H3C_PH3ImageStill": ph3.H3C_PH3ImageStill}):
        return image_recipe.prepare(recipe(), workflow(), body, list(references))


class PrepareTest(unittest.TestCase):
    def test_text_to_image_binds_prompt_seed_and_size_on_the_node_and_saves_its_image(self):
        result = prepare()
        node = result["prompt"][NODE]["inputs"]
        self.assertEqual((node["prompt"], node["seed"], node["width"], node["height"]), ("She pours coffee.", 42, 1280, 704))
        self.assertEqual(result["prompt"]["h3c_still_output"]["inputs"]["images"], [NODE, 0])
        self.assertEqual(result["provenance"]["generator"], "P-H3-Image")
        self.assertEqual(result["provenance"]["effective_prompt"], "She pours coffee.")
        self.assertNotIn("prompt_policy", result["provenance"])
        self.assertFalse([key for key in node if key.startswith("images.")])

    def test_the_canvas_reference_goes_first_as_picture_1_and_the_prompt_says_which_picture_is_edited(self):
        result = prepare([reference("image2", ["identity: Mei"], "b" * 64), reference("image1", ["location: Kitchen"], "a" * 64)])
        node = result["prompt"][NODE]["inputs"]
        self.assertEqual([key for key in node if key.startswith("images.")], ["images.image_1", "images.image_2"])
        prompt = result["provenance"]["effective_prompt"]
        self.assertTrue(prompt.startswith("Edit <Picture 1>. "))
        self.assertIn("<Picture 1>: location: Kitchen", prompt)
        self.assertIn("<Picture 2>: identity: Mei", prompt)
        self.assertTrue(prompt.endswith("Requested visible state:\nShe pours coffee."))
        self.assertEqual(result["provenance"]["prompt_policy"], "p-h3-image-scene-v1")
        self.assertEqual(result["provenance"]["canvas_reference"], "<Picture 1>")
        self.assertEqual(node["images.image_1"], ["h3c_still_source_0", 0])

    def test_logical_references_in_the_prompt_become_picture_labels(self):
        result = prepare([reference("image1", ["location: Kitchen"], "a" * 64), reference("image2", ["identity: Mei"], "b" * 64)],
                         prompt="@image2 stands in @image1.")
        self.assertIn("<Picture 2> stands in <Picture 1>.", result["provenance"]["effective_prompt"])

    def test_more_than_eight_references_name_what_does_not_fit(self):
        refs = [reference(f"image{i}", [f"prop: Thing {i}"], f"{i:064x}") for i in range(1, 10)]
        with self.assertRaisesRegex(ValueError, "capacity 8 cannot fit 9"):
            prepare(refs)


class RendererTest(unittest.TestCase):
    def prompt(self, link, **extra):
        return {"1": {"class_type": "H3C_Timeline", "inputs": {"still_recipe": link}},
                "5": {"class_type": "H3C_PH3ImageStill", "inputs": {}}, **extra}

    def test_a_pixel_story_that_uses_the_p_h3_image_recipe_output_writes_image_prompts(self):
        self.assertEqual(story_context.renderer_for(self.prompt(["5", 1]), "1"), "image")

    def test_the_image_output_is_not_a_recipe(self):
        self.assertEqual(story_context.renderer_for(self.prompt(["5", 0]), "1"), "video")

    def test_a_video_output_downstream_keeps_video_writing(self):
        save = {"9": {"class_type": "SaveVideo", "inputs": {"video": ["1", 0]}}}
        self.assertEqual(story_context.renderer_for(self.prompt(["5", 1], **save), "1"), "video")

    def test_a_recipe_through_a_lazy_switch_is_found(self):
        prompt = self.prompt(["7", 0], **{"7": {"class_type": "LazySwitchKJ", "inputs": {"switch": True, "on_true": ["5", 1], "on_false": ["5", 0]}}})
        self.assertEqual(story_context.renderer_for(prompt, "1"), "image")
        prompt["7"]["inputs"]["switch"] = False
        self.assertEqual(story_context.renderer_for(prompt, "1"), "video")

    def test_existing_still_recipes_are_unchanged(self):
        pixels = '{"adapter": "pixels"}'
        prompt = {"1": {"class_type": "H3C_Timeline", "inputs": {"still_recipe": ["6", 0]}},
                  "6": {"class_type": "H3C_StillRecipe", "inputs": {"bindings": pixels}}}
        self.assertEqual(story_context.renderer_for(prompt, "1"), "image")
        prompt["6"]["inputs"]["bindings"] = '{"adapter": "h3"}'
        self.assertEqual(story_context.renderer_for(prompt, "1"), "video")


if __name__ == "__main__":
    unittest.main()
