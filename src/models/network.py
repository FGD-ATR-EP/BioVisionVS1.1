import torch.nn as nn
from .layers import (
    OpticalPreprocessing,
    PhotoreceptorSimulation,
    RetinalNeuralProcessing,
    CorticalHierarchicalProcessing,
    TemporalProcessing
)

class BioVisionNet(nn.Module):
    def __init__(self, num_classes=1000, seq_len=5, embed_dim=768, in_channels=3):
        super().__init__()
        self.seq_len = seq_len
        self.optical = OpticalPreprocessing()
        self.photoreceptor = PhotoreceptorSimulation()
        self.retinal = RetinalNeuralProcessing(in_channels)
        self.cortical = CorticalHierarchicalProcessing(embed_dim)
        self.temporal = TemporalProcessing(embed_dim, seq_len)
        self.classifier = nn.Linear(embed_dim, num_classes)

    def forward(self, x):
        # Handle Sequence Input [batch, seq, c, h, w] vs Single Image [batch, c, h, w]
        if len(x.shape) == 5:
            b, s, c, h, w = x.shape
            x = x.view(b * s, c, h, w)
            seq_len = s
        else:
            b, c, h, w = x.shape
            x = x.view(b, 1, c, h, w)
            seq_len = 1
            x = x.view(b * seq_len, c, h, w)
        
        # Forward pass through layers
        x = self.optical(x)
        x = self.photoreceptor(x)
        x = self.retinal(x)
        features = self.cortical(x)
        
        # Reshape for Temporal Processing
        features = features.view(b, seq_len, -1)
        temporal_features = self.temporal(features, seq_len)
        
        logits = self.classifier(temporal_features)
        
        # Return internal map for visualization, features, and final logits
        return x.view(b, seq_len, 32, h, w), temporal_features, logits
