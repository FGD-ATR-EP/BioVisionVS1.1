import torch
import torch.nn as nn
import torch.nn.functional as F
import logging
from typing import Tuple, Optional

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
        if x.max() > 1.0 + 1e-6 or x.min() < -1e-6:
            logging.warning("Input image not in expected range [0,1] or [-1,1]")
        return F.normalize(x, p=2, dim=1)

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
        dog = dog / dog.abs().sum()
        return dog.unsqueeze(0).unsqueeze(0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x expected to be [B, 3, H, W]
        if x.shape[1] != 3:
            # If 5D input passed directly, this raises error.
            # BioVisionNet.forward handles reshaping before calling this.
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
        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
        self._init_sobel_weights()

    def _init_sobel_weights(self):
        # [Fix NameError] ใช้ self.conv.out_channels แทน
        out_channels = self.conv.out_channels

        sobel = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32).view(1, 1, 3, 3)
        weight = torch.cat([sobel, -sobel], dim=0)
        weight = weight.repeat(1, 3, 1, 1)

        # คำนวณจำนวนการ repeat ให้พอดีกับ out_channels
        repeats = out_channels // weight.shape[0] + 1
        weight = weight.repeat(repeats, 1, 1, 1)

        with torch.no_grad():
            self.conv.weight.copy_(weight[:out_channels])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.conv(x))

# --- New: Temporal Processing Adapter (เพื่อรองรับ Option B) ---
class TemporalProcessingAdapter(nn.Module):
    """
    ส่วนจำลองการประมวลผลเชิงเวลา (Temporal)
    ในอนาคต: เปลี่ยนเป็น LSTM หรือ Transformer
    ปัจจุบัน: ใช้ Simple Pooling เพื่อให้ Interface ตรงกับ main.py
    """
    def __init__(self, input_dim: int):
        super().__init__()
        # ตัวอย่าง: สมมติว่ารับ [Batch, Time, Features] หรือ [Batch, Features]
        # ในที่นี้เราจะส่งผ่านไปก่อน (Identity) หรือ Mean Pooling ถ้ามี Time dim
        self.dummy_layer = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [Batch, Time, Features] or [Batch, Features]
        if x.dim() == 3:
            # Mean pooling over time dimension (dim 1)
            return x.mean(dim=1)
        return self.dummy_layer(x)

# --- Main Model (Updated for Option B) ---

class BioVisionNet(nn.Module):
    def __init__(self,
                 num_classes: int = 1000,
                 embed_dim: int = 768,
                 dog_sigma_center: float = 1.0,
                 dog_sigma_surround: float = 3.0,
                 temporal_steps: int = 1): # เพิ่ม parameter เพื่อความเข้ากันได้
        super().__init__()

        # 1. Perception Layers
        self.preprocess   = OpticalPreprocessing()
        self.photoreceptor = PhotoreceptorSimulation(sigma_center=dog_sigma_center, sigma_surround=dog_sigma_surround)
        self.retinal      = RetinalNeuralProcessing(in_channels=3, out_channels=32)

        # 2. Cortical Processing (Feature Extraction)
        self.cortical     = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(32, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.ReLU() # เพิ่ม Non-linearity ก่อนเข้า Classifier
        )

        # 3. [Option B] Temporal Processing (Placeholder/Adapter)
        self.temporal = TemporalProcessingAdapter(embed_dim)

        # 4. [Option B] Classifier (เพื่อสร้าง Logits)
        self.classifier = nn.Linear(embed_dim, num_classes)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Return:
            edge_maps (features): Output จาก Retinal (Visual Debugging)
            embedding: Vector ตัวแทนภาพ
            logits: ผลลัพธ์การจำแนกประเภท (สำหรับ main.py)
        """
        # Handle 5D Input [B, S, C, H, W] -> Flatten to [B*S, C, H, W]
        b, s, c, h, w = 0, 1, 0, 0, 0
        if x.dim() == 5:
            b, s, c, h, w = x.shape
            x = x.view(b * s, c, h, w)
            is_sequence = True
        else:
            b, c, h, w = x.shape
            s = 1
            is_sequence = False

        # --- Visual Pathway ---
        x = self.preprocess(x)
        x = self.photoreceptor(x)
        edge_maps = self.retinal(x)  # [B*S, 32, H, W]

        # --- Cognitive Pathway ---
        embedding = self.cortical(edge_maps) # [B*S, embed_dim]

        # --- Temporal & Decision Pathway ---
        # Reshape to [B, S, embed_dim] for temporal processing
        embedding_seq = embedding.view(b, s, -1)

        # Temporal Adapter (handles aggregation if S > 1)
        context_aware_embedding = self.temporal(embedding_seq) # [B, embed_dim]

        logits = self.classifier(context_aware_embedding) # [B, num_classes]

        # Reshape edge_maps to 5D [B, S, 32, H, W] for visualization compatibility
        edge_maps = edge_maps.view(b, s, 32, h, w)

        return edge_maps, context_aware_embedding, logits

if __name__ == "__main__":
    # Test Compatibility
    model = BioVisionNet(num_classes=10, embed_dim=512).to(device)

    # Test 1: Image Input (4D)
    dummy_img = torch.randn(2, 3, 224, 224).to(device) # Batch=2
    edge_maps, emb, logits = model(dummy_img)
    print(f"Image Input - Edge Maps Shape : {edge_maps.shape}") # Expected [2, 1, 32, 224, 224]
    print(f"Image Input - Embedding Shape : {emb.shape}")       # Expected [2, 512]
    print(f"Image Input - Logits Shape    : {logits.shape}")    # Expected [2, 10]

    # Test 2: Video Input (5D)
    dummy_video = torch.randn(1, 5, 3, 224, 224).to(device) # Batch=1, Seq=5
    edge_maps_v, emb_v, logits_v = model(dummy_video)
    print(f"Video Input - Edge Maps Shape : {edge_maps_v.shape}") # Expected [1, 5, 32, 224, 224]
    print(f"Video Input - Embedding Shape : {emb_v.shape}")       # Expected [1, 512]
    print(f"Video Input - Logits Shape    : {logits_v.shape}")    # Expected [1, 10]
