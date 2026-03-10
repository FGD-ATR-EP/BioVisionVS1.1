import unittest

import torch

from src.models.biovision_1_1s import BioVisionNetV1_1S, TemporalProcessingAdapter


class TestTemporalProcessingAdapter(unittest.TestCase):
    def test_mean_backend_returns_pooled_embedding(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend='mean')
        x = torch.randn(2, 5, 8)
        y = adapter(x)
        self.assertEqual(y.shape, (2, 8))

    def test_lstm_backend_returns_last_step_embedding(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend='lstm', lstm_hidden_dim=12)
        x = torch.randn(2, 5, 8)
        y = adapter(x)
        self.assertEqual(y.shape, (2, 12))

    def test_transformer_backend_returns_pooled_embedding(self):
        adapter = TemporalProcessingAdapter(input_dim=16, backend='transformer', transformer_heads=4)
        x = torch.randn(2, 5, 16)
        y = adapter(x)
        self.assertEqual(y.shape, (2, 16))

    def test_model_supports_multiple_temporal_backends(self):
        x = torch.randn(2, 3, 3, 32, 32)
        for backend in ('mean', 'lstm', 'transformer'):
            model = BioVisionNetV1_1S(num_classes=4, embed_dim=32, temporal_backend=backend)
            edge_maps, embedding, logits = model(x)
            self.assertEqual(edge_maps.shape, (2, 3, 32, 32, 32))
            self.assertEqual(logits.shape, (2, 4))
            self.assertEqual(embedding.shape[0], 2)


if __name__ == '__main__':
    unittest.main()
