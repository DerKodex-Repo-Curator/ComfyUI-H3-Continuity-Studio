import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import av
import torch

from h3_continuity import media, video_preview


class VideoPreviewTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='h3c-preview-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'h3_sequences' / 'seq' / 'seg_0001.mp4'
        self.source.parent.mkdir(parents=True)
        self.cache = self.root / 'cache'
        self.query = {'type': 'output', 'subfolder': 'h3_sequences/seq', 'filename': 'seg_0001.mp4'}
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(video_preview.folder_paths, 'get_output_directory', return_value=str(self.root)).start()
        mock.patch.object(video_preview.folder_paths, 'get_temp_directory', return_value=str(self.cache)).start()

    def write_source(self, color_space='HDR'):
        media.write_segment_video(str(self.source), torch.full((10, 400, 800, 3), 0.3), 48, 20,
                                  audio=(torch.full((1, 2000), 0.1), 8000), color_space=color_space)

    def test_hdr_high10_becomes_bounded_sdr_main_with_sound_without_changing_original(self):
        self.write_source()
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        result = video_preview.preview(self.query)
        self.assertNotEqual(Path(result), self.source)
        with av.open(result) as container:
            video = container.streams.video[0]
            self.assertEqual((video.codec_context.name, video.codec_context.profile, video.pix_fmt),
                             ('h264', 'Main', 'yuv420p'))
            self.assertEqual((video.width, video.height), (720, 360))
            self.assertEqual(video.average_rate, 24)
            self.assertEqual(video.codec_context.color_trc, 1)
            self.assertEqual(container.streams.audio[0].codec_context.name, 'aac')
            self.assertGreater(sum(1 for _ in container.decode(video)), 0)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), before)

    def test_cache_is_reused_and_source_change_selects_a_new_preview(self):
        self.write_source('sRGB')
        first = Path(video_preview.preview(self.query))
        stamp = first.stat().st_mtime_ns
        self.assertEqual(video_preview.preview(self.query), str(first))
        self.assertEqual(first.stat().st_mtime_ns, stamp)
        source_stamp = self.source.stat().st_mtime_ns
        os.utime(self.source, ns=(source_stamp + 1000000, source_stamp + 1000000))
        self.assertNotEqual(video_preview.preview(self.query), str(first))

    def test_only_existing_sequence_mp4s_inside_output_are_accepted(self):
        self.write_source()
        for changes in ({'type': 'input'}, {'subfolder': '../outside'},
                        {'subfolder': 'h3_sequences/../../outside'}, {'filename': '../seg_0001.mp4'},
                        {'filename': 'missing.mp4'}, {'filename': 'manifest.json'}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, FileNotFoundError)):
                video_preview.preview({**self.query, **changes})
