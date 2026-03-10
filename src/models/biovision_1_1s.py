import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
from typing import Tuple, Optional
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Device handling
if torch.cuda.is_available():
    device = torch.device("cuda")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")

# --- Components ---

class OpticalPreprocessing(nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Enhanced Normalization from BioVisionNet 1.1s (Synergistic Update)
        # Check range and auto-correct if needed
        if x.max() > 1.0 + 1e-6 or x.min() < -1e-6:
            if x.max() > 2.0:
                 # Assumes [0, 255]
                x = x / 255.0
            else:
                 # Just clamp if slightly off
                x = x.clamp(0, 1)

        # Removed F.normalize (L2 norm) which destroys intensity info.
        # Keeping intensity is crucial for "clarity" (BioVisionNet 1.1s goal).
        return x

class PhotoreceptorSimulation(nn.Module):
    def __init__(self, sigma_center: float = 1.0, sigma_surround: float = 3.0, kernel_size: int = 15):
        super().__init__()
        self.sigma_center = sigma_center
        self.sigma_surround = sigma_surround
        self.kernel_size = kernel_size
        self.padding = kernel_size // 2
        self.register_buffer("dog_kernel", self._create_dog_kernel())

    def _create_dog_kernel(self) -> torch.Tensor:
        size = self.kernel_size
        x = torch.arange(-size//2 + 1, size//2 + 1, dtype=torch.float32)
        x, y = torch.meshgrid(x, x, indexing='ij')
        g_center   = torch.exp( -(x**2 + y**2) / (2 * self.sigma_center**2) )
        g_surround = torch.exp( -(x**2 + y**2) / (2 * self.sigma_surround**2) )
        dog = g_center - g_surround

        # Normalize by absolute sum to preserve energy balance without gain explosion
        dog = dog / (dog.abs().sum() + 1e-8)

        return dog.unsqueeze(0).unsqueeze(0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x expected to be [B, 3, H, W]
        if x.shape[1] != 3:
            raise ValueError(f"Expected 3 channels, got {x.shape[1]}")

        r, g, b = x[:,0], x[:,1], x[:,2]
        luminance = (r + g) * 0.5
        rg_opponent = r - g
        by_opponent = b - luminance
        opponent = torch.stack([rg_opponent, by_opponent, luminance], dim=1)

        dog = F.conv2d(
            opponent,
            weight=self.dog_kernel.expand(3, 1, self.kernel_size, self.kernel_size),
            padding=self.padding,
            groups=3
        )
        return dog

class RetinalNeuralProcessing(nn.Module):
    def __init__(self, in_channels: int = 3, out_channels: int = 32):
        super().__init__()
        # We split out_channels into 2 groups: Horizontal and Vertical edges
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self._init_sobel_weights()

    def _init_sobel_weights(self):
        out_channels = self.conv.out_channels
        in_channels = self.conv.in_channels

        # Standard Sobel X (responds strongly to vertical lines)
        # [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
        sobel_h_kernel = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32)

        # Standard Sobel Y (responds strongly to horizontal lines)
        # [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
        sobel_v_kernel = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32)

        # Reshape for broadcasting: [1, 1, 3, 3]
        sobel_h = sobel_h_kernel.view(1, 1, 3, 3)
        sobel_v = sobel_v_kernel.view(1, 1, 3, 3)

        # Split filters equally: Sobel-X group first, Sobel-Y group second.
        # If out_channels = 32, first 16 are X-gradient and next 16 are Y-gradient.
        split = out_channels // 2

        # Create weights for H part [split, in_channels, 3, 3]
        # We repeat sobel_h across in_channels (3) and split (16)
        weight_h = sobel_h.expand(split, in_channels, 3, 3) / 8.0 # Normalize scale

        # Create weights for V part
        weight_v = sobel_v.expand(out_channels - split, in_channels, 3, 3) / 8.0

        # Concatenate
        weight_final = torch.cat([weight_h, weight_v], dim=0)

        with torch.no_grad():
            self.conv.weight.copy_(weight_final)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.conv(x))

class TemporalProcessingAdapter(nn.Module):
    """
    Configurable temporal aggregation for sequence embeddings.
    """
    def __init__(
        self,
        input_dim: int,
        backend: str = "mean",
        lstm_hidden_dim: int = 256,
        transformer_heads: int = 8,
        transformer_layers: int = 1,
    ):
        super().__init__()
        self.backend = backend.lower()

        if self.backend == "mean":
            self.adapter = nn.Identity()
            self.output_dim = input_dim
        elif self.backend == "lstm":
            self.adapter = nn.LSTM(
                input_size=input_dim,
                hidden_size=lstm_hidden_dim,
                num_layers=1,
                batch_first=True,
            )
            self.output_dim = lstm_hidden_dim
        elif self.backend == "transformer":
            if input_dim % transformer_heads != 0:
                raise ValueError(
                    f"input_dim ({input_dim}) must be divisible by transformer_heads ({transformer_heads})"
                )
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=input_dim,
                nhead=transformer_heads,
                batch_first=True,
            )
            self.adapter = nn.TransformerEncoder(encoder_layer, num_layers=transformer_layers)
            self.output_dim = input_dim
        else:
            raise ValueError(
                f"Unsupported temporal backend: {backend}. Supported backends are: mean, lstm, transformer"
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [Batch, Time, Features] or [Batch, Features]
        if x.dim() == 2:
            return x

        if x.dim() != 3:
            raise ValueError(f"Temporal input must be 2D or 3D tensor, got shape {tuple(x.shape)}")

        if self.backend == "mean":
            return x.mean(dim=1)
        if self.backend == "lstm":
            out, _ = self.adapter(x)
            return out[:, -1, :]

        transformed = self.adapter(x)
        return transformed.mean(dim=1)

# --- Main Model BioVisionNet 1.1s ---

class BioVisionNetV1_1S(nn.Module):
    """
    BioVisionNet 1.1s (Synergistic Update)
    Combines the robust architecture of v2 with enhanced initialization and processing from alternative research.
    """
    def __init__(self,
                 num_classes: int = 1000,
                 embed_dim: int = 768,
                 dog_sigma_center: float = 1.0,
                 dog_sigma_surround: float = 3.0,
                 temporal_backend: str = "mean",
                 temporal_steps: int = 1):
        super().__init__()

        self._temporal_steps = temporal_steps  # reserved for future use

        # 1. Perception Layers
        self.preprocess   = OpticalPreprocessing()
        self.photoreceptor = PhotoreceptorSimulation(sigma_center=dog_sigma_center, sigma_surround=dog_sigma_surround)

        # Retinal Processing now includes both H and V edge detection explicitly
        self.retinal      = RetinalNeuralProcessing(in_channels=3, out_channels=32)

        # 2. Cortical Processing (Feature Extraction)
        # Matches v2 but receives richer (H+V) features from Retinal layer
        self.cortical     = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(32, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.ReLU()
        )

        # 3. Temporal Processing
        self.temporal = TemporalProcessingAdapter(embed_dim, backend=temporal_backend)

        # 4. Classifier
        self.classifier = nn.Linear(self.temporal.output_dim, num_classes)

        self._init_weights()

    def _init_weights(self):
        # Explicit initialization for cortical and classifier
        nn.init.trunc_normal_(self.cortical[2].weight, std=0.02)
        nn.init.trunc_normal_(self.classifier.weight, std=0.02)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Return:
            edge_maps (features): Output from Retinal (Visual Debugging)
            embedding: Vector representation
            logits: Classification results
        """
        # Handle 5D Input [B, S, C, H, W] -> Flatten to [B*S, C, H, W]
        b, s, c, h, w = 0, 1, 0, 0, 0
        if x.dim() == 5:
            b, s, c, h, w = x.shape
            x = x.view(b * s, c, h, w)
        else:
            b, c, h, w = x.shape
            s = 1

        # --- Visual Pathway ---
        x = self.preprocess(x)
        x = self.photoreceptor(x)
        edge_maps = self.retinal(x)  # [B*S, 32, H, W] (16 H-filters + 16 V-filters)

        # --- Cognitive Pathway ---
        embedding = self.cortical(edge_maps) # [B*S, embed_dim]

        # --- Temporal & Decision Pathway ---
        embedding_seq = embedding.view(b, s, -1)
        context_aware_embedding = self.temporal(embedding_seq) # [B, temporal.output_dim]
        logits = self.classifier(context_aware_embedding) # [B, num_classes]

        # Reshape edge_maps to 5D [B, S, 32, H, W] for visualization
        edge_maps = edge_maps.view(b, s, 32, h, w)

        return edge_maps, context_aware_embedding, logits

if __name__ == "__main__":
    # Test Compatibility
    model = BioVisionNetV1_1S(num_classes=10, embed_dim=512).to(device)
    print("BioVisionNet 1.1s initialized successfully.")

    # Test 1: Image Input (4D)
    dummy_img = torch.randn(2, 3, 224, 224).to(device) # Batch=2
    edge_maps, emb, logits = model(dummy_img)
    print(f"Image Input - Edge Maps Shape : {edge_maps.shape}") # Expected [2, 1, 32, 224, 224]
    print(f"Image Input - Embedding Shape : {emb.shape}")       # Expected [2, 512]
    print(f"Image Input - Logits Shape    : {logits.shape}")    # Expected [2, 10]

    # Verify Edge Maps (First 16 should be different from Next 16)
    # Visual check logic would go here
