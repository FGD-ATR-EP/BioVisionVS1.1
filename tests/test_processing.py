import unittest
from unittest.mock import patch

import torch

from src.data.processing import preprocess_video


class TestPreprocessVideo(unittest.TestCase):
    def test_preprocess_video_normalizes_to_unit_range(self):
        fake_video = torch.full((5, 2, 2, 3), 255, dtype=torch.uint8)

        with patch('src.data.processing.tvio.read_video', return_value=(fake_video, None, None)):
            output = preprocess_video('dummy.mp4', seq_len=5, target_size=(2, 2), grayscale=False)

        self.assertEqual(output.shape, (1, 5, 3, 2, 2))
        self.assertTrue(torch.isfinite(output).all())
        # All-white input should map close to normalized 1.0 level after ImageNet stats.
        self.assertLess(output.max().item(), 3.0)

    def test_preprocess_video_loops_frames_when_shorter_than_seq_len(self):
        fake_video = torch.randint(0, 255, (2, 2, 2, 3), dtype=torch.uint8)

        with patch('src.data.processing.tvio.read_video', return_value=(fake_video, None, None)):
            output = preprocess_video('dummy.mp4', seq_len=5, target_size=(2, 2), grayscale=False)

        self.assertEqual(output.shape, (1, 5, 3, 2, 2))


if __name__ == '__main__':
    unittest.main()
