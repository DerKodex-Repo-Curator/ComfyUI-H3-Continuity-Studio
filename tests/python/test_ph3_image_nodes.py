import asyncio
import unittest
from unittest import mock

import torch

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

from h3_continuity import ph3_image_nodes as ph3  # noqa: E402

UPSAMPLER = "p-h3-image_prompt_upsampler_int8_convrot.safetensors"
FILES = {
    "diffusion_models": ["minimax_h3_ref2va_pruned_int8_convrot.safetensors", "p-h3-image_int8_convrot.safetensors",
                         "pruna\\p-h3-image_bf16.safetensors"],
    "text_encoders": ["qwen3vl_32b_minimax_h3_bf16.safetensors", "p-h3-image_text_encoder_bf16.safetensors", UPSAMPLER],
    "vae": ["minimax_h3_video_vae_fp16.safetensors", "p-h3-image_vae_int8_convrot.safetensors"],
}
CORE = {name: object for name in ("PH3ImageConditioning", "MiniMaxH3SigmaShift", "TextGenerateV2")}


def listing(files):
    return lambda folder: list(files.get(folder, []))


def arguments(**over):
    base = dict(diffusion_model="p-h3-image_int8_convrot.safetensors", text_encoder="p-h3-image_text_encoder_bf16.safetensors",
                vae="p-h3-image_vae_int8_convrot.safetensors", prompt="A kitchen at dawn.", instruction="", seed=7,
                width=1024, height=576)
    return {**base, **over}


def run(**over):
    with mock.patch("folder_paths.get_filename_list", listing(FILES)), \
         mock.patch("nodes.NODE_CLASS_MAPPINGS", {**CORE}):
        return ph3.H3C_PH3ImageStill.execute(**arguments(**over))


def classes(graph):
    return {node["class_type"]: node for node in graph.values()}


def options_of(files):
    with mock.patch("folder_paths.get_filename_list", listing(files)):
        schema = ph3.H3C_PH3ImageStill.define_schema()
    return {item.id: item.options for item in schema.inputs if hasattr(item, "options")}, schema


class FilesTest(unittest.TestCase):
    def test_only_p_h3_image_files_are_offered_and_video_h3_files_are_not(self):
        with mock.patch("folder_paths.get_filename_list", listing(FILES)):
            self.assertEqual(ph3.installed("diffusion_model"),
                             ["p-h3-image_int8_convrot.safetensors", "pruna\\p-h3-image_bf16.safetensors"])
            self.assertEqual(ph3.installed("text_encoder"), ["p-h3-image_text_encoder_bf16.safetensors"])
            self.assertEqual(ph3.installed("prompt_upsampler"), [UPSAMPLER])
            self.assertEqual(ph3.installed("vae"), ["p-h3-image_vae_int8_convrot.safetensors"])

    def test_schema_lists_the_installed_files_and_offers_the_upsampler_off(self):
        options, _ = options_of(FILES)
        self.assertEqual(options["vae"], ["p-h3-image_vae_int8_convrot.safetensors"])
        self.assertEqual(options["prompt_upsampler"], ["off", UPSAMPLER])

    def test_schema_without_files_has_a_placeholder_so_a_video_render_still_validates(self):
        options, _ = options_of({})
        self.assertEqual(options["diffusion_model"], [ph3.MISSING])
        self.assertEqual(options["prompt_upsampler"], ["off"])

    def test_missing_file_message_names_the_folder_the_file_and_the_source(self):
        with mock.patch("folder_paths.get_filename_list", listing({})):
            with self.assertRaises(ValueError) as caught:
                ph3.choose("vae", ph3.MISSING)
        text = str(caught.exception)
        for part in ("VAE is missing", "p-h3-image_vae_int8_convrot.safetensors", "ComfyUI/models/vae", ph3.UPSTREAM,
                     "not interchangeable"):
            self.assertIn(part, text)

    def test_a_video_file_chosen_by_hand_is_refused_with_the_valid_choices(self):
        with mock.patch("folder_paths.get_filename_list", listing(FILES)):
            with self.assertRaises(ValueError) as caught:
                ph3.choose("vae", "minimax_h3_video_vae_fp16.safetensors")
        self.assertIn("not an installed p-h3-image file", str(caught.exception))
        self.assertIn("p-h3-image_vae_int8_convrot.safetensors", str(caught.exception))


class RequirementsTest(unittest.TestCase):
    def test_old_comfyui_is_named_with_the_missing_nodes(self):
        with mock.patch("nodes.NODE_CLASS_MAPPINGS", {}):
            with self.assertRaises(ValueError) as caught:
                ph3.require_core()
        self.assertIn("PH3ImageConditioning", str(caught.exception))
        self.assertIn("Update ComfyUI", str(caught.exception))

    def test_size_must_be_a_multiple_of_32(self):
        with self.assertRaisesRegex(ValueError, "width must be a multiple of 32"):
            run(width=1000)
        with self.assertRaisesRegex(ValueError, "height must be a multiple of 32 and at least 256"):
            run(height=64)

    def test_too_many_references_and_upsampler_with_references_are_refused(self):
        pixels = torch.zeros(1, 8, 8, 3)
        with self.assertRaisesRegex(ValueError, "at most 8"):
            run(images={f"image_{i}": pixels for i in range(1, 10)})
        with self.assertRaisesRegex(ValueError, "does not support reference images"):
            run(images={"image_1": pixels}, prompt_upsampler=UPSAMPLER)

    def test_empty_prompt_is_refused(self):
        with self.assertRaisesRegex(ValueError, "needs a prompt"):
            run(prompt="  ")


class GraphTest(unittest.TestCase):
    def test_text_to_image_is_the_official_graph(self):
        result = run(instruction="Film still.")
        found = classes(result.expand)
        self.assertEqual(set(found), {"UNETLoader", "MiniMaxH3SigmaShift", "CLIPLoader", "VAELoader", "PH3ImageConditioning",
                                      "BasicGuider", "RandomNoise", "KSamplerSelect", "ManualSigmas",
                                      "SamplerCustomAdvanced", "VAEDecode"})
        self.assertEqual(found["UNETLoader"]["inputs"]["unet_name"], "p-h3-image_int8_convrot.safetensors")
        shift = found["MiniMaxH3SigmaShift"]["inputs"]
        self.assertEqual((shift["shift_video"], shift["shift_audio"]), (1.0, 1.0))
        self.assertEqual(found["CLIPLoader"]["inputs"]["type"], "minimax")
        self.assertEqual(found["KSamplerSelect"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(found["ManualSigmas"]["inputs"]["sigmas"], ph3.SIGMAS)
        self.assertEqual(found["RandomNoise"]["inputs"]["noise_seed"], 7)
        conditioning = found["PH3ImageConditioning"]["inputs"]
        self.assertEqual((conditioning["width"], conditioning["height"]), (1024, 576))
        self.assertEqual(conditioning["prompt"], "A kitchen at dawn.\n\nFilm still.")
        self.assertFalse([key for key in conditioning if key.startswith("images.")])
        decode = next(id for id, node in result.expand.items() if node["class_type"] == "VAEDecode")
        self.assertEqual(result.result[0], [decode, 0])

    def test_references_become_numbered_images_in_order(self):
        a, b = torch.zeros(1, 8, 8, 3), torch.ones(1, 8, 8, 3)
        inputs = classes(run(images={"image_2": b, "image_1": a, "image_3": None}).expand)["PH3ImageConditioning"]["inputs"]
        self.assertEqual([key for key in inputs if key.startswith("images.")], ["images.image_1", "images.image_2"])
        self.assertIs(inputs["images.image_1"], a)

    def test_upsampler_adds_the_text_generation_branch_with_the_nearest_aspect_ratio(self):
        graph = run(prompt_upsampler=UPSAMPLER, width=1920, height=1088).expand
        loaders = sorted(node["inputs"]["clip_name"] for node in graph.values() if node["class_type"] == "CLIPLoader")
        self.assertEqual(loaders, [UPSAMPLER, "p-h3-image_text_encoder_bf16.safetensors"])
        generate = classes(graph)["TextGenerateV2"]["inputs"]
        self.assertEqual(generate["prompt"], "Aspect ratio: 16:9\nRequest: A kitchen at dawn.")
        self.assertEqual((generate["sampling_mode"], generate["thinking"]), ("off", True))
        self.assertIsInstance(classes(graph)["PH3ImageConditioning"]["inputs"]["prompt"], list)

    def test_the_recipe_output_describes_this_node_without_running_it(self):
        result = run()
        recipe = ph3.recipe()
        self.assertEqual(result.result[1], recipe)
        self.assertEqual((recipe["adapter"], recipe["reference_label"], recipe["reference_limit"]),
                         ("pixels", "<Picture {index}>", 8))

    def test_registered_with_the_extension_and_expandable(self):
        from h3_continuity.extension import H3ContinuityExtension
        self.assertIn(ph3.H3C_PH3ImageStill, asyncio.run(H3ContinuityExtension().get_node_list()))
        self.assertTrue(options_of(FILES)[1].enable_expand)


if __name__ == "__main__":
    unittest.main()
