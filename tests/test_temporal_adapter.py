import unittest

import torch

from src.models.biovision_1_1s import BioVisionNetV1_1S, TemporalProcessingAdapter


class TestTemporalProcessingAdapter(unittest.TestCase):
    def test_invalid_backend_raises_value_error(self):
        with self.assertRaises(ValueError):
            TemporalProcessingAdapter(input_dim=8, backend="invalid")

    def test_2d_input_passthrough_for_mean_backend(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend="mean")
        x = torch.randn(4, 8)
        y = adapter(x)
        self.assertEqual(tuple(y.shape), tuple(x.shape))

    def test_output_dim_matches_backend_contract(self):
        mean_adapter = TemporalProcessingAdapter(input_dim=8, backend="mean")
        self.assertEqual(mean_adapter.output_dim, 8)

        lstm_adapter = TemporalProcessingAdapter(input_dim=8, backend="lstm", lstm_hidden_dim=16)
        self.assertEqual(lstm_adapter.output_dim, 16)

        transformer_adapter = TemporalProcessingAdapter(input_dim=8, backend="transformer", transformer_heads=2)
        self.assertEqual(transformer_adapter.output_dim, 8)

    def test_mean_backend_temporal_pooling(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend="mean")
        x = torch.randn(2, 5, 8)
        y = adapter(x)
        self.assertEqual(tuple(y.shape), (2, 8))

    def test_lstm_backend_temporal_output_shape(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend="lstm", lstm_hidden_dim=12)
        x = torch.randn(2, 5, 8)
        y = adapter(x)
        self.assertEqual(tuple(y.shape), (2, 12))

    def test_transformer_backend_temporal_output_shape(self):
        adapter = TemporalProcessingAdapter(input_dim=8, backend="transformer", transformer_heads=2)
        x = torch.randn(2, 5, 8)
        y = adapter(x)
        self.assertEqual(tuple(y.shape), (2, 8))

    def test_transformer_head_divisibility_validation(self):
        with self.assertRaises(ValueError):
            TemporalProcessingAdapter(input_dim=10, backend="transformer", transformer_heads=3)


class TestBioVisionNetTemporalBackends(unittest.TestCase):
    def test_model_forward_with_different_temporal_backends(self):
        x = torch.randn(2, 4, 3, 64, 64)

        for backend in ("mean", "lstm", "transformer"):
            model = BioVisionNetV1_1S(num_classes=10, embed_dim=32, temporal_backend=backend)
            edge_maps, embedding, logits = model(x)

            self.assertEqual(tuple(edge_maps.shape), (2, 4, 32, 64, 64))
            self.assertEqual(tuple(logits.shape), (2, 10))
            self.assertEqual(tuple(embedding.shape), (2, model.temporal.output_dim))


if __name__ == "__main__":
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
