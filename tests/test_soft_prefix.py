import json
import unittest

import torch

from tests.continuity_support import enable_comfy_cpu

enable_comfy_cpu()

import comfy.nested_tensor  # noqa: E402
from h3_continuity import latents  # noqa: E402


class SoftPrefixTest(unittest.TestCase):
    def setUp(self):
        generator = torch.Generator().manual_seed(0)
        self.video = torch.randn(1, 24, 57, 4, 6, generator=generator)
        self.audio = torch.randn(1, 32, 2, 320, generator=generator)
        self.target = {"samples": comfy.nested_tensor.NestedTensor((torch.zeros(1, 24, 37, 4, 6), torch.zeros(1, 32, 2, 207)))}

    def masks(self, **kwargs):
        out, *_ = latents.build_continuation(self.target, self.video, self.audio, 39, True, **kwargs)
        return out["noise_mask"].tensors

    def test_default_freezes_exactly(self):
        video_mask, audio_mask = self.masks()
        self.assertEqual(video_mask[:, :, :12].sum().item(), 0)

    def test_soft_value_on_video_only(self):
        video_mask, audio_mask = self.masks(soft_prefix=0.03)
        self.assertTrue(torch.allclose(video_mask[:, :, :12], torch.full_like(video_mask[:, :, :12], 0.03)))
        self.assertTrue(bool((video_mask[:, :, 12:] == 1).all()))
        self.assertEqual(audio_mask[..., :65].sum().item(), 0)

    def test_rejects_out_of_range(self):
        with self.assertRaisesRegex(ValueError, "soft_prefix"):
            self.masks(soft_prefix=1.5)


class TimelineSettingsTest(unittest.TestCase):
    def parse(self, **keys):
        from h3_continuity import timeline
        data = {"version": 1, "boxes": [{"id": "a", "frames": 124, "seed": 1, "prompt": "p"},
                                        {"id": "b", "frames": 124, "seed": 2, "prompt": "q"}], **keys}
        return timeline, timeline.parse(json.dumps(data))

    def test_defaults_leave_layouts_unchanged(self):
        timeline, parsed = self.parse()
        self.assertEqual((parsed.soft_prefix, parsed.continuation_guide), (0.0, True))
        _, marked = self.parse(soft_prefix=0, continuation_guide=True)
        self.assertEqual(timeline.layout_key(parsed, 1), timeline.layout_key(marked, 1))

    def test_settings_change_only_continuing_layouts(self):
        timeline, plain = self.parse()
        _, soft = self.parse(soft_prefix=0.03, continuation_guide=False)
        self.assertEqual(timeline.layout_key(plain, 0), timeline.layout_key(soft, 0))
        self.assertNotEqual(timeline.layout_key(plain, 1), timeline.layout_key(soft, 1))

    def test_invalid_values_fail(self):
        for keys in ({"soft_prefix": 2}, {"soft_prefix": True}, {"continuation_guide": "no"}):
            with self.assertRaises(ValueError):
                self.parse(**keys)


if __name__ == "__main__":
    unittest.main()
