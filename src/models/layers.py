import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class OpticalPreprocessing(nn.Module):
    """เลียนแบบการหักเหแสงเบื้องต้น"""
    def __init__(self):
        super().__init__()

    def forward(self, x):
        return F.normalize(x, p=2, dim=1)

class PhotoreceptorSimulation(nn.Module):
    """เลียนแบบเซลล์รับแสง Retina ด้วย DoG Kernel"""
    def __init__(self, sigma1=1.0, sigma2=3.0):
        super().__init__()
        self.sigma1 = sigma1
        self.sigma2 = sigma2
        self.dog_kernel = self._create_dog_kernel(self.sigma1, self.sigma2)

    def _create_dog_kernel(self, sigma1, sigma2):
        size = 15
        x, y = np.mgrid[-size//2 + 1:size//2 + 1, -size//2 + 1:size//2 + 1]
        g1 = np.exp(-(x**2 + y**2) / (2 * sigma1**2))
        g2 = np.exp(-(x**2 + y**2) / (2 * sigma2**2))
        kernel = (g1 - g2) / (2 * np.pi * sigma1**2)
        kernel = kernel / kernel.sum()
        return torch.FloatTensor(kernel).unsqueeze(0).unsqueeze(0)

    def forward(self, x):
        if x.shape[1] == 3:  # RGB
            r, g, b = x[:, 0], x[:, 1], x[:, 2]
            y = (r + g) / 2
            rg = r - g
            by = b - y
            lum = y
            opponent = torch.cat([rg.unsqueeze(1), by.unsqueeze(1), lum.unsqueeze(1)], dim=1)
        elif x.shape[1] == 1:  # Grayscale
            opponent = x.repeat(1, 3, 1, 1)
        else:
            raise ValueError("Input must have 1 or 3 channels")
        
        # Apply DoG filter
        dog = F.conv2d(opponent, self.dog_kernel.to(x.device).expand(3, 1, 15, 15), padding=7, groups=3)
        return dog

class RetinalNeuralProcessing(nn.Module):
    """เลียนแบบเส้นประสาทตา (Edge Detection)"""
    def __init__(self, in_channels=3):
        super().__init__()
        self.in_channels = in_channels
        self.edge_h = nn.Conv2d(in_channels, 16, kernel_size=3, padding=1, bias=False)
        self.edge_v = nn.Conv2d(in_channels, 16, kernel_size=3, padding=1, bias=False)
        self._init_gabor_kernels()

    def _init_gabor_kernels(self):
        sobel_h = torch.tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=torch.float32).view(1, 1, 3, 3)
        sobel_v = torch.tensor([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=torch.float32).view(1, 1, 3, 3)
        sobel_h = sobel_h.repeat(1, self.in_channels, 1, 1)
        sobel_v = sobel_v.repeat(1, self.in_channels, 1, 1)
        with torch.no_grad():
            self.edge_h.weight = nn.Parameter(sobel_h.repeat(16, 1, 1, 1))
            self.edge_v.weight = nn.Parameter(sobel_v.repeat(16, 1, 1, 1))

    def forward(self, x):
        h_edges = F.relu(self.edge_h(x))
        v_edges = F.relu(self.edge_v(x))
        return torch.cat([h_edges, v_edges], dim=1)  # Output 32 channels

class CorticalHierarchicalProcessing(nn.Module):
    """เลียนแบบ Visual Cortex (Feature Extraction)"""
    def __init__(self, embed_dim=768):
        super().__init__()
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(32, embed_dim)

    def forward(self, x):
        pooled = self.pool(x).flatten(1)
        return self.fc(pooled)

class TemporalProcessing(nn.Module):
    """เลียนแบบความจำระยะสั้น (Sequence/Video)"""
    def __init__(self, embed_dim=768, seq_len=5):
        super().__init__()
        self.lstm = nn.LSTM(embed_dim, embed_dim // 2, bidirectional=True, batch_first=True)

    def forward(self, features, seq_len):
        if seq_len > 1:
            packed = nn.utils.rnn.pack_padded_sequence(features, lengths=[seq_len]*features.size(0), batch_first=True, enforce_sorted=False)
            out, _ = self.lstm(packed)
            out, _ = nn.utils.rnn.pad_packed_sequence(out, batch_first=True)
            return out.mean(1)
        return features
